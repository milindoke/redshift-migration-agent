"""Apply scheduled queries to Redshift Serverless."""

import boto3
import json
from typing import List, Dict, Any, Optional
from ..models import ScheduledQuery


class ScheduledQueryApplier:
    """Apply scheduled queries to Redshift Serverless workgroup."""

    def __init__(self, region: Optional[str] = None, dry_run: bool = False):
        self.events = boto3.client("events", region_name=region)
        self.scheduler = boto3.client("scheduler", region_name=region)
        self.iam = boto3.client("iam", region_name=region)
        self.region = region or boto3.Session().region_name
        self.dry_run = dry_run

    def apply_scheduled_queries(
        self,
        scheduled_queries: List[ScheduledQuery],
        workgroup_name: str,
        namespace_name: str,
        execution_role_arn: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply scheduled queries to serverless workgroup."""
        if self.dry_run:
            return self._dry_run_report(scheduled_queries, workgroup_name)
        
        results = {
            "created": [],
            "failed": [],
            "skipped": [],
        }
        
        for query in scheduled_queries:
            try:
                result = self._create_scheduled_query(
                    query,
                    workgroup_name,
                    namespace_name,
                    execution_role_arn,
                )
                results["created"].append({
                    "rule_name": query.rule_name,
                    "result": result,
                })
            except Exception as e:
                results["failed"].append({
                    "rule_name": query.rule_name,
                    "error": str(e),
                })
        
        return results

    def _create_scheduled_query(
        self,
        query: ScheduledQuery,
        workgroup_name: str,
        namespace_name: str,
        execution_role_arn: Optional[str],
    ) -> Dict[str, Any]:
        """Create a scheduled query using EventBridge Scheduler."""
        # Prepare the target configuration for Redshift Data API
        target_input = {
            "WorkgroupName": workgroup_name,
            "Database": query.database,
            "Sql": query.query,
        }
        
        # Create schedule name (prefix with serverless workgroup name)
        schedule_name = f"{workgroup_name}-{query.rule_name}"
        
        # Get or create execution role
        if not execution_role_arn:
            execution_role_arn = self._get_or_create_execution_role()
        
        try:
            # Use EventBridge Scheduler (newer, more flexible)
            response = self.scheduler.create_schedule(
                Name=schedule_name,
                ScheduleExpression=query.schedule_expression,
                State="ENABLED" if query.enabled else "DISABLED",
                FlexibleTimeWindow={"Mode": "OFF"},
                Target={
                    "Arn": f"arn:aws:redshift:{self.region}:*:workgroup:{workgroup_name}",
                    "RoleArn": execution_role_arn,
                    "Input": json.dumps(target_input),
                    "RedshiftDataParameters": {
                        "Database": query.database,
                        "Sql": query.query,
                    },
                },
                Description=f"Migrated from provisioned cluster - {query.rule_name}",
            )
            return {"status": "created", "schedule_arn": response.get("ScheduleArn")}
            
        except self.scheduler.exceptions.ConflictException:
            # Schedule already exists, try to update it
            return self._update_scheduled_query(
                schedule_name, query, workgroup_name, execution_role_arn
            )

    def _update_scheduled_query(
        self,
        schedule_name: str,
        query: ScheduledQuery,
        workgroup_name: str,
        execution_role_arn: str,
    ) -> Dict[str, Any]:
        """Update an existing scheduled query."""
        target_input = {
            "WorkgroupName": workgroup_name,
            "Database": query.database,
            "Sql": query.query,
        }
        
        response = self.scheduler.update_schedule(
            Name=schedule_name,
            ScheduleExpression=query.schedule_expression,
            State="ENABLED" if query.enabled else "DISABLED",
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": f"arn:aws:redshift:{self.region}:*:workgroup:{workgroup_name}",
                "RoleArn": execution_role_arn,
                "Input": json.dumps(target_input),
                "RedshiftDataParameters": {
                    "Database": query.database,
                    "Sql": query.query,
                },
            },
        )
        return {"status": "updated", "schedule_arn": response.get("ScheduleArn")}

    def _get_or_create_execution_role(self) -> str:
        """Get or create an IAM role for EventBridge to execute Redshift queries."""
        role_name = "RedshiftServerlessSchedulerRole"
        
        try:
            # Try to get existing role
            response = self.iam.get_role(RoleName=role_name)
            return response["Role"]["Arn"]
        except self.iam.exceptions.NoSuchEntityException:
            # Create the role
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "scheduler.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
            
            response = self.iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Role for EventBridge Scheduler to execute Redshift queries",
            )
            
            # Attach policy for Redshift Data API
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "redshift-data:ExecuteStatement",
                            "redshift-data:DescribeStatement",
                            "redshift-data:GetStatementResult",
                        ],
                        "Resource": "*",
                    }
                ],
            }
            
            self.iam.put_role_policy(
                RoleName=role_name,
                PolicyName="RedshiftDataAPIAccess",
                PolicyDocument=json.dumps(policy_document),
            )
            
            return response["Role"]["Arn"]

    def _dry_run_report(
        self, scheduled_queries: List[ScheduledQuery], workgroup_name: str
    ) -> Dict[str, Any]:
        """Generate a dry-run report for scheduled queries."""
        return {
            "dry_run": True,
            "workgroup_name": workgroup_name,
            "scheduled_queries": [
                {
                    "rule_name": query.rule_name,
                    "schedule": query.schedule_expression,
                    "database": query.database,
                    "query_preview": query.query[:100] + "..." if len(query.query) > 100 else query.query,
                    "enabled": query.enabled,
                    "action": "create",
                }
                for query in scheduled_queries
            ],
            "total_queries": len(scheduled_queries),
        }

    def delete_scheduled_query(self, schedule_name: str) -> Dict[str, Any]:
        """Delete a scheduled query."""
        if self.dry_run:
            return {"dry_run": True, "action": "delete", "schedule_name": schedule_name}
        
        try:
            self.scheduler.delete_schedule(Name=schedule_name)
            return {"status": "deleted", "schedule_name": schedule_name}
        except Exception as e:
            return {"status": "error", "error": str(e)}
