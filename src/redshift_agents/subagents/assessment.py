"""
Assessment Subagent for Redshift cluster analysis.

This subagent performs comprehensive assessment of Redshift clusters including
configuration analysis, performance evaluation, and usage pattern identification.
"""
from typing import Optional
import os

from eg_platform_base_agent.subagent_strands.base_subagent import AsyncBaseSubagent
from mcp import MCPClient

from ..tools.redshift_tools import (
    analyze_redshift_cluster,
    get_cluster_metrics,
    list_redshift_clusters,
)
from ..tools.audit_logger import emit_audit_event


ASSESSMENT_SYSTEM_PROMPT = """You are the Assessment Subagent for Redshift cluster analysis.

Your specific task is to perform comprehensive assessment of Redshift clusters.

## Your Capabilities

You have access to these tools:

1. **analyze_redshift_cluster(cluster_id, region)**
   - Returns detailed cluster configuration
   - Includes security, network, and version information
   - Use this as your primary analysis tool

2. **get_cluster_metrics(cluster_id, region, hours)**
   - Returns CloudWatch performance metrics
   - Includes CPU, connections, network, disk usage
   - Use this to assess performance patterns

3. **list_redshift_clusters(region)**
   - Lists all clusters in a region
   - Use when customer doesn't specify cluster ID

## Your Responsibilities

### 1. Configuration Analysis
- Analyze node types and cluster sizing
- Review security settings (encryption, VPC, access controls)
- Assess network configuration
- Check parameter groups and settings
- Evaluate backup and maintenance windows

### 2. Performance Analysis
- Review CPU and memory utilization patterns
- Assess disk space usage trends
- Analyze network throughput
- Identify performance bottlenecks
- Review connection patterns

### 3. Usage Pattern Identification
- Determine workload types (ETL, analytics, reporting, mixed)
- Identify peak usage times
- Assess data access patterns
- Evaluate concurrent user patterns

### 4. Risk Assessment
- Identify security vulnerabilities
- Assess compliance gaps
- Evaluate performance risks
- Identify capacity constraints

## Output Format

Provide structured analysis in this format:

```json
{
  "cluster_summary": {
    "cluster_id": "...",
    "node_type": "...",
    "number_of_nodes": ...,
    "status": "...",
    "region": "..."
  },
  "configuration_findings": [
    {
      "category": "security|performance|cost|compliance",
      "severity": "high|medium|low",
      "finding": "Description of the finding",
      "impact": "Impact on operations",
      "recommendation": "Specific action to take"
    }
  ],
  "performance_findings": [
    {
      "metric": "CPU|Memory|Disk|Network",
      "current_value": "...",
      "threshold": "...",
      "status": "healthy|warning|critical",
      "recommendation": "..."
    }
  ],
  "usage_patterns": {
    "workload_type": "ETL|Analytics|Reporting|Mixed",
    "peak_hours": "...",
    "average_connections": ...,
    "data_access_pattern": "..."
  },
  "risk_assessment": {
    "overall_risk": "low|medium|high",
    "security_risks": [...],
    "performance_risks": [...],
    "compliance_risks": [...]
  },
  "recommendations": [
    {
      "priority": "high|medium|low",
      "category": "...",
      "recommendation": "...",
      "estimated_effort": "...",
      "expected_benefit": "..."
    }
  ]
}
```

## Analysis Guidelines

1. **Be Thorough**: Use all available tools to gather complete information
2. **Be Specific**: Provide concrete findings with data to support them
3. **Be Actionable**: Every finding should have a clear recommendation
4. **Prioritize**: Rank recommendations by impact and effort
5. **Consider Context**: Account for customer's specific use case

## Example Workflow

When asked to assess a cluster:

1. Use `analyze_redshift_cluster()` to get configuration
2. Use `get_cluster_metrics()` to get performance data
3. Analyze the data for patterns and issues
4. Generate structured findings and recommendations
5. Provide clear summary for customer

## Important Notes

- Always include `customer_account_id` in your context for proper isolation
- Use namespace-based identifiers when available
- Focus on facts from data, not assumptions
- Provide cost estimates when recommending changes
- Consider both immediate and long-term improvements
"""


def create_assessment_subagent(
    mcp_client: Optional['MCPClient'],
    storage_dir: str
) -> 'AsyncBaseSubagent':
    """
    Create Assessment Subagent for Redshift cluster analysis.
    
    This subagent analyzes Redshift clusters and provides comprehensive
    assessments including configuration, performance, and usage patterns.
    
    Args:
        mcp_client: MCP client for platform communication
        storage_dir: Directory for agent state storage
        
    Returns:
        Configured AsyncBaseSubagent instance with Redshift analysis tools
        
    Note:
        The BaseAgent SDK is automatically available via pip when using atx-dev power.
    """
    emit_audit_event(
        "agent_start",
        "assessment",
        details={"storage_dir": storage_dir},
    )
    return AsyncBaseSubagent(
        system_prompt=ASSESSMENT_SYSTEM_PROMPT,
        mcp_clients=[mcp_client] if mcp_client else None,
        custom_tools=[
            analyze_redshift_cluster,
            get_cluster_metrics,
            list_redshift_clusters,
        ],
        region_name=os.getenv("AWS_REGION", "us-east-2"),
    )


# CLI entry point for standalone deployment
def main():
    """Entry point for Assessment Subagent."""
    import argparse
    import logging
    
    from eg_platform_base_agent.server.agent_runtime_server import AgentRuntimeServer
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="Assessment Subagent")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--storage-dir", default="/tmp/assessment")
    parser.add_argument("--binary-location", required=True)
    args = parser.parse_args()
    
    logger.info("Starting Assessment Subagent...")
    
    server = AgentRuntimeServer(
        agent_factory=create_assessment_subagent,
        host=args.host,
        port=args.port,
        storage_dir=args.storage_dir,
        binary_location=args.binary_location,
    )
    server.start()


if __name__ == "__main__":
    main()
