# Migrating Scheduled Queries to Redshift Serverless

Complete guide for migrating scheduled queries from Redshift Provisioned clusters to Redshift Serverless workgroups.

## Overview

Scheduled queries in Redshift Provisioned clusters are typically implemented using:
- EventBridge Rules
- EventBridge Scheduler
- Redshift Data API

When migrating to Serverless, these queries need to be recreated to target the new workgroup instead of the provisioned cluster.

## Quick Start

```bash
# Start the chat interface
./chat

# List scheduled queries
You: List scheduled queries for cluster my-cluster in us-east-2

# Preview migration
You: Migrate scheduled queries from my-cluster to my-workgroup with dry-run

# Perform migration
You: Migrate scheduled queries from my-cluster to my-workgroup
```

## How It Works

### 1. Extraction
The agent extracts scheduled queries from:
- **EventBridge Rules**: Traditional scheduled rules
- **EventBridge Scheduler**: Modern scheduler service

For each query, it captures:
- Schedule expression (cron or rate)
- SQL query text
- Target database
- Enabled/disabled state

### 2. Migration
The agent recreates each query to target the serverless workgroup:
- Creates new EventBridge Scheduler schedules
- Updates target from cluster to workgroup
- Uses Redshift Data API for serverless execution
- Preserves schedule timing and query logic
- Maintains enabled/disabled state

### 3. IAM Role Creation
If needed, the agent creates an IAM role for EventBridge to execute queries:
- Role name: `RedshiftScheduledQueryExecutionRole`
- Allows EventBridge Scheduler to assume the role
- Grants permissions for Redshift Data API operations

## Step-by-Step Guide

### Step 1: List Scheduled Queries

First, see what queries exist on your provisioned cluster:

```bash
./chat
```

```
You: List scheduled queries for cluster prod-db-1 in us-east-2

Agent: I found 3 scheduled queries for cluster 'prod-db-1':

1. daily-sales-report
   - Type: EventBridge Scheduler
   - Schedule: cron(0 8 * * ? *)
   - Database: sales
   - Status: Enabled

2. hourly-metrics-update
   - Type: EventBridge Rule
   - Schedule: rate(1 hour)
   - Database: metrics
   - Status: Enabled

3. weekly-cleanup
   - Type: EventBridge Scheduler
   - Schedule: cron(0 2 ? * SUN *)
   - Database: admin
   - Status: Disabled
```

### Step 2: Preview Migration (Dry Run)

Preview what will happen without making changes:

```
You: Migrate scheduled queries from prod-db-1 to prod-serverless-wg with dry-run

Agent: Here's what would be migrated:

Cluster: prod-db-1
Target Workgroup: prod-serverless-wg
Target Namespace: prod-serverless-wg

Queries to migrate:
1. daily-sales-report → prod-serverless-wg-daily-sales-report
   - Schedule: cron(0 8 * * ? *)
   - Database: sales
   - Status: Would be created

2. hourly-metrics-update → prod-serverless-wg-hourly-metrics-update
   - Schedule: rate(1 hour)
   - Database: metrics
   - Status: Would be created

3. weekly-cleanup → prod-serverless-wg-weekly-cleanup
   - Schedule: cron(0 2 ? * SUN *)
   - Database: admin
   - Status: Would be created (disabled)

Total: 3 queries would be migrated
```

### Step 3: Perform Migration

Execute the migration:

```
You: Migrate scheduled queries from prod-db-1 to prod-serverless-wg in us-east-2

Agent: Migrating scheduled queries...

✅ Created: prod-serverless-wg-daily-sales-report
✅ Created: prod-serverless-wg-hourly-metrics-update
✅ Created: prod-serverless-wg-weekly-cleanup (disabled)

Successfully migrated 3 scheduled queries!

The queries now target your serverless workgroup 'prod-serverless-wg'.
You can view them in the EventBridge Scheduler console.
```

### Step 4: Verify Migration

Check the migrated queries:

```
You: List EventBridge schedules for workgroup prod-serverless-wg

Agent: Found 3 schedules targeting workgroup 'prod-serverless-wg':

1. prod-serverless-wg-daily-sales-report
   - Schedule: cron(0 8 * * ? *)
   - State: ENABLED
   - Next run: Tomorrow at 8:00 AM

2. prod-serverless-wg-hourly-metrics-update
   - Schedule: rate(1 hour)
   - State: ENABLED
   - Next run: In 45 minutes

3. prod-serverless-wg-weekly-cleanup
   - Schedule: cron(0 2 ? * SUN *)
   - State: DISABLED
```

## What Gets Migrated

### Preserved
- ✅ Schedule expression (cron/rate)
- ✅ SQL query text
- ✅ Target database
- ✅ Enabled/disabled state
- ✅ Query logic and parameters

### Changed
- 🔄 Target: Cluster → Workgroup
- 🔄 Execution method: Cluster endpoint → Redshift Data API
- 🔄 Schedule name: Prefixed with workgroup name
- 🔄 IAM role: Uses new execution role

### Not Migrated
- ❌ Query execution history
- ❌ CloudWatch logs (new logs will be created)
- ❌ Original EventBridge rules (kept for rollback)

## Schedule Naming Convention

Original queries are renamed to avoid conflicts:

```
Original: daily-sales-report
Migrated: {workgroup-name}-daily-sales-report

Example:
Cluster: prod-db-1
Workgroup: prod-serverless-wg
Original: daily-sales-report
New: prod-serverless-wg-daily-sales-report
```

## IAM Permissions Required

### For the Agent (Lambda)
```json
{
  "Effect": "Allow",
  "Action": [
    "events:DescribeRule",
    "events:ListRules",
    "events:ListTargetsByRule",
    "scheduler:GetSchedule",
    "scheduler:ListSchedules",
    "scheduler:ListScheduleGroups",
    "scheduler:CreateSchedule",
    "scheduler:UpdateSchedule",
    "iam:GetRole",
    "iam:CreateRole",
    "iam:PutRolePolicy",
    "redshift-data:ExecuteStatement",
    "redshift-data:DescribeStatement",
    "redshift-data:ListStatements"
  ],
  "Resource": "*"
}
```

### For EventBridge Execution Role
The agent creates this role automatically:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "redshift-data:ExecuteStatement",
      "redshift-data:DescribeStatement",
      "redshift-data:GetStatementResult"
    ],
    "Resource": "*"
  }]
}
```

## Common Scenarios

### Scenario 1: Migrate All Queries
```
You: Migrate all scheduled queries from my-cluster to my-workgroup
```

### Scenario 2: Preview Before Migrating
```
You: Show me what scheduled queries exist on my-cluster
You: Migrate them to my-workgroup with dry-run
You: Looks good, migrate them for real
```

### Scenario 3: Migrate to Different Namespace
```
You: Migrate scheduled queries from my-cluster to workgroup my-wg and namespace my-ns
```

### Scenario 4: Check Migration Status
```
You: List EventBridge schedules for my-workgroup
```

## Troubleshooting

### No Queries Found

**Problem:** "No scheduled queries found for cluster 'my-cluster'"

**Causes:**
- Cluster has no scheduled queries
- Queries use different scheduling mechanism
- Insufficient permissions to list EventBridge resources

**Solution:**
```bash
# Check EventBridge console manually
# Verify IAM permissions include events:ListRules and scheduler:ListSchedules
```

### Permission Denied

**Problem:** "User is not authorized to perform: scheduler:CreateSchedule"

**Solution:**
```bash
# Update permissions
scripts/utils/update_all_permissions.sh
```

### Query Already Exists

**Problem:** "ConflictException: Schedule already exists"

**Behavior:** Agent skips the query and marks it as "already_exists"

**Solution:**
- This is normal if you run migration multiple times
- Delete existing schedules if you want to recreate them
- Or use different workgroup name

### Execution Role Creation Failed

**Problem:** "Cannot create IAM role"

**Causes:**
- Insufficient IAM permissions
- Role name already exists with different trust policy

**Solution:**
```bash
# Check if role exists
aws iam get-role --role-name RedshiftScheduledQueryExecutionRole

# If it exists with wrong policy, delete and recreate
aws iam delete-role --role-name RedshiftScheduledQueryExecutionRole

# Run migration again
```

## Best Practices

### 1. Test in Non-Production First
```
You: Migrate queries from dev-cluster to dev-workgroup with dry-run
You: Verify the preview looks correct
You: Migrate for real
You: Test one query execution manually
```

### 2. Migrate During Low-Traffic Period
- Schedule migrations during maintenance windows
- Queries will have brief downtime during migration
- Original queries continue running until you disable them

### 3. Keep Original Queries Temporarily
- Original EventBridge rules are not deleted
- Keep them for rollback if needed
- Disable them after verifying serverless queries work
- Delete after successful migration

### 4. Monitor After Migration
```bash
# Check CloudWatch Logs for query executions
aws logs tail /aws/events/scheduler --follow

# Check Redshift Data API query history
aws redshift-data list-statements --status ALL
```

### 5. Update Query Logic If Needed
Some queries may need updates for serverless:
- Remove cluster-specific parameters
- Update connection strings if hardcoded
- Adjust resource limits for serverless

## Schedule Expression Reference

### Cron Expressions
```
cron(0 8 * * ? *)     # Daily at 8:00 AM
cron(0 */4 * * ? *)   # Every 4 hours
cron(0 0 ? * MON *)   # Every Monday at midnight
cron(0 2 1 * ? *)     # First day of month at 2:00 AM
```

### Rate Expressions
```
rate(1 hour)          # Every hour
rate(30 minutes)      # Every 30 minutes
rate(1 day)           # Daily
rate(7 days)          # Weekly
```

## Rollback

If you need to rollback:

### Option 1: Disable Serverless Queries
```bash
# Disable all schedules for a workgroup
aws scheduler list-schedules --name-prefix prod-serverless-wg- \
  --query 'Schedules[].Name' --output text | \
  xargs -I {} aws scheduler update-schedule --name {} --state DISABLED
```

### Option 2: Re-enable Original Queries
```bash
# Re-enable original EventBridge rules
aws events enable-rule --name daily-sales-report
```

### Option 3: Delete Serverless Queries
```bash
# Delete all schedules for a workgroup
aws scheduler list-schedules --name-prefix prod-serverless-wg- \
  --query 'Schedules[].Name' --output text | \
  xargs -I {} aws scheduler delete-schedule --name {}
```

## Cost Considerations

### EventBridge Scheduler Pricing
- $1.00 per million invocations
- First 14 million invocations per month are free
- Most migrations will stay within free tier

### Redshift Data API Pricing
- No additional charge for Data API calls
- You pay for Redshift Serverless compute (RPU-hours)
- Queries consume RPUs while running

### Example Cost
```
Scenario: 100 queries running hourly
- Invocations per month: 100 × 24 × 30 = 72,000
- EventBridge cost: $0 (within free tier)
- Redshift cost: Based on query execution time and RPU usage
```

## Next Steps

After migrating scheduled queries:

1. ✅ Verify queries are running correctly
2. ✅ Monitor CloudWatch Logs for errors
3. ✅ Update any external monitoring/alerting
4. ✅ Disable original EventBridge rules
5. ✅ Delete original rules after verification period
6. ✅ Update documentation with new schedule names

## Related Documentation

- [Migration Guide](CHAT_GUIDE.md)
- [Deployment Guide](../deployment/DEPLOY_NOW.md)
- [Troubleshooting](../deployment/TROUBLESHOOT_LAMBDA.md)
- [AWS EventBridge Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html)
- [Redshift Data API](https://docs.aws.amazon.com/redshift/latest/mgmt/data-api.html)

---

**Quick Commands:**

```bash
# List queries
./chat → "List scheduled queries for my-cluster"

# Preview migration
./chat → "Migrate queries from my-cluster to my-wg with dry-run"

# Migrate
./chat → "Migrate queries from my-cluster to my-wg"
```

**Your scheduled queries will continue running seamlessly on serverless!** 🎉
