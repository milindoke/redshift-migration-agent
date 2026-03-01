"""
Subagents for Redshift modernization tasks.

Each subagent specializes in a specific aspect of the modernization workflow.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type hints only - these will be available once SDK is installed
    from .assessment import create_assessment_subagent
    from .scoring import create_scoring_subagent
    from .architecture import create_architecture_subagent
    from .execution import create_execution_subagent

__all__ = [
    "create_assessment_subagent",
    "create_scoring_subagent",
    "create_architecture_subagent",
    "create_execution_subagent",
]
