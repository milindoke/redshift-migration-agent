"""
Orchestrator for Redshift modernization workflow.

Coordinates the complete modernization process by delegating to specialized subagents.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type hints only - these will be available once SDK is installed
    from .orchestrator import create_orchestrator, ORCHESTRATOR_SYSTEM_PROMPT

__all__ = [
    "create_orchestrator",
    "ORCHESTRATOR_SYSTEM_PROMPT",
]
