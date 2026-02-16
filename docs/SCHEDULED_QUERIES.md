# Scheduled Queries Migration

## Overview

Scheduled queries in Redshift Provisioned clusters are typically implemented using:
- Amazon EventBridge Rules
- EventBridge Scheduler
- AWS Lambda functions
- Redshift Data API

This tool automatically migrates these scheduled queries to work with your Redshift Serverless workgroup.

## How It Works

### Detection

The tool scans for scheduled queries by:

1. **EventBridge Rules**: Searches for rules that target the Redshift Data API with your cluster identifier
2. **EventBridge Scheduler**: Checks scheduler schedules that execute queries on your cluster
3. **Target Validation**: Verifies that the target is your specific cluster

### Migration Process

1. **Extract**: Identifies all scheduled queries targeting the provisioned cluster
2. **Transform**: Updates the target from cluster identifier to workgroup name
3. **Create**: Creates new EventBridge Scheduler schedules for the serverless workgroup
4. **IAM Role**: Automatically creates or uses an IAM role for EventBridge to execute queries

## Usage

### Extract Scheduled Queries

```bash
redshift-migrate extract \
  --cluster-id my-cluster \
  --output config.json
```

The output includes scheduled query information:

```json
{
  "scheduled_queries": [
    {
      "rule_name": "daily-aggregation",
      "schedule_expression": "cron(0 2 * * ? *)",
      "query": "INSERT INTO summary SELECT ...",
      "database": "analytics",
      "enabled": true
    }
  ]
}
```

### Preview Migration

```bash
redshift-migrate apply \
  --config config.json \
  --workgroup my-workgroup \
  --namespace my-namespace \
  --dry-run
```

### Apply Scheduled Queries

```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --workgroup my-workgroup \
  --namespace my-namespace
```

## Schedule Expression Formats

The tool supports both EventBridge schedule formats:

### Cron Expressions
```
cron(0 2 * * ? *)  # Daily at 2 AM UTC
cron(0 */6 * * ? *)  # Every 6 hours
cron(0 0 ? * MON *)  # Every Monday at midnight
```

### Rate Expressions
```
rate(1 hour)   # Every hour
rate(30 minutes)  # Every 30 minutes
rate(7 days)   # Every 7 days
```

## IAM Permissions

### Required Permissions for Migration

Your AWS credentials need:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "events:ListRules",
        "events:ListTargetsByRule",
        "scheduler:ListSchedules",
        "scheduler:GetSchedule",
        "scheduler:CreateSchedule",
        "scheduler:UpdateSchedule",
        "iam:CreateRole",
        "iam:GetRole",
        "iam:PutRolePolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

### Execution Role

The tool automatically creates an IAM role named `RedshiftServerlessSchedulerRole` with permissions to:
- Execute Redshift Data API statements
- Describe statement status
- Get statement results

## Advanced Features

### Custom Execution Role

If you want to use a specific IAM role for query execution:

```python
from redshift_migrate.appliers import ScheduledQueryApplier

applier = ScheduledQueryApplier(region="us-east-1")
result = applier.apply_scheduled_queries(
    scheduled_queries=queries,
    workgroup_name="my-workgroup",
    namespace_name="my-namespace",
    execution_role_arn="arn:aws:iam::123456789012:role/MyCustomRole"
)
```

### Query Validation

Before migration, you can validate queries:

```python
from redshift_migrate.extractors import ScheduledQueryExtractor

extractor = ScheduledQueryExtractor(region="us-east-1")
queries = extractor.extract_eventbridge_rules("my-cluster")

for query in queries:
    print(f"Query: {query.rule_name}")
    print(f"Schedule: {query.schedule_expression}")
    print(f"SQL: {query.query[:100]}...")
```

## Limitations

### Not Migrated Automatically

The following are NOT automatically migrated:

1. **Lambda-based schedulers**: Custom Lambda functions that execute queries
2. **Third-party schedulers**: Apache Airflow, AWS Step Functions, etc.
3. **Application-level schedulers**: Queries scheduled within your application code
4. **Complex workflows**: Multi-step ETL processes with dependencies

For these cases, you'll need to manually update the target from cluster to workgroup.

## Best Practices

1. **Test Queries**: Validate that queries work in serverless before scheduling
2. **Monitor Execution**: Set up CloudWatch alarms for failed query executions
3. **Use Descriptive Names**: Name your schedules clearly for easy identification
4. **Document Dependencies**: Keep track of query dependencies and execution order
5. **Set Timeouts**: Configure appropriate timeouts for long-running queries

## Troubleshooting

### "No scheduled queries found"
- Queries may be scheduled outside of EventBridge
- Check Lambda functions, Step Functions, or application code
- Verify the cluster identifier matches exactly

### "Permission denied creating schedule"
- Ensure you have `scheduler:CreateSchedule` permission
- Check that the execution role can be created/accessed

### "Query execution failed"
- Verify the database name is correct for serverless
- Check that the workgroup has access to required resources
- Ensure IAM roles are properly configured

### "Schedule already exists"
- The tool will attempt to update existing schedules
- You can manually delete old schedules if needed

## Migration Checklist

- [ ] Extract scheduled queries from provisioned cluster
- [ ] Review query list and validate SQL
- [ ] Test queries manually in serverless workgroup
- [ ] Run migration in dry-run mode
- [ ] Apply scheduled queries
- [ ] Verify schedules are created in EventBridge
- [ ] Monitor first few executions
- [ ] Update documentation with new schedule names
- [ ] Disable/delete old provisioned cluster schedules

## Example: Complete Migration

```bash
# 1. Extract everything
redshift-migrate extract \
  --cluster-id prod-cluster \
  --output prod-config.json

# 2. Review scheduled queries
cat prod-config.json | jq '.scheduled_queries'

# 3. Dry-run migration
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --workgroup prod-serverless \
  --namespace prod-namespace \
  --dry-run

# 4. Apply migration
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --workgroup prod-serverless \
  --namespace prod-namespace

# 5. Verify in AWS Console
# Check EventBridge Scheduler for new schedules
```
