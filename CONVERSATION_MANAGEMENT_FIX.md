# Conversation History Management Fix (Updated)

## Problem

After 30+ messages in tool-heavy conversations, the agent encountered a Bedrock ValidationException:
```
The number of toolResult blocks at messages.X.content exceeds the number of toolUse blocks of previous turn.
```

This error occurred because the conversation history management was dropping messages in a way that created an imbalance between toolUse and toolResult blocks.

## Root Cause

The issue was with how the `SlidingWindowConversationManager` handles message dropping:

1. In tool-heavy conversations (like migration workflows), each user message can trigger 3-5 tool calls
2. When the sliding window drops old messages, it can drop a message containing toolUse blocks
3. The corresponding toolResult blocks in the next message become "orphaned"
4. Bedrock validates that every toolResult has a corresponding toolUse in the previous turn
5. This validation fails when the toolUse message was dropped but the toolResult message remains

## Solution Implemented

### 1. Very Conservative Sliding Window
```python
conversation_manager = SlidingWindowConversationManager(
    window_size=10,  # Very small window for tool-heavy workflows
    should_truncate_results=True  # Truncate large tool results
)
```

**Why 10 messages?**
- Reduces the chance of toolUse/toolResult imbalance
- Each message pair (user + assistant) typically contains 1-3 tool calls
- 10 messages ≈ 5 conversation turns ≈ 15-25 tool blocks
- Stays well within Bedrock's limits
- Minimizes risk of dropping messages that break pairs

### 2. Error Detection and Recovery
```python
# In lambda_handler.py
if 'toolResult blocks' in error_msg and 'toolUse blocks' in error_msg:
    return {
        'error': 'Conversation history has become imbalanced',
        'suggestion': 'Please start a new session with a different session_id'
    }
```

**Recovery Strategy:**
- Detect the specific error pattern
- Inform user that conversation history is corrupted
- Suggest starting a new session
- Chat script automatically creates new session

### 3. AgentCore Memory Preservation
```python
session_manager = AgentCoreMemorySessionManager(
    agentcore_memory_config=AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=actor_id
    )
)
```

**Memory Strategies:**
- Summary Strategy: Preserves conversation summaries
- User Preference Strategy: Remembers user preferences
- Semantic Memory Strategy: Stores important facts

**Benefits:**
- Important information persists even when starting new session
- Migration progress and decisions are remembered
- User doesn't lose context when switching sessions

## Trade-offs

### Pros
✅ Prevents toolUse/toolResult imbalance errors
✅ Works reliably for tool-heavy workflows
✅ Important information preserved in long-term memory
✅ Automatic error recovery

### Cons
❌ Smaller context window (10 vs 40 messages)
❌ May need to start new session in very long conversations
❌ Less immediate context available to the model

## Why Not a Larger Window?

We tried window_size=20 first, but it still caused imbalances because:
- The SlidingWindowConversationManager's pair-preservation logic isn't perfect
- In tool-heavy workflows, even 20 messages can accumulate 60+ tool blocks
- When dropping messages, it's hard to guarantee pairs stay together
- A smaller window (10) is more conservative and reliable

## Alternative Approaches Considered

### 1. Custom Conversation Manager
**Idea:** Build a custom manager that tracks toolUse/toolResult pairs explicitly

**Why not:**
- Complex to implement correctly
- Would need to handle edge cases (nested tools, errors, etc.)
- Maintenance burden
- Strands SDK should handle this (it's a framework issue)

### 2. Periodic History Clearing
**Idea:** Clear conversation history every N messages

**Why not:**
- Loses all context, not just old messages
- Breaks conversation flow
- User experience suffers

### 3. Manual Session Management
**Idea:** Require users to manually start new sessions

**Why not:**
- Poor user experience
- Users don't know when to switch
- Adds cognitive load

## Current Solution: Best Balance

The current approach (window_size=10 + error recovery + memory) provides:
- Reliability: Minimizes imbalance errors
- Usability: Automatic recovery when errors occur
- Continuity: Memory preserves important information
- Simplicity: No complex custom logic needed

## Testing

To verify the fix:

1. Start a long conversation (20+ messages)
2. Use multiple tool calls per message
3. Verify no imbalance errors for first 20-25 messages
4. If error occurs after 30+ messages:
   - Chat script automatically starts new session
   - Important context preserved in memory
   - User can continue migration

## Future Improvements

### Short-term
1. Monitor error frequency in production
2. Adjust window_size if needed (8, 12, etc.)
3. Add metrics for conversation length

### Long-term
1. Contribute fix to Strands SDK for better pair preservation
2. Implement smarter message dropping (keep complete turns)
3. Add conversation summarization before dropping messages

## References

- [Strands SlidingWindowConversationManager](https://strandsagents.com/latest/documentation/docs/api-reference/python/agent/conversation_manager/sliding_window_conversation_manager/)
- [AWS Bedrock AgentCore Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html)
- [Bedrock Converse API Validation](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
