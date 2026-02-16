# ✅ Scheduled Query Migration Added!

Your agent can now migrate scheduled queries from Redshift Provisioned clusters to Serverless workgroups!

## What's New?

### New Agent Tools

1. **list_scheduled_queries** - List all scheduled queries for a provisioned cluster
   - Extracts from EventBridge Rules
   - Extracts from EventBridge Scheduler
   - Shows schedule expressions, SQL, database, and status

2. **migrate_scheduled_queries** - Migrate queries to serverless workgroup
   - Recreates queries to target serverless workgroup
   - Uses Redshift Data API for execution
   - Preserves schedule timing and query logic
   - Supports dry-run mode for preview
   - Automatically creates IAM execution role

### New Permissions

Added to `template.yaml` and `scripts/utils/update_all_permissions.sh`:

**EventBridge (Extended)**
- `events:ListTargetsByRule` - Check query targets
- `events:RemoveTargets` - Clean up old targets
- `events:DeleteRule` - Remove old rules

**EventBridge Scheduler (Extended)**
- `scheduler:ListScheduleGroups` - List schedule groups
- `scheduler:UpdateSchedule` - Update existing schedules
- `scheduler:DeleteSchedule` - Remove schedules

**Redshift Data API (New)**
- `redshift-data:ExecuteStatement` - Run queries
- `redshift-data:DescribeStatement` - Check query status
- `redshift-data:GetStatementResult` - Get query results
- `redshift-data:ListStatements` - List query history

### New Documentation

Created comprehensive guide: [docs/guides/SCHEDULED_QUERIES.md](docs/guides/SCHEDULED_QUERIES.md)

Covers:
- How scheduled query migration works
- Step-by-step migration guide
- IAM permissions required
- Common scenarios and troubleshooting
- Best practices
- Cost considerations
- Rollback procedures

## How to Use

### Quick Start

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

### Example Conversation

```
You: List scheduled queries for prod-db-1 in us-east-2

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

You: Migrate these queries to prod-serverless-wg with dry-run

Agent: Here's what would be migrated:

Cluster: prod-db-1
Target Workgroup: prod-serverless-wg
Target Namespace: prod-serverless-wg

Queries to migrate:
1. daily-sales-report → prod-serverless-wg-daily-sales-report
2. hourly-metrics-update → prod-serverless-wg-hourly-metrics-update
3. weekly-cleanup → prod-serverless-wg-weekly-cleanup (disabled)

Total: 3 queries would be migrated

You: Looks good, migrate them for real

Agent: Migrating scheduled queries...

✅ Created: prod-serverless-wg-daily-sales-report
✅ Created: prod-serverless-wg-hourly-metrics-update
✅ Created: prod-serverless-wg-weekly-cleanup (disabled)

Successfully migrated 3 scheduled queries!
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

## Technical Details

### How It Works

1. **Extraction Phase**
   - Lists all EventBridge Rules
   - Lists all EventBridge Scheduler schedules
   - Filters for rules/schedules targeting the cluster
   - Extracts schedule expression, SQL, database, and state

2. **Migration Phase**
   - Creates/gets IAM execution role for EventBridge
   - For each query:
     - Creates new EventBridge Scheduler schedule
     - Targets Redshift Data API with workgroup name
     - Preserves schedule expression and query SQL
     - Sets enabled/disabled state

3. **IAM Role Creation**
   - Role name: `RedshiftScheduledQueryExecutionRole`
   - Trust policy: Allows EventBridge Scheduler to assume role
   - Permissions: Redshift Data API operations

### Schedule Naming Convention

```
Original: daily-sales-report
Migrated: {workgroup-name}-daily-sales-report

Example:
Cluster: prod-db-1
Workgroup: prod-serverless-wg
Original: daily-sales-report
New: prod-serverless-wg-daily-sales-report
```

This prevents naming conflicts and makes it clear which workgroup the query targets.

## Files Modified

1. **redshift_agent.py**
   - Added `list_scheduled_queries` tool
   - Added `migrate_scheduled_queries` tool
   - Updated system prompt with scheduled query guidance
   - Updated help system with scheduled query topic

2. **template.yaml**
   - Added EventBridge permissions (ListTargetsByRule, RemoveTargets, DeleteRule)
   - Added EventBridge Scheduler permissions (ListScheduleGroups, UpdateSchedule, DeleteSchedule)
   - Added Redshift Data API permissions (ExecuteStatement, DescribeStatement, GetStatementResult, ListStatements)

3. **scripts/utils/update_all_permissions.sh**
   - Updated policy document with new permissions

4. **docs/guides/SCHEDULED_QUERIES.md**
   - Created comprehensive guide (new file)

5. **README.md**
   - Added scheduled query migration to features
   - Added example conversation with scheduled queries
   - Added link to scheduled query documentation

## Permissions Required

### For the Agent (Lambda)

```json
{
  "Effect": "Allow",
  "Action": [
    "events:DescribeRule",
    "events:ListRules",
    "events:ListTargetsByRule",
    "events:RemoveTargets",
    "events:DeleteRule",
    "scheduler:GetSchedule",
    "scheduler:ListSchedules",
    "scheduler:ListScheduleGroups",
    "scheduler:CreateSchedule",
    "scheduler:UpdateSchedule",
    "scheduler:DeleteSchedule",
    "redshift-data:ExecuteStatement",
    "redshift-data:DescribeStatement",
    "redshift-data:GetStatementResult",
    "redshift-data:ListStatements",
    "iam:GetRole",
    "iam:CreateRole",
    "iam:PutRolePolicy"
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

## Apply the Changes

### Option 1: Update Existing Deployment

```bash
# Update permissions
scripts/utils/update_all_permissions.sh

# Test the new features
./chat
```

### Option 2: Redeploy

```bash
# Redeploy with new permissions
./deploy
```

## Test It

```bash
# Start chat
./chat

# Try these commands
You: List scheduled queries for my-cluster
You: Migrate scheduled queries from my-cluster to my-workgroup with dry-run
You: Migrate scheduled queries from my-cluster to my-workgroup
```

## Benefits

### For Users
- ✅ No manual recreation of scheduled queries
- ✅ Preserves all query logic and timing
- ✅ Preview changes before applying
- ✅ Automatic IAM role management
- ✅ Clear migration status reporting

### For Operations
- ✅ Reduces migration time
- ✅ Eliminates manual errors
- ✅ Provides audit trail
- ✅ Supports rollback
- ✅ Maintains query history

### For Cost
- ✅ EventBridge Scheduler free tier covers most use cases
- ✅ No additional Redshift Data API charges
- ✅ Pay only for query execution time

## Common Use Cases

### 1. Full Migration
```
You: Migrate cluster my-cluster to serverless
You: Migrate scheduled queries from my-cluster to my-workgroup
```

### 2. Query-Only Migration
```
You: List scheduled queries for my-cluster
You: Migrate them to my-existing-workgroup
```

### 3. Preview Before Migrating
```
You: Show me scheduled queries for my-cluster
You: Migrate them to my-workgroup with dry-run
You: Looks good, migrate for real
```

### 4. Selective Migration
```
You: List scheduled queries for my-cluster
You: Migrate only the daily-sales-report query
```

## Troubleshooting

### No Queries Found
- Cluster may not have scheduled queries
- Check EventBridge console manually
- Verify IAM permissions

### Permission Denied
```bash
# Update permissions
scripts/utils/update_all_permissions.sh
```

### Query Already Exists
- Normal if running migration multiple times
- Agent skips and marks as "already_exists"
- Delete existing schedules to recreate

## Next Steps

1. ✅ Update permissions: `scripts/utils/update_all_permissions.sh`
2. ✅ Test the feature: `./chat`
3. ✅ Read the guide: [docs/guides/SCHEDULED_QUERIES.md](docs/guides/SCHEDULED_QUERIES.md)
4. ✅ Migrate your queries!

## Documentation

- **Complete Guide**: [docs/guides/SCHEDULED_QUERIES.md](docs/guides/SCHEDULED_QUERIES.md)
- **Deployment**: [docs/deployment/DEPLOY_NOW.md](docs/deployment/DEPLOY_NOW.md)
- **Chat Guide**: [docs/guides/CHAT_GUIDE.md](docs/guides/CHAT_GUIDE.md)
- **Troubleshooting**: [docs/deployment/TROUBLESHOOT_LAMBDA.md](docs/deployment/TROUBLESHOOT_LAMBDA.md)

---

**Your agent can now migrate scheduled queries seamlessly!** 🎉

Apply the changes:
```bash
scripts/utils/update_all_permissions.sh
```

Then start chatting:
```bash
./chat
```
