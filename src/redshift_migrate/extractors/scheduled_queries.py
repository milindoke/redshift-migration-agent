"""Extract scheduled queries from EventBridge and Redshift Data API."""

import boto3
import json
from typing import List, Dict, Optional, Any
from ..models import ScheduledQuery


class ScheduledQueryExtractor:
    """Extract scheduled queries associated with a Redshift cluster."""

    def __init__(self, region: Optional[str] = None):
        self.events = boto3.client("events", region_name=region)
        self.redshift_data = boto3.client("redshift-data", region_name=region)
        self.scheduler = boto3.client("scheduler", region_name=region)
        self.region = region or boto3.Session().region_name

    def extract_eventbridge_rules(
        self, cluster_identifier: str
    ) -> List[ScheduledQuery]:
        """Extract EventBridge rules that target the Redshift cluster."""
        scheduled_queries = []
        
        try:
            # List all EventBridge rules
            paginator = self.events.get_paginator("list_rules")
            
            for page in paginator.paginate():
                for rule in page.get("Rules", []):
                    rule_name = rule.get("Name")
                    
                    # Check if this rule targets our cluster
                    if self._rule_targets_cluster(rule_name, cluster_identifier):
                        query_info = self._extract_query_from_rule(rule_name, rule)
                        if query_info:
                            scheduled_queries.append(query_info)
            
        except Exception as e:
            print(f"Warning: Could not extract EventBridge rules: {e}")
        
        return scheduled_queries

    def extract_eventbridge_scheduler(
        self, cluster_identifier: str
    ) -> List[ScheduledQuery]:
        """Extract schedules from EventBridge Scheduler."""
        scheduled_queries = []
        
        try:
            # List schedule groups
            groups_response = self.scheduler.list_schedule_groups()
            
            for group in groups_response.get("ScheduleGroups", []):
                group_name = group.get("Name")
                
                # List schedules in this group
                schedules_response = self.scheduler.list_schedules(
                    GroupName=group_name
                )
                
                for schedule in schedules_response.get("Schedules", []):
                    schedule_name = schedule.get("Name")
                    
                    # Get schedule details
                    schedule_detail = self.scheduler.get_schedule(
                        Name=schedule_name,
                        GroupName=group_name
                    )
                    
                    # Check if it targets our cluster
                    query_info = self._extract_query_from_scheduler(
                        schedule_detail, cluster_identifier
                    )
                    if query_info:
                        scheduled_queries.append(query_info)
            
        except Exception as e:
            print(f"Warning: Could not extract EventBridge Scheduler schedules: {e}")
        
        return scheduled_queries

    def _rule_targets_cluster(self, rule_name: str, cluster_identifier: str) -> bool:
        """Check if an EventBridge rule targets the specified cluster."""
        try:
            targets_response = self.events.list_targets_by_rule(Rule=rule_name)
            
            for target in targets_response.get("Targets", []):
                # Check if target is Redshift Data API
                if "redshift-data" in target.get("Arn", ""):
                    # Parse input to check cluster identifier
                    input_str = target.get("Input", "{}")
                    input_data = json.loads(input_str)
                    
                    if input_data.get("ClusterIdentifier") == cluster_identifier:
                        return True
            
        except Exception:
            pass
        
        return False

    def _extract_query_from_rule(
        self, rule_name: str, rule: Dict[str, Any]
    ) -> Optional[ScheduledQuery]:
        """Extract query details from an EventBridge rule."""
        try:
            targets_response = self.events.list_targets_by_rule(Rule=rule_name)
            
            for target in targets_response.get("Targets", []):
                if "redshift-data" in target.get("Arn", ""):
                    input_str = target.get("Input", "{}")
                    input_data = json.loads(input_str)
                    
                    return ScheduledQuery(
                        rule_name=rule_name,
                        schedule_expression=rule.get("ScheduleExpression", ""),
                        query=input_data.get("Sql", ""),
                        database=input_data.get("Database", ""),
                        enabled=rule.get("State") == "ENABLED",
                    )
            
        except Exception as e:
            print(f"Warning: Could not extract query from rule {rule_name}: {e}")
        
        return None

    def _extract_query_from_scheduler(
        self, schedule: Dict[str, Any], cluster_identifier: str
    ) -> Optional[ScheduledQuery]:
        """Extract query details from EventBridge Scheduler."""
        try:
            target = schedule.get("Target", {})
            
            # Check if it's a Redshift Data API target
            if "redshift-data" in target.get("Arn", ""):
                input_data = json.loads(target.get("Input", "{}"))
                
                if input_data.get("ClusterIdentifier") == cluster_identifier:
                    return ScheduledQuery(
                        rule_name=schedule.get("Name"),
                        schedule_expression=schedule.get("ScheduleExpression", ""),
                        query=input_data.get("Sql", ""),
                        database=input_data.get("Database", ""),
                        enabled=schedule.get("State") == "ENABLED",
                    )
            
        except Exception as e:
            print(f"Warning: Could not extract query from scheduler: {e}")
        
        return None

    def get_query_history(
        self, cluster_identifier: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent query execution history for the cluster."""
        try:
            response = self.redshift_data.list_statements(
                MaxResults=limit,
                Status="ALL"
            )
            
            statements = []
            for statement in response.get("Statements", []):
                # Filter by cluster identifier if available
                if statement.get("ClusterIdentifier") == cluster_identifier:
                    statements.append({
                        "id": statement.get("Id"),
                        "query": statement.get("QueryString"),
                        "database": statement.get("Database"),
                        "status": statement.get("Status"),
                        "created_at": statement.get("CreatedAt"),
                    })
            
            return statements
            
        except Exception as e:
            print(f"Warning: Could not get query history: {e}")
            return []
