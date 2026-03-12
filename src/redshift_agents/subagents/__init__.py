"""
Subagents for Redshift modernization tasks.

Each subagent specializes in a specific aspect of the modernization workflow:
- Assessment: Cluster discovery, WLM queue analysis, CloudWatch metrics
- Architecture: Workgroup split design, RPU sizing, cost estimates
- Execution: Namespace/workgroup creation, snapshot restore, migration
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .assessment import create_agent as create_assessment_agent
    from .architecture import create_agent as create_architecture_agent
    from .execution import create_agent as create_execution_agent

__all__ = [
    "create_assessment_agent",
    "create_architecture_agent",
    "create_execution_agent",
]
