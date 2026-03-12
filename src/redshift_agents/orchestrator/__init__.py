"""
Orchestrator for Redshift modernization workflow.

Coordinates the complete modernization process by delegating to specialized subagents.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import create_agent, ORCHESTRATOR_SYSTEM_PROMPT

__all__ = [
    "create_agent",
    "ORCHESTRATOR_SYSTEM_PROMPT",
]
