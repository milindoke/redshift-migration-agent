# ✅ Maintenance Track and Snapshot Copy Migration Added!

Your agent can now carry over maintenance track and cross-region snapshot copy settings from provisioned clusters to serverless workgroups!

## What's New?

### New Agent Tools

1. **get_cluster_maintenance_settings** - Get maintenance track and window from provisioned cluster
   - Shows maintenance track (current, trailing, preview)
   - Shows maintenance window (e.g., "sun:05:00-sun:05:30")
   - Shows next maintenance window time
   - Shows cluster version and upgrade settings

2. **get_cluster_snapshot_copy_settings** - Get cross-region snapshot copy configuration
   - Shows if snapshot copy is enabled
   - Shows destination region
   - Shows retention periods (automated and manual)
   - Shows KMS encryption grant if used

3. **configure_serverless_snapshot_copy** - Configure snapshot copy for serverless namespace
   - Sets up cross-region snapshot copy
   - Configures retention periods
   - Supports KMS encryption grants
   - Preserves disaster recovery capabilities

### New Data Models

Updated `ProvisionedClusterConfig` model to include:
- `maintenance_track`: Maintenance track name (current, trailing, preview)
- `snapshot_copy_config`: Cross-region snapshot copy settings

### New Permissions

Added to `template.yaml` and `scripts/utils/update_all_permissions.sh`:

**Redshift Serverless (Extended)**
- `redshift-serverless:CreateSnapshotCopyConfiguration` - Create snapshot copy config
- `redshift-serverless:UpdateSnapshotCopyConfiguration` - Update snapshot copy config
- `redshift-serverless:DeleteSnapshotCopyConfiguration` - Delete snapshot copy config
- `redshift-serverless:ListSnapshotCopyConfigurations` - List snapshot copy configs

### New Documentation

Created comprehensive guide: [docs/guides/MAINTENANCE_AND_SNAPSHOTS.md](docs/guides/MAINTENANCE_AND_SNAPSHOTS.md)

Covers:
- Maintenance track and window differences between provisioned and serverless
- Cross-region snapshot copy migration
- Step-by-step migration guide
- IAM permissions required
- Troubleshooting
- Best practices
- Cost considerations

## How to Use

### Quick Start

```bash
# Start the chat interface
./chat

# Check maintenance settings
You: Get maintenance settings for cluster my-cluster in us-east-2

# Check snapshot copy settings
You: Get snapshot copy settings for cluster my-cluster

# After migration, configure snapshot copy
You: Configure snapshot copy for namespace my-namespace to us-west-2 with 7 day retention
```

### Example Conversation

```
You: Get maintenance and snapshot settings for prod-db-1 in us-east-2

Agent: Checking settings...

Maintenance Settings:
{
  "cluster_id": "prod-db-1",
  "maintenance_track": "current",
  "maintenance_window": "sun:05:00-sun:05:30",
  "next_maintenance_window": "2026-02-23T05:00:00Z",
  "allow_version_upgrade": true,
  "cluster_version": "1.0.12345"
}

Snapshot Copy Settings:
{
  "cluster_id": "prod-db-1",
  "snapshot_copy_enabled": true,
  "destination_region": "us-west-2",
  "retention_period_days": 7,
  "manual_snapshot_retention_period_days": 30,
  "snapshot_copy_grant_name": "my-kms-grant"
}

You: Migrate prod-db-1 to serverless

Agent: [Performs migration...]

✅ Migration complete!
- Namespace: prod-db-1
- Workgroup: prod-db-1
- Maintenance: Automatic (AWS managed)

You: Configure snapshot copy for namespace prod-db-1 to us-west-2 with 7 day retention

Agent: Configuring cross-region snapshot copy...

{
  "status": "success",
  "namespace_name": "prod-db-1",
  "destination_region": "us-west-2",
  "retention_period_days": 7,
  "message": "Cross-region snapshot copy configured for namespace 'prod-db-1'"
}

✅ Cross-region snapshot copy is now active!
```

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
| Configuration | Via cluster settings | Via namespace settings |

## What Gets Migrated

### Maintenance Settings

**Extracted (for reference):**
- ✅ Maintenance track name
- ✅ Maintenance window
- ✅ Next maintenance time
- ✅ Version upgrade settings

**In Serverless:**
- 🔄 Automatic maintenance (no manual window)
- 🔄 Always on latest version
- 🔄 Minimal/zero downtime updates
- 🔄 AWS-managed timing

### Snapshot Copy Settings

**Preserved:**
- ✅ Destination region
- ✅ Retention period (automated snapshots)
- ✅ Manual snapshot retention period
- ✅ KMS encryption grant

**Migration Process:**
1. Extract settings from provisioned cluster
2. Migrate cluster to serverless
3. Configure snapshot copy for serverless namespace
4. Verify snapshots are being copied

## Technical Details

### Maintenance Track Extraction

The agent extracts:
- `MaintenanceTrackName`: current, trailing, or preview
- `PreferredMaintenanceWindow`: Day and time (e.g., "sun:05:00-sun:05:30")
- `NextMaintenanceWindowStartTime`: Next scheduled maintenance
- `AllowVersionUpgrade`: Whether automatic upgrades are enabled
- `ClusterVersion`: Current cluster version

### Snapshot Copy Extraction

The agent extracts from `ClusterSnapshotCopyStatus`:
- `DestinationRegion`: Target region for snapshot copies
- `RetentionPeriod`: Days to retain automated snapshots
- `ManualSnapshotRetentionPeriod`: Days to retain manual snapshots
- `SnapshotCopyGrantName`: KMS grant for encrypted snapshots

### Serverless Configuration

For serverless namespaces, the agent calls:
```python
redshift_serverless.create_snapshot_copy_configuration(
    namespaceName=namespace_name,
    destinationRegion=destination_region,
    retentionPeriod=retention_period,
    snapshotCopyGrantName=snapshot_copy_grant_name  # if provided
)
```

## Files Modified

1. **redshift_agent.py**
   - Added `get_cluster_maintenance_settings` tool
   - Added `get_cluster_snapshot_copy_settings` tool
   - Added `configure_serverless_snapshot_copy` tool
   - Updated system prompt with maintenance and snapshot guidance
   - Updated help system with maintenance_snapshot topic

2. **src/redshift_migrate/models.py**
   - Added `maintenance_track` field to `ProvisionedClusterConfig`
   - Added `snapshot_copy_config` field to `ProvisionedClusterConfig`

3. **src/redshift_migrate/extractors/provisioned.py**
   - Added `_extract_snapshot_copy_config` method
   - Updated `extract` method to capture maintenance track and snapshot copy

4. **template.yaml**
   - Added Redshift Serverless snapshot copy permissions

5. **scripts/utils/update_all_permissions.sh**
   - Updated policy document with snapshot copy permissions

6. **docs/guides/MAINTENANCE_AND_SNAPSHOTS.md**
   - Created comprehensive guide (new file)

7. **README.md**
   - Added maintenance and snapshot migration to features
   - Added example conversation
   - Added link to documentation

## Permissions Required

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
You: Get maintenance settings for my-cluster
You: Get snapshot copy settings for my-cluster
You: Migrate my-cluster to serverless
You: Configure snapshot copy for namespace my-ns to us-west-2 with 7 day retention
```

## Benefits

### For Users
- ✅ Preserves disaster recovery capabilities
- ✅ No manual maintenance window configuration needed
- ✅ Automatic version upgrades in serverless
- ✅ Clear visibility into current settings
- ✅ Easy snapshot copy configuration

### For Operations
- ✅ Maintains compliance with retention policies
- ✅ Preserves cross-region backup strategy
- ✅ Reduces manual configuration steps
- ✅ Provides audit trail of settings
- ✅ Simplifies disaster recovery planning

### For Cost
- ✅ Same snapshot copy costs as provisioned
- ✅ No additional charges for automatic maintenance
- ✅ Predictable cross-region data transfer costs

## Common Use Cases

### 1. Full Migration with Snapshot Copy

```
You: Get snapshot copy settings for my-cluster
You: Migrate my-cluster to serverless
You: Configure snapshot copy for namespace my-ns to DESTINATION_REGION with RETENTION_DAYS day retention
```

### 2. Check Settings Before Migration

```
You: Get maintenance settings for my-cluster
You: Get snapshot copy settings for my-cluster
You: [Review settings]
You: Migrate my-cluster to serverless
```

### 3. Configure Snapshot Copy After Migration

```
You: [Cluster already migrated]
You: Configure snapshot copy for namespace my-ns to us-west-2 with 7 day retention
```

### 4. Update Snapshot Copy Settings

```
You: Update snapshot copy for namespace my-ns to 30 day retention
```

## Troubleshooting

### Snapshot Copy Already Configured

**Problem:** "ConflictException: Snapshot copy configuration already exists"

**Solution:** Normal if running configuration multiple times. Existing configuration is preserved.

### Permission Denied

**Problem:** "User is not authorized to perform: redshift-serverless:CreateSnapshotCopyConfiguration"

**Solution:**
```bash
# Update permissions
scripts/utils/update_all_permissions.sh
```

### Invalid Destination Region

**Problem:** "Invalid destination region"

**Solution:** Ensure destination region:
- Is different from source region
- Supports Redshift Serverless
- Is in the same partition

## Next Steps

1. ✅ Update permissions: `scripts/utils/update_all_permissions.sh`
2. ✅ Test the feature: `./chat`
3. ✅ Read the guide: [docs/guides/MAINTENANCE_AND_SNAPSHOTS.md](docs/guides/MAINTENANCE_AND_SNAPSHOTS.md)
4. ✅ Migrate your clusters with full settings preservation!

## Documentation

- **Complete Guide**: [docs/guides/MAINTENANCE_AND_SNAPSHOTS.md](docs/guides/MAINTENANCE_AND_SNAPSHOTS.md)
- **Scheduled Queries**: [docs/guides/SCHEDULED_QUERIES.md](docs/guides/SCHEDULED_QUERIES.md)
- **Deployment**: [docs/deployment/DEPLOY_NOW.md](docs/deployment/DEPLOY_NOW.md)
- **Chat Guide**: [docs/guides/CHAT_GUIDE.md](docs/guides/CHAT_GUIDE.md)

---

**Your agent can now preserve all maintenance and snapshot settings!** 🎉

Apply the changes:
```bash
scripts/utils/update_all_permissions.sh
```

Then start chatting:
```bash
./chat
```
