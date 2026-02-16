# Migrating Usage Limits to Redshift Serverless

Complete guide for migrating usage limits from Redshift Provisioned clusters to Redshift Serverless workgroups.

## Overview

Usage limits control resource consumption and costs by setting thresholds on specific features. When migrating from Provisioned to Serverless, usage limit types change significantly.

### Provisioned Cluster Usage Limits
- **Spectrum**: Limit data scanned by Redshift Spectrum queries (in TB)
- **Concurrency Scaling**: Limit time using concurrency scaling clusters (in minutes)
- **Cross-Region Datasharing**: Limit data transferred for datasharing (in TB)

### Serverless Workgroup Usage Limits
- **Serverless Compute**: Limit RPU-hours consumed by the workgroup

## Quick Start

```bash
# Start the chat interface
./chat

# Check usage limits
You: Get usage limits for cluster my-cluster in us-east-2

# Get migration recommendations
You: Migrate usage limits from my-cluster to my-workgroup with dry-run

# Create serverless usage limit
You: Create usage limit for workgroup my-workgroup with 60 RPU-hours per day
```

## Understanding Usage Limits

### What are RPU-hours?

RPU (Redshift Processing Unit) is the unit of compute capacity in Serverless:
- 1 RPU = Compute and memory resources
- RPU-hours = RPUs × hours of usage
- Example: 8 RPUs running for 2 hours = 16 RPU-hours

### Common Usage Limit Scenarios

**Light Usage (Development/Testing)**
- 30-60 RPU-hours per day
- Breach action: log (monitor only)

**Medium Usage (Production)**
- 100-200 RPU-hours per day
- Breach action: emit-metric (alert on breach)

**Heavy Usage (Enterprise)**
- 300+ RPU-hours per day
- Breach action: deactivate (stop on breach)

## Checking Current Usage Limits

```bash
./chat
```

```
You: Get usage limits for cluster prod-db-1 in us-east-2

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

The cluster has 2 usage limits configured:
1. Concurrency scaling limited to 60 minutes per day
2. Spectrum limited to 100 TB scanned per month
```

## Migration Recommendations

Since provisioned and serverless use different limit types, the agent provides intelligent recommendations:

```
You: Migrate usage limits from prod-db-1 to prod-serverless-wg with dry-run

Agent: Analyzing usage limits and providing recommendations...

{
  "cluster_id": "prod-db-1",
  "workgroup_name": "prod-serverless-wg",
  "dry_run": true,
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
  ],
  "total_provisioned_limits": 1,
  "total_recommendations": 1
}

Recommendation: Set a daily limit of 120 RPU-hours for your serverless workgroup.
```

## Creating Serverless Usage Limits

### Basic Usage Limit

```
You: Create usage limit for workgroup my-workgroup with 60 RPU-hours per day

Agent: Creating usage limit...

{
  "status": "success",
  "workgroup_name": "my-workgroup",
  "usage_limit_id": "limit-xyz789",
  "usage_type": "serverless-compute",
  "amount": 60,
  "period": "daily",
  "breach_action": "log",
  "message": "Usage limit created for workgroup 'my-workgroup'"
}

✅ Usage limit created! Your workgroup will log when it exceeds 60 RPU-hours per day.
```

### With Different Breach Actions

**Log Only (Monitor)**
```
You: Create usage limit for workgroup my-wg with 100 RPU-hours per day and log action
```

**Emit Metric (Alert)**
```
You: Create usage limit for workgroup my-wg with 100 RPU-hours per day and emit-metric action
```

**Deactivate (Stop)**
```
You: Create usage limit for workgroup my-wg with 100 RPU-hours per day and deactivate action
```

## Complete Migration Example

```
You: Get usage limits for prod-db-1 in us-east-2

Agent: [Shows 2 usage limits: concurrency-scaling and spectrum]

You: Migrate prod-db-1 to serverless

Agent: [Performs migration...]

✅ Migration complete!
- Namespace: prod-db-1
- Workgroup: prod-db-1

You: Migrate usage limits from prod-db-1 to prod-db-1 with dry-run

Agent: [Shows recommendations]

Recommendation: 120 RPU-hours per day based on concurrency scaling usage

You: Create usage limit for workgroup prod-db-1 with 120 RPU-hours per day and emit-metric action

Agent: Creating usage limit...

✅ Usage limit created!
- Amount: 120 RPU-hours per day
- Breach action: emit-metric (CloudWatch metric will be emitted)

Your serverless workgroup now has cost controls in place!
```

## Usage Limit Parameters

### Usage Type
- **serverless-compute**: Only type available for serverless (RPU-hours)

### Amount
- Number of RPU-hours allowed
- Examples: 30, 60, 100, 200, 500

### Period
- **daily**: Limit resets every day at midnight UTC
- **weekly**: Limit resets every Monday at midnight UTC
- **monthly**: Limit resets on the 1st of each month at midnight UTC

### Breach Action
- **log**: Log the breach to CloudWatch Logs (monitoring only)
- **emit-metric**: Emit a CloudWatch metric when breached (for alerting)
- **deactivate**: Stop the workgroup when limit is breached (hard stop)

## Mapping Provisioned to Serverless

### Concurrency Scaling → Serverless Compute

**Provisioned:**
- Feature: concurrency-scaling
- Limit: 60 minutes per day

**Serverless Equivalent:**
- Usage type: serverless-compute
- Recommended: 120 RPU-hours per day
- Reason: Concurrency scaling indicates burst workload needs

### Spectrum → Serverless Compute

**Provisioned:**
- Feature: spectrum
- Limit: 100 TB scanned per month

**Serverless Equivalent:**
- Usage type: serverless-compute
- Recommended: 60 RPU-hours per day (1800/month)
- Reason: Spectrum queries consume compute resources

### No Limits → Serverless Compute

**Provisioned:**
- No usage limits configured

**Serverless Equivalent:**
- Usage type: serverless-compute
- Recommended: 60 RPU-hours per day
- Reason: Standard recommendation for cost control

## IAM Permissions Required

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

## Monitoring Usage Limits

### CloudWatch Metrics

When breach action is `emit-metric`, CloudWatch metrics are created:
- Metric namespace: `AWS/Redshift-Serverless`
- Metric name: `UsageLimitBreach`
- Dimensions: WorkgroupName, UsageLimitId

### CloudWatch Logs

When breach action is `log`, entries are written to CloudWatch Logs:
- Log group: `/aws/redshift-serverless/workgroup/{workgroup-name}`
- Log stream: Contains usage limit breach events

### Setting Up Alerts

```bash
# Create CloudWatch alarm for usage limit breaches
aws cloudwatch put-metric-alarm \
  --alarm-name redshift-serverless-usage-limit-breach \
  --alarm-description "Alert when serverless usage limit is breached" \
  --metric-name UsageLimitBreach \
  --namespace AWS/Redshift-Serverless \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=WorkgroupName,Value=my-workgroup
```

## Troubleshooting

### Usage Limit Already Exists

**Problem:** "ConflictException: Usage limit already exists"

**Solution:** Each workgroup can have multiple usage limits with different periods. Check existing limits:

```
You: List usage limits for workgroup my-workgroup
```

### Permission Denied

**Problem:** "User is not authorized to perform: redshift-serverless:CreateUsageLimit"

**Solution:**
```bash
# Update permissions
scripts/utils/update_all_permissions.sh
```

### Workgroup Deactivated

**Problem:** Workgroup stopped due to usage limit breach with `deactivate` action

**Solution:**
1. Check CloudWatch Logs for breach details
2. Increase the usage limit or change breach action
3. Reactivate the workgroup:
```
You: Activate workgroup my-workgroup
```

### Unexpected High Usage

**Problem:** Hitting usage limits unexpectedly

**Solution:**
1. Check query history for expensive queries
2. Review workgroup metrics in CloudWatch
3. Optimize queries or increase limits
4. Consider using query monitoring rules

## Best Practices

### 1. Start with Monitoring

Begin with `log` breach action to understand usage patterns:
```
You: Create usage limit for workgroup my-wg with 100 RPU-hours per day and log action
```

### 2. Gradually Tighten Limits

After monitoring for a week:
1. Analyze actual usage
2. Set limit 20% above average usage
3. Change to `emit-metric` for alerting
4. Eventually use `deactivate` for hard limits

### 3. Use Multiple Periods

Set limits for different time periods:
```
You: Create usage limit for workgroup my-wg with 60 RPU-hours per day
You: Create usage limit for workgroup my-wg with 1500 RPU-hours per month
```

### 4. Align with Business Hours

For workloads with predictable patterns:
- Daily limits for consistent workloads
- Weekly limits for batch processing
- Monthly limits for compliance reporting

### 5. Test Before Production

Test usage limits in development:
```
You: Create usage limit for workgroup dev-wg with 10 RPU-hours per day and deactivate action
```

## Cost Estimation

### RPU-hour Pricing

Redshift Serverless pricing (as of 2026):
- $0.375 per RPU-hour (us-east-1)
- Prices vary by region

### Example Costs

**60 RPU-hours per day:**
- Daily: 60 × $0.375 = $22.50
- Monthly: $22.50 × 30 = $675

**120 RPU-hours per day:**
- Daily: 120 × $0.375 = $45
- Monthly: $45 × 30 = $1,350

**200 RPU-hours per day:**
- Daily: 200 × $0.375 = $75
- Monthly: $75 × 30 = $2,250

## Comparison: Provisioned vs Serverless

### Provisioned Cluster Limits

```
Concurrency Scaling: 60 minutes/day
- Limits burst capacity usage
- Charged per second of usage
- Separate from base cluster cost

Spectrum: 100 TB/month
- Limits data scanned
- Charged per TB scanned
- Separate from cluster cost
```

### Serverless Workgroup Limits

```
Serverless Compute: 120 RPU-hours/day
- Limits total compute usage
- Includes all query processing
- Single unified limit
- Charged per RPU-hour
```

## Next Steps

After setting up usage limits:

1. ✅ Monitor usage patterns for 1-2 weeks
2. ✅ Set up CloudWatch alarms for breaches
3. ✅ Review and adjust limits monthly
4. ✅ Optimize expensive queries
5. ✅ Document limits in runbooks

## Related Documentation

- [Migration Guide](CHAT_GUIDE.md)
- [Maintenance & Snapshots](MAINTENANCE_AND_SNAPSHOTS.md)
- [Scheduled Queries](SCHEDULED_QUERIES.md)
- [AWS Redshift Serverless Pricing](https://aws.amazon.com/redshift/pricing/)

---

**Quick Commands:**

```bash
# Check limits
./chat → "Get usage limits for my-cluster"

# Get recommendations
./chat → "Migrate usage limits from my-cluster to my-wg with dry-run"

# Create limit
./chat → "Create usage limit for workgroup my-wg with 60 RPU-hours per day"
```

**Control your serverless costs with usage limits!** 🎉
