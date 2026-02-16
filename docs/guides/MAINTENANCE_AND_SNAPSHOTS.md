# Migrating Maintenance Track and Snapshot Copy Settings

Complete guide for migrating maintenance track and cross-region snapshot copy settings from Redshift Provisioned clusters to Redshift Serverless.

## Overview

When migrating from Redshift Provisioned to Serverless, there are important differences in how maintenance and snapshots are handled:

### Maintenance Windows
- **Provisioned**: Manual maintenance windows (e.g., "sun:05:00-sun:05:30")
- **Serverless**: Automatic maintenance windows (AWS managed, no configuration needed)

### Maintenance Tracks
- **Provisioned**: Choose tracks (current, trailing, preview)
- **Serverless**: Always on latest version automatically

### Cross-Region Snapshot Copy
- **Both**: Support cross-region snapshot copy for disaster recovery
- **Migration**: Settings can be carried over to serverless namespace

## Quick Start

```bash
# Start the chat interface
./chat

# Check maintenance settings
You: Get maintenance settings for cluster my-cluster in us-east-2

# Check snapshot copy settings
You: Get snapshot copy settings for cluster my-cluster

# After migration, configure snapshot copy for serverless
You: Configure snapshot copy for namespace my-namespace to us-west-2 with 7 day retention
```

## Maintenance Track Migration

### Understanding Maintenance Tracks

Provisioned clusters use maintenance tracks to control when updates are applied:
- **current**: Latest stable version (recommended)
- **trailing**: One version behind current
- **preview**: Early access to new features

### What Happens in Serverless?

Serverless automatically manages maintenance:
- No manual maintenance windows needed
- Updates applied during low-activity periods
- Always runs on latest stable version
- No downtime for most updates

### Checking Maintenance Settings

```bash
./chat
```

```
You: Get maintenance settings for cluster prod-db-1 in us-east-2

Agent: Here are the maintenance settings for cluster 'prod-db-1':

{
  "cluster_id": "prod-db-1",
  "maintenance_track": "current",
  "maintenance_window": "sun:05:00-sun:05:30",
  "next_maintenance_window": "2026-02-23T05:00:00Z",
  "allow_version_upgrade": true,
  "cluster_version": "1.0.12345"
}

The cluster is on the 'current' track with maintenance scheduled for Sundays at 5:00 AM.
When you migrate to serverless, maintenance will be handled automatically by AWS.
```

### Migration Impact

When migrating to serverless:
1. ✅ Maintenance track information is captured for reference
2. ✅ Serverless handles updates automatically
3. ✅ No manual maintenance window configuration needed
4. ✅ Updates typically happen during low-activity periods
5. ✅ Most updates have zero downtime

## Cross-Region Snapshot Copy Migration

### Understanding Snapshot Copy

Cross-region snapshot copy provides disaster recovery by:
- Automatically copying snapshots to another AWS region
- Maintaining retention periods for compliance
- Supporting encrypted snapshots with KMS

### Checking Snapshot Copy Settings

```bash
./chat
```

```
You: Get snapshot copy settings for cluster prod-db-1

Agent: Here are the snapshot copy settings for cluster 'prod-db-1':

{
  "cluster_id": "prod-db-1",
  "snapshot_copy_enabled": true,
  "destination_region": "us-west-2",
  "retention_period_days": 7,
  "manual_snapshot_retention_period_days": 30,
  "snapshot_copy_grant_name": "my-kms-grant"
}

Cross-region snapshot copy is enabled, copying to us-west-2 with 7-day retention.
```

### Migrating Snapshot Copy to Serverless

After creating your serverless namespace, configure snapshot copy:

```
You: Configure snapshot copy for namespace prod-serverless-ns to us-west-2 with 7 day retention

Agent: Configuring cross-region snapshot copy...

{
  "status": "success",
  "namespace_name": "prod-serverless-ns",
  "destination_region": "us-west-2",
  "retention_period_days": 7,
  "message": "Cross-region snapshot copy configured for namespace 'prod-serverless-ns'"
}

✅ Snapshot copy is now active! Snapshots will be automatically copied to us-west-2.
```

## Step-by-Step Migration Guide

### Step 1: Check Current Settings

```
You: Get maintenance settings for my-cluster
You: Get snapshot copy settings for my-cluster
```

### Step 2: Migrate the Cluster

```
You: Migrate cluster my-cluster to serverless with snapshot
```

### Step 3: Configure Snapshot Copy (if enabled)

If snapshot copy was enabled on the source cluster:

```
You: Configure snapshot copy for namespace my-namespace to DESTINATION_REGION with RETENTION_DAYS day retention
```

Replace:
- `DESTINATION_REGION`: Same region as source cluster (e.g., us-west-2)
- `RETENTION_DAYS`: Same retention period as source cluster (e.g., 7)

### Step 4: Verify Configuration

```
You: List snapshot copy configurations for namespace my-namespace
```

## Complete Migration Example

```
You: Get maintenance and snapshot settings for prod-db-1 in us-east-2

Agent: Checking settings...

Maintenance Settings:
- Track: current
- Window: sun:05:00-sun:05:30
- Next maintenance: 2026-02-23T05:00:00Z

Snapshot Copy Settings:
- Enabled: Yes
- Destination: us-west-2
- Retention: 7 days
- Manual retention: 30 days

You: Migrate prod-db-1 to serverless

Agent: [Performs migration...]

✅ Migration complete!
- Namespace: prod-db-1
- Workgroup: prod-db-1
- Maintenance: Automatic (AWS managed)

You: Configure snapshot copy for namespace prod-db-1 to us-west-2 with 7 day retention

Agent: Configuring snapshot copy...

✅ Cross-region snapshot copy configured!
- Destination: us-west-2
- Retention: 7 days
- Snapshots will be automatically copied

Your migration is complete with all settings preserved!
```

## Snapshot Copy Configuration Options

### Basic Configuration

```
You: Configure snapshot copy for namespace my-ns to us-west-2 with 7 day retention
```

### With KMS Encryption

If your source cluster uses KMS encryption for snapshots:

```
You: Configure snapshot copy for namespace my-ns to us-west-2 with 7 day retention and grant my-kms-grant
```

### Custom Retention Periods

```
You: Configure snapshot copy for namespace my-ns to us-west-2 with 30 day retention
```

Common retention periods:
- 7 days: Standard backup
- 14 days: Extended backup
- 30 days: Monthly compliance
- 90 days: Quarterly compliance

## IAM Permissions Required

### For Maintenance Settings

```json
{
  "Effect": "Allow",
  "Action": [
    "redshift:DescribeClusters"
  ],
  "Resource": "*"
}
```

### For Snapshot Copy Configuration

```json
{
  "Effect": "Allow",
  "Action": [
    "redshift:DescribeClusters",
    "redshift-serverless:CreateSnapshotCopyConfiguration",
    "redshift-serverless:UpdateSnapshotCopyConfiguration",
    "redshift-serverless:ListSnapshotCopyConfigurations"
  ],
  "Resource": "*"
}
```

### For KMS Encrypted Snapshots

```json
{
  "Effect": "Allow",
  "Action": [
    "kms:DescribeKey",
    "kms:CreateGrant",
    "kms:ListGrants"
  ],
  "Resource": "*"
}
```

## Troubleshooting

### Snapshot Copy Already Configured

**Problem:** "ConflictException: Snapshot copy configuration already exists"

**Solution:** This is normal if you run the configuration multiple times. The existing configuration is preserved.

To update:
```
You: Update snapshot copy configuration for namespace my-ns
```

### Permission Denied

**Problem:** "User is not authorized to perform: redshift-serverless:CreateSnapshotCopyConfiguration"

**Solution:**
```bash
# Update permissions
scripts/utils/update_all_permissions.sh
```

### KMS Grant Not Found

**Problem:** "Snapshot copy grant 'my-grant' not found"

**Solution:** Create the KMS grant in the destination region first:

```bash
aws redshift create-snapshot-copy-grant \
  --snapshot-copy-grant-name my-grant \
  --kms-key-id arn:aws:kms:us-west-2:ACCOUNT:key/KEY_ID \
  --region us-west-2
```

### Invalid Destination Region

**Problem:** "Invalid destination region"

**Solution:** Ensure the destination region:
- Is different from the source region
- Supports Redshift Serverless
- Is in the same partition (e.g., both in aws, not aws-cn)

## Best Practices

### 1. Match Source Settings

When migrating, use the same snapshot copy settings as the source cluster:
- Same destination region
- Same retention period
- Same KMS grant (if encrypted)

### 2. Test in Non-Production First

```
You: Get snapshot copy settings for dev-cluster
You: Migrate dev-cluster to serverless
You: Configure snapshot copy for namespace dev-ns
You: Verify snapshots are being copied
```

### 3. Monitor Snapshot Copy

After configuration:
```bash
# Check snapshot copy status
aws redshift-serverless list-snapshots \
  --namespace-name my-namespace \
  --region us-east-2

# Check copied snapshots in destination region
aws redshift-serverless list-snapshots \
  --namespace-name my-namespace \
  --region us-west-2
```

### 4. Update Disaster Recovery Plans

After migration:
- Update DR documentation with new namespace names
- Test snapshot restore in destination region
- Update monitoring and alerting

## Key Differences: Provisioned vs Serverless

### Maintenance

| Feature | Provisioned | Serverless |
|---------|-------------|------------|
| Maintenance Window | Manual (e.g., sun:05:00-sun:05:30) | Automatic (AWS managed) |
| Maintenance Track | current, trailing, preview | Always latest |
| Version Control | Manual upgrades | Automatic upgrades |
| Downtime | Scheduled during window | Minimal/zero downtime |
| Configuration | Required | Not needed |

### Snapshot Copy

| Feature | Provisioned | Serverless |
|---------|-------------|------------|
| Cross-Region Copy | Supported | Supported |
| Retention Periods | Configurable | Configurable |
| KMS Encryption | Supported | Supported |
| Manual Snapshots | Separate retention | Same configuration |
| Configuration | Via cluster settings | Via namespace settings |

## Cost Considerations

### Snapshot Copy Costs

- **Storage**: Pay for snapshot storage in both regions
- **Data Transfer**: Cross-region data transfer charges apply
- **Retention**: Longer retention = more storage costs

### Example Cost

```
Scenario: 100 GB database, 7-day retention, us-east-1 → us-west-2

- Snapshot size: ~100 GB (compressed)
- Snapshots per day: 1 automated
- Total snapshots: 7 (7-day retention)
- Storage cost: 7 × 100 GB × $0.024/GB = $16.80/month per region
- Total storage: $16.80 × 2 regions = $33.60/month
- Data transfer: 100 GB × $0.02/GB = $2.00/day = $60/month

Total: ~$94/month for cross-region snapshot copy
```

## Maintenance Window Comparison

### Provisioned Cluster

```
Maintenance Window: sun:05:00-sun:05:30
- Updates applied during this 30-minute window
- Cluster unavailable during updates
- Can be rescheduled if needed
- Predictable timing
```

### Serverless Namespace

```
Maintenance: Automatic
- Updates applied during low-activity periods
- Minimal/zero downtime
- No configuration needed
- AWS optimizes timing
```

## Next Steps

After migrating maintenance and snapshot settings:

1. ✅ Verify snapshot copy is working
2. ✅ Update monitoring and alerting
3. ✅ Update disaster recovery documentation
4. ✅ Test snapshot restore in destination region
5. ✅ Remove old provisioned cluster (after verification period)

## Related Documentation

- [Migration Guide](CHAT_GUIDE.md)
- [Scheduled Query Migration](SCHEDULED_QUERIES.md)
- [Deployment Guide](../deployment/DEPLOY_NOW.md)
- [AWS Redshift Serverless Snapshots](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-snapshots-recovery.html)

---

**Quick Commands:**

```bash
# Check settings
./chat → "Get maintenance settings for my-cluster"
./chat → "Get snapshot copy settings for my-cluster"

# Migrate
./chat → "Migrate my-cluster to serverless"

# Configure snapshot copy
./chat → "Configure snapshot copy for namespace my-ns to us-west-2 with 7 day retention"
```

**Your maintenance and snapshot settings will be preserved in serverless!** 🎉
