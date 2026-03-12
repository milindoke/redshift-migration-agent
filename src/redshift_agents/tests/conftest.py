"""
Shared test configuration.

Stubs the ``strands`` package so tool modules can be imported in the test
environment where strands-agents is not installed (requires Python 3.10+).
"""
import os
import sys
import types

# Add src/ to sys.path so the full ``redshift_agents`` package is importable
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Stub strands so tools/__init__.py → redshift_tools.py can be imported
_strands = types.ModuleType("strands")
_strands_tools = types.ModuleType("strands.tools")
_strands_tools.tool = lambda f: f  # no-op @tool decorator
_strands.tools = _strands_tools
class _StubAgent:
    def __init__(self, system_prompt="", tools=None, **kwargs):
        self.system_prompt = system_prompt
        self.tools = tools or []

_strands.Agent = _StubAgent

sys.modules.setdefault("strands", _strands)
sys.modules.setdefault("strands.tools", _strands_tools)

# Stub bedrock_agentcore so orchestrator module can be imported
_bedrock_agentcore = types.ModuleType("bedrock_agentcore")
_bedrock_agentcore_runtime = types.ModuleType("bedrock_agentcore.runtime")


class _StubBedrockAgentCoreApp:
    def __init__(self, **kwargs):
        pass

    def serve(self):
        pass


_bedrock_agentcore_runtime.BedrockAgentCoreApp = _StubBedrockAgentCoreApp
_bedrock_agentcore.runtime = _bedrock_agentcore_runtime
sys.modules.setdefault("bedrock_agentcore", _bedrock_agentcore)
sys.modules.setdefault("bedrock_agentcore.runtime", _bedrock_agentcore_runtime)
