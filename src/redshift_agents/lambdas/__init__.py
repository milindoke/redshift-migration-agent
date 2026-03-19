"""
Lambda action group handlers for Bedrock Agents.

Each handler receives Bedrock Agent action group invocation events,
dispatches to the appropriate tool function, and returns the structured
response format expected by Bedrock Agents.
Public API is available via direct module imports:
  from lambdas.assessment_handler import handler
  from lambdas.execution_handler import handler
  from lambdas.cluster_lock_handler import handler
"""
