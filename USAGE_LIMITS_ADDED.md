# ✅ Usage Limits Migration Added!

Your agent can now extract and carry over usage limits from provisioned clusters to serverless workgroups with intelligent recommendations!

## What's New?

### New Agent Tools

1. **get_cluster_usage_limits** - Extract usage limits from provisioned cluster
   - Shows spectrum limits (data scanned)
   - Shows concurrency scaling limits (time)
   - Shows cross-region datasharing limits (data transferred)
   - Displays limit amounts, periods, and breach actions

2. **create_serverless_usage_limit** - Create usage limit for serverless workgroup
   - Sets RPU-hour limits for compute usage
   - Supports daily, weekly, monthly periods
   - Configurable breach actions (log, emit-metric, deactivate)

3. **migrate_usage_limits_to_serverless** - Get intelligent recommendations
   - Analyzes provisioned cluster usage limits
   - Provides equivalent serverless recommendations
   - Explains reasoning for each recommendation
   - Supports dry-run mode

### New Data Models

Updated models to include:
- `UsageLimit` class with limit_id, feature_type, limit_type, amount, period, breach_action
- `usage_limits` field in `ProvisionedClusterConfig`
- `_extract_usage_limits()` method in provisioned extractor

### New Permissions

Added to `template.yaml` and `scripts/utils/update_all_permissions.sh`:

**Redshift (Extended)**
- `redshift:DescribeUsageLimits` - List usage limits for provisioned clusters

**Redshift Serverless (Extended)**
- `redshift-serverless:CreateUsageLimit` - Create usage limits
- `redshift-serverless:UpdateUsageLimit` - Update usage limits
- `redshift-serverless:DeleteUsageLimit` - Delete usage limits
- `redshift-serverless:ListUsageLimits` - List usage limits

### New Documentation

Created comprehensive guide: [docs/guides/USAGE_LIMITS.md](docs/guides/USAGE_LIMITS.md)

Covers:
- Understanding usage limits and RPU-hours
- Checking current usage limits
- Migration recommendations
- Creating serverless usage limits
- Monitoring and alerting
- Cost estimation
- Best practices

## How to Use

### Quick Start

```bash
# Start the chat interface
./chat

# Check usage limits
You: Get usage limits for cluster my-cluster in us-east-2

# Get recommendations
You: Migrate usage limits from my-cluster to my-workgroup with dry-run

# Create serverless limit
You: Create usage limit for workgroup my-workgroup with 60 RPU-hours per day
```

### Example Conversation

```
You: Get usage limits for prod-db-1 in us-east-2

Agent: Here are the usage limits for cluster 'prod-db-1':

{
  "cluster_id": "prod-db-1",
  "usage_limits_count": 2,
  "usage_limits": [
    {
      "limit_id": "limit-abc123",
      "feature_type": "concurrency-scaling",
      "limit_type": "time",
      "amount": 60,
      "period": "daily",
      "breach_action": "log"
    },
    {
      "limit_id": "limit-def456",
      "feature_type": "spectrum",
      "limit_type": "data-scanned",
      "amount": 100,
      "period": "monthly",
      "breach_action": "emit-metric"
    }
  ]
}

You: Migrate usage limits from prod-db-1 to prod-serverless-wg with dry-run

Agent: Analyzing usage limits and providing recommendations...

{
  "provisioned_limits": [
    {
      "feature_type": "concurrency-scaling",
      "limit_type": "time",
      "amount": 60,
      "period": "daily",
      "breach_action": "log"
    }
  ],
  "serverless_recommendations": [
    {
      "usage_type": "serverless-compute",
      "amount": 120,
      "period": "daily",
      "breach_action": "log",
      "reason": "Cluster has concurrency scaling limits - recommended 120 RPU-hours/day"
    }
  ],
  "notes": [
    "Provisioned usage limits don't directly map to serverless",
    "Serverless uses RPU-hours for compute limits"
  ]
}

Recommendation: Set a daily limit of 120 RPU-hours for your serverless workgroup.

You: Create usage limit for workgroup prod-serverless-wg with 120 RPU-hours per day and emit-metric action

Agent: Creating usage limit...

{
  "status": "success",
  "workgroup_name": "prod-serverless-wg",
  "usage_limit_id": "limit-xyz789",
  "usage_type": "serverless-compute",
  "amount": 120,
  "period": "daily",
  "breach_action": "emit-metric",
  "message": "Usage limit created for workgroup 'prod-serverless-wg'"
}

✅ Usage limit created! CloudWatch metrics will be emitted when you exceed 120 RPU-hours per day.
```

## Key Differences: Provisioned vs Serverless

### Provisioned Cluster Limits

| Feature Type | Measures | Unit |
|--------------|----------|------|
| spectrum | Data scanned | TB |
| concurrency-scaling | Time using scaling | Minutes |
| cross-region-datasharing | Data transferred | TB |

### Serverless Workgroup Limits

| Usage Type | Measures | Unit |
|------------|----------|------|
| serverless-compute | Compute usage | RPU-hours |

## What Gets Migrated

### Extracted from Provisioned
- ✅ Feature type (spectrum, concurrency-scaling, datasharing)
- ✅ Limit type (time, data-scanned)
- ✅ Amount (numeric value)
- ✅ Period (daily, weekly, monthly)
- ✅ Breach action (log, emit-metric, disable)

### Recommendations for Serverless
- 🔄 Usage type: Always "serverless-compute"
- 🔄 Amount: Intelligent recommendation based on provisioned limits
- 🔄 Period: Preserved from provisioned (daily, weekly, monthly)
- 🔄 Breach action: Mapped (disable → deactivate)

### Recommendation Logic

**Has Concurrency Scaling Limit:**
- Recommended: 120 RPU-hours per day
- Reason: Indicates burst workload needs

**Has Spectrum Limit:**
- Recommended: 60 RPU-hours per day
- Reason: Spectrum queries consume compute

**No Limits:**
- Recommended: 60 RPU-hours per day
- Reason: Standard recommendation for cost control

## Technical Details

### RPU-hours Explained

RPU (Redshift Processing Unit) = Compute + Memory resources

Examples:
- 8 RPUs × 2 hours = 16 RPU-hours
- 16 RPUs × 0.5 hours = 8 RPU-hours
- 32 RPUs × 1 hour = 32 RPU-hours

### Breach Actions

**log** - Monitor only
- Logs breach to CloudWatch Logs
- Workgroup continues running
- Use for: Initial monitoring

**emit-metric** - Alert
- Emits CloudWatch metric
- Workgroup continues running
- Use for: Production alerting

**deactivate** - Hard stop
- Stops the workgroup
- Prevents further usage
- Use for: Strict cost control

## Files Modified

1. **redshift_agent.py**
   - Added `get_cluster_usage_limits` tool
   - Added `create_serverless_usage_limit` tool
   - Added `migrate_usage_limits_to_serverless` tool
   - Updated system prompt with usage limits guidance
   - Updated help system with usage_limits topic

2. **src/redshift_migrate/models.py**
   - Added `UsageLimit` class
   - Added `usage_limits` field to `ProvisionedClusterConfig`

3. **src/redshift_migrate/extractors/provisioned.py**
   - Added `_extract_usage_limits` method
   - Updated `extract` method to capture usage limits

4. **template.yaml**
   - Added Redshift DescribeUsageLimits permission
   - Added Redshift Serverless usage limit permissions

5. **scripts/utils/update_all_permissions.sh**
   - Updated policy document with usage limit permissions

6. **docs/guides/USAGE_LIMITS.md**
   - Created comprehensive guide (new file)

7. **README.md**
   - Added usage limits migration to features
   - Added example conversation
   - Added link to documentation

## Permissions Required

### For Provisioned Cluster

```json
{
  "Effect": "Allow",
  "Action": [
    "redshift:DescribeUsageLimits"
  ],
  "Resource": "*"
}
```

### For Serverless Workgroup

```json
{
  "Effect": "Allow",
  "Action": [
    "redshift-serverless:CreateUsageLimit",
    "redshift-serverless:UpdateUsageLimit",
    "redshift-serverless:ListUsageLimits",
    "redshift-serverless:DeleteUsageLimit"
  ],
  "Resource": "*"
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
You: Get usage limits for my-cluster
You: Migrate usage limits from my-cluster to my-wg with dry-run
You: Create usage limit for workgroup my-wg with 60 RPU-hours per day
```

## Benefits

### For Users
- ✅ Intelligent recommendations for serverless limits
- ✅ No manual calculation of RPU-hours needed
- ✅ Clear explanation of recommendations
- ✅ Dry-run mode to preview before creating
- ✅ Cost control from day one

### For Operations
- ✅ Prevents runaway costs
- ✅ CloudWatch integration for monitoring
- ✅ Flexible breach actions
- ✅ Multiple period options (daily, weekly, monthly)
- ✅ Easy to adjust as needs change

### For Cost Management
- ✅ Predictable monthly costs
- ✅ Automatic alerts on overages
- ✅ Option to hard-stop on breach
- ✅ Granular control per workgroup

## Common Use Cases

### 1. Development Workload

```
You: Create usage limit for workgroup dev-wg with 30 RPU-hours per day and log action
```

Cost: ~$337/month (30 × $0.375 × 30 days)

### 2. Production Workload

```
You: Create usage limit for workgroup prod-wg with 120 RPU-hours per day and emit-metric action
```

Cost: ~$1,350/month (120 × $0.375 × 30 days)

### 3. Batch Processing

```
You: Create usage limit for workgroup batch-wg with 500 RPU-hours per week and deactivate action
```

Cost: ~$750/month (500 × $0.375 × 4 weeks)

### 4. Cost-Sensitive Environment

```
You: Create usage limit for workgroup test-wg with 10 RPU-hours per day and deactivate action
```

Cost: ~$112/month (10 × $0.375 × 30 days)

## Monitoring and Alerting

### CloudWatch Metrics

When using `emit-metric` breach action:
- Namespace: `AWS/Redshift-Serverless`
- Metric: `UsageLimitBreach`
- Dimensions: WorkgroupName, UsageLimitId

### CloudWatch Logs

When using `log` breach action:
- Log Group: `/aws/redshift-serverless/workgroup/{workgroup-name}`
- Contains breach event details

### Setting Up Alerts

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name serverless-usage-breach \
  --metric-name UsageLimitBreach \
  --namespace AWS/Redshift-Serverless \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold
```

## Troubleshooting

### Permission Denied

**Problem:** "User is not authorized to perform: redshift-serverless:CreateUsageLimit"

**Solution:**
```bash
scripts/utils/update_all_permissions.sh
```

### Workgroup Deactivated

**Problem:** Workgroup stopped due to usage limit breach

**Solution:**
1. Check CloudWatch Logs for details
2. Increase limit or change breach action
3. Reactivate workgroup

### No Recommendations

**Problem:** "No usage limits found on provisioned cluster"

**Solution:** Agent provides default recommendation of 60 RPU-hours per day

## Next Steps

1. ✅ Update permissions: `scripts/utils/update_all_permissions.sh`
2. ✅ Test the feature: `./chat`
3. ✅ Read the guide: [docs/guides/USAGE_LIMITS.md](docs/guides/USAGE_LIMITS.md)
4. ✅ Set up usage limits for cost control!

## Documentation

- **Complete Guide**: [docs/guides/USAGE_LIMITS.md](docs/guides/USAGE_LIMITS.md)
- **Maintenance & Snapshots**: [docs/guides/MAINTENANCE_AND_SNAPSHOTS.md](docs/guides/MAINTENANCE_AND_SNAPSHOTS.md)
- **Scheduled Queries**: [docs/guides/SCHEDULED_QUERIES.md](docs/guides/SCHEDULED_QUERIES.md)
- **Deployment**: [docs/deployment/DEPLOY_NOW.md](docs/deployment/DEPLOY_NOW.md)

---

**Your agent can now migrate usage limits with intelligent recommendations!** 🎉

Apply the changes:
```bash
scripts/utils/update_all_permissions.sh
```

Then start chatting:
```bash
./chat
```
