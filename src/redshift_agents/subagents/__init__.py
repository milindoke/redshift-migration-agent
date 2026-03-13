"""
Subagents for Redshift modernization tasks.

Each subagent module contains a system prompt constant used by the CDK stack
to configure the corresponding Bedrock Agent:
- Assessment: Cluster discovery, WLM queue analysis, CloudWatch metrics
- Architecture: Workgroup split design, RPU sizing, cost estimates
- Execution: Namespace/workgroup creation, snapshot restore, migration
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .assessment import ASSESSMENT_SYSTEM_PROMPT
    from .architecture import ARCHITECTURE_SYSTEM_PROMPT
    from .execution import EXECUTION_SYSTEM_PROMPT

__all__ = [
    "ASSESSMENT_SYSTEM_PROMPT",
    "ARCHITECTURE_SYSTEM_PROMPT",
    "EXECUTION_SYSTEM_PROMPT",
]
