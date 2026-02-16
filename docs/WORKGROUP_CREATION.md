# Workgroup and Namespace Creation

## Overview

The migration tool can automatically create Redshift Serverless workgroups and namespaces if they don't already exist. This simplifies the migration process by handling infrastructure setup automatically.

## Features

- ✅ Create namespace from scratch
- ✅ Restore namespace from snapshot
- ✅ Create workgroup with proper configuration
- ✅ Automatically apply VPC and IAM settings
- ✅ Check if resources exist before creating
- ✅ Price-performance target optimization (level 50, balanced)
- ✅ Configurable maximum capacity (RPU)

## Usage

### Option 1: Create Snapshot and Restore (Recommended)

This automatically creates a fresh snapshot from your provisioned cluster and restores it.

With smart defaults (workgroup = cluster-id, namespace = workgroup-ns):

```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --create-if-missing \
  --create-snapshot \
  --max-capacity 512 \
  --region us-east-1
```

Or with custom names:

```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --workgroup my-new-workgroup \
  --namespace my-new-namespace \
  --create-if-missing \
  --create-snapshot \
  --max-capacity 512 \
  --region us-east-1
```

### Option 2: Create New Namespace and Workgroup

With smart defaults:

```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --create-if-missing \
  --admin-username admin \
  --admin-password "YourSecurePassword123!" \
  --max-capacity 512 \
  --region us-east-1
```

Or with custom names:

```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --workgroup my-new-workgroup \
  --namespace my-new-namespace \
  --create-if-missing \
  --admin-username admin \
  --admin-password "YourSecurePassword123!" \
  --max-capacity 512 \
  --region us-east-1
```

### Option 3: Restore from Existing Snapshot

With smart defaults:

```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --create-if-missing \
  --snapshot-name my-cluster-snapshot-2024-01-15 \
  --max-capacity 512 \
  --region us-east-1
```

### Option 4: Apply to Existing Workgroup

```bash
# Without --create-if-missing, assumes workgroup/namespace exist
redshift-migrate migrate \
  --cluster-id my-cluster \
  --workgroup existing-workgroup \
  --namespace existing-namespace \
  --region us-east-1
```

## Command Options

### Required Options

- `--cluster-id` - Source provisioned cluster identifier

### Optional Naming

- `--workgroup` - Target serverless workgroup name (default: same as cluster-id)
- `--namespace` - Target serverless namespace name (default: same as cluster-id)

**Smart Defaults**: If you don't specify workgroup and namespace names, the tool will use the cluster-id for both.

For example, if your cluster-id is `prod-cluster`:
- Default workgroup: `prod-cluster`
- Default namespace: `prod-cluster`

### Creation Options

- `--create-if-missing` - Enable automatic creation (flag)
- `--create-snapshot` - Create a new snapshot from the cluster before restoring (flag, mutually exclusive with --snapshot-name)
- `--snapshot-name` - Snapshot to restore from (optional, mutually exclusive with --create-snapshot)
- `--admin-username` - Admin username for new namespace (default: "admin")
- `--admin-password` - Admin password for new namespace (required if creating without snapshot)
- `--max-capacity` - Maximum capacity in RPU (default: 512)

**Note**: You cannot use both `--create-snapshot` and `--snapshot-name` together. Use `--create-snapshot` to automatically create a new snapshot, or use `--snapshot-name` to restore from an existing snapshot.

### Other Options

- `--dry-run` - Preview without making changes
- `--region` - AWS region

## What Gets Created

### Namespace

When creating a new namespace:
- **Admin User**: Configured with provided username/password
- **Database**: Default database named "dev"
- **IAM Roles**: Copied from provisioned cluster
- **Tags**: Copied from provisioned cluster

### Workgroup

When creating a new workgroup:
- **VPC Configuration**: Subnets and security groups from provisioned cluster
- **Network Access**: Public accessibility setting from provisioned cluster
- **Price-Performance Target**: Level 50 (balanced) for optimal cost/performance
- **Maximum Capacity**: Configurable RPU limit (default 512)
- **Config Parameters**: Applied from parameter group mapping
- **Tags**: Copied from provisioned cluster

## Price-Performance Target

The tool uses Redshift Serverless price-performance target optimization instead of fixed base capacity:

- **Level**: 50 (balanced setting)
- **Status**: Enabled
- **Behavior**: Automatically scales compute between 0 and max-capacity based on workload
- **Benefits**: 
  - Optimizes cost by scaling down during low usage
  - Maintains performance during peak loads
  - Balanced approach between cost and performance

## Automatic Snapshot Creation

The `--create-snapshot` flag automatically:

1. **Creates a snapshot** from your provisioned cluster with a timestamped name
2. **Waits for completion** (monitors progress every 30 seconds)
3. **Restores the namespace** from the new snapshot
4. **Creates the workgroup** and links it to the namespace
5. **Applies all configurations** (IAM roles, VPC, parameters, etc.)

**Important**: When using `--create-snapshot`, you don't need to specify `--snapshot-name`. The tool automatically creates a new snapshot with a timestamped name like `cluster-migration-20240115-143022`.

### Benefits

- ✅ No need to manually create snapshots
- ✅ Ensures you have the latest data
- ✅ Automatic naming with timestamps
- ✅ Progress monitoring during snapshot creation
- ✅ One-command migration

### Example

```bash
# Complete migration with automatic snapshot
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --workgroup prod-serverless \
  --namespace prod-namespace \
  --create-if-missing \
  --create-snapshot \
  --max-capacity 512 \
  --region us-east-1
```

Output:
```
[1/4] Extracting from cluster: prod-cluster
✓ Found 2 IAM roles
✓ Found 3 subnets

[2/4] Creating workgroup/namespace
Creating snapshot: prod-cluster-migration-20240115-143022
Waiting for snapshot to complete (this may take several minutes)...
  Snapshot progress: 125.50 MB/s
✓ Snapshot prod-cluster-migration-20240115-143022 is ready
Restoring namespace from snapshot...
✓ Successfully created snapshot and restored to prod-namespace
  Snapshot: prod-cluster-migration-20240115-143022

[3/4] Transforming configuration
[4/4] Applying to workgroup: prod-serverless
✓ Migration completed successfully!
```

## Snapshot Restore

When using `--snapshot-name`:

1. **Namespace** is restored from the snapshot (includes all data and schemas)
2. **Workgroup** is created and linked to the restored namespace
3. **IAM Roles** are applied to the namespace
4. **Network Configuration** is applied to the workgroup

### Finding Snapshots

```bash
# List available snapshots
aws redshift describe-cluster-snapshots \
  --cluster-identifier my-cluster \
  --query 'Snapshots[*].[SnapshotIdentifier,SnapshotCreateTime]' \
  --output table
```

## Maximum Capacity (RPU)

Redshift Processing Units (RPU) determine the maximum compute capacity. With price-performance target enabled, the workgroup scales between 0 and this maximum:

| Max RPU | Use Case |
|---------|----------|
| 128-256 | Development/testing, small workloads |
| 256-512 | Small to medium production workloads |
| 512-1024 | Medium to large production workloads |
| 1024+ | Very large production workloads |

**Note**: The workgroup automatically scales down during low usage periods to save costs, and scales up to the maximum during peak loads.

## Security Considerations

### Admin Password

When creating a namespace without a snapshot, you must provide an admin password:

```bash
# Option 1: Command line (less secure)
--admin-password "MyPassword123!"

# Option 2: Environment variable (more secure)
export REDSHIFT_ADMIN_PASSWORD="MyPassword123!"
redshift-migrate migrate ... --admin-password "$REDSHIFT_ADMIN_PASSWORD"

# Option 3: Prompt (most secure)
read -s REDSHIFT_ADMIN_PASSWORD
export REDSHIFT_ADMIN_PASSWORD
redshift-migrate migrate ... --admin-password "$REDSHIFT_ADMIN_PASSWORD"
```

### IAM Permissions

Additional permissions required for creation:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift-serverless:CreateNamespace",
        "redshift-serverless:CreateWorkgroup",
        "redshift-serverless:GetNamespace",
        "redshift-serverless:GetWorkgroup",
        "redshift-serverless:RestoreFromSnapshot",
        "redshift-serverless:ListSnapshots"
      ],
      "Resource": "*"
    }
  ]
}
```

## Examples

### Example 1: Complete New Setup (with smart defaults)

```bash
# Extract configuration
redshift-migrate extract \
  --cluster-id prod-cluster \
  --output prod-config.json

# Review configuration
cat prod-config.json | jq

# Create and migrate (dry-run first)
# This will create both workgroup and namespace as 'prod-cluster'
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --create-if-missing \
  --admin-password "SecurePass123!" \
  --max-capacity 512 \
  --dry-run

# Apply for real
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --create-if-missing \
  --admin-password "SecurePass123!" \
  --max-capacity 512
```

### Example 2: Complete New Setup (with custom names)

```bash
# Extract configuration
redshift-migrate extract \
  --cluster-id prod-cluster \
  --output prod-config.json

# Review configuration
cat prod-config.json | jq

# Create and migrate (dry-run first)
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --workgroup prod-serverless \
  --namespace prod-namespace \
  --create-if-missing \
  --admin-password "SecurePass123!" \
  --max-capacity 512 \
  --dry-run

# Apply for real
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --workgroup prod-serverless \
  --namespace prod-namespace \
  --create-if-missing \
  --admin-password "SecurePass123!" \
  --max-capacity 512
```

### Example 2: Complete New Setup (with custom names)

```bash
# Extract configuration
redshift-migrate extract \
  --cluster-id prod-cluster \
  --output prod-config.json

# Review configuration
cat prod-config.json | jq

# Create and migrate (dry-run first)
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --workgroup prod-serverless \
  --namespace prod-namespace \
  --create-if-missing \
  --admin-password "SecurePass123!" \
  --max-capacity 512 \
  --dry-run

# Apply for real
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --workgroup prod-serverless \
  --namespace prod-namespace \
  --create-if-missing \
  --admin-password "SecurePass123!" \
  --max-capacity 512
```

### Example 3: Restore from Snapshot (with smart defaults)

```bash
# Create snapshot first
aws redshift create-cluster-snapshot \
  --cluster-identifier prod-cluster \
  --snapshot-identifier prod-migration-snapshot

# Wait for snapshot to complete
aws redshift wait snapshot-available \
  --snapshot-identifier prod-migration-snapshot

# Migrate using snapshot (creates 'prod-cluster' for both workgroup and namespace)
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --create-if-missing \
  --snapshot-name prod-migration-snapshot \
  --max-capacity 512
```

### Example 4: Restore from Snapshot (with custom names)

```bash
# Create snapshot first
aws redshift create-cluster-snapshot \
  --cluster-identifier prod-cluster \
  --snapshot-identifier prod-migration-snapshot

# Wait for snapshot to complete
aws redshift wait snapshot-available \
  --snapshot-identifier prod-migration-snapshot

# Migrate using snapshot
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --workgroup prod-serverless \
  --namespace prod-namespace \
  --create-if-missing \
  --snapshot-name prod-migration-snapshot \
  --max-capacity 512
```

### Example 4: Restore from Snapshot (with custom names)

```bash
# Create snapshot first
aws redshift create-cluster-snapshot \
  --cluster-identifier prod-cluster \
  --snapshot-identifier prod-migration-snapshot

# Wait for snapshot to complete
aws redshift wait snapshot-available \
  --snapshot-identifier prod-migration-snapshot

# Migrate using snapshot
redshift-migrate migrate \
  --cluster-id prod-cluster \
  --workgroup prod-serverless \
  --namespace prod-namespace \
  --create-if-missing \
  --snapshot-name prod-migration-snapshot \
  --max-capacity 512
```

### Example 5: Apply Command with Creation (smart defaults)

```bash
# Extract first
redshift-migrate extract \
  --cluster-id my-cluster \
  --output config.json

# Apply with creation (uses 'my-cluster' for both workgroup and namespace)
redshift-migrate apply \
  --config config.json \
  --create-if-missing \
  --admin-password "Pass123!" \
  --max-capacity 512
```

## Troubleshooting

### "Namespace already exists"
- The tool will skip creation and use the existing namespace
- Ensure the existing namespace is in the correct state

### "Workgroup already exists"
- The tool will skip creation and use the existing workgroup
- Configuration will still be applied to the existing workgroup

### "Invalid admin password"
- Password must be 8-64 characters
- Must contain uppercase, lowercase, and numbers
- Cannot contain certain special characters

### "Insufficient permissions"
- Ensure you have `redshift-serverless:CreateNamespace` permission
- Ensure you have `redshift-serverless:CreateWorkgroup` permission

### "Snapshot not found"
- Verify the snapshot name is correct
- Ensure the snapshot is in "available" state
- Check that the snapshot is in the same region

### "Cannot use both --create-snapshot and --snapshot-name"
- These options are mutually exclusive
- Use `--create-snapshot` to automatically create a new snapshot
- Use `--snapshot-name` to restore from an existing snapshot
- Remove one of the options from your command

## Best Practices

1. **Use Snapshots for Production**: Always restore from a snapshot for production migrations
2. **Test First**: Use `--dry-run` to preview changes
3. **Secure Passwords**: Never hardcode passwords in scripts
4. **Right-Size Capacity**: Start with appropriate RPU based on workload
5. **Tag Resources**: Tags are automatically copied from the source cluster
6. **Monitor Creation**: Watch CloudWatch for creation progress
7. **Verify Connectivity**: Test database connectivity after creation

## Cleanup

If you need to delete created resources:

```bash
# Delete workgroup
aws redshift-serverless delete-workgroup \
  --workgroup-name my-workgroup

# Delete namespace (after workgroup is deleted)
aws redshift-serverless delete-namespace \
  --namespace-name my-namespace
```

## Next Steps

After creation:
1. Verify workgroup is in "AVAILABLE" state
2. Test database connectivity
3. Run validation queries
4. Update application connection strings
5. Monitor performance and adjust capacity as needed
