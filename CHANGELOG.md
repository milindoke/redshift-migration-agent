# Changelog

All notable changes to the Redshift Migration Tool project.

## [0.3.0] - 2024-02-11

### Changed - Price-Performance Target Optimization

- **Price-Performance Target**: Workgroups now use price-performance target (level 50, balanced) instead of fixed base capacity
- **Auto-Scaling**: Workgroups automatically scale between 0 and max-capacity based on workload
- **Cost Optimization**: Scales down during low usage to save costs, scales up during peak loads
- **Parameter Change**: Replaced `--base-capacity` flag with `--max-capacity` (default: 512 RPU)
- **Better Defaults**: Increased default from 128 to 512 RPU for better production readiness

### Improved - Snapshot Options

- **Mutually Exclusive Flags**: `--create-snapshot` and `--snapshot-name` are now mutually exclusive
- **Clearer Intent**: Use `--create-snapshot` to automatically create a new snapshot, OR use `--snapshot-name` to restore from an existing one
- **Better Validation**: CLI now validates and provides clear error messages if both options are used together

### Added - Smart Naming Defaults

- **Automatic Workgroup Name**: If not specified, workgroup name defaults to cluster-id
- **Automatic Namespace Name**: If not specified, namespace name defaults to cluster-id (same as workgroup)
- **Simplified Commands**: No need to specify names for simple migrations
- **Example**: For cluster `prod-cluster`, both workgroup and namespace will be `prod-cluster`

### Fixed

- **Parameter Application Bug**: Fixed KeyError when applying config parameters to workgroup
- **Error Handling**: Improved error messages with more detailed information for troubleshooting
- **Resource Availability**: Added wait logic to ensure workgroup and namespace are fully available before applying configuration
- **Error Display**: Enhanced CLI output to show detailed error messages in results table
- **Snapshot Restore API**: Fixed restore_from_snapshot to use correct parameters (workgroupName required, snapshotArn instead of snapshotName)
- **IAM Roles During Restore**: IAM roles now applied after restore completes (cannot be set during restore operation)

### Benefits

- **Lower Costs**: Automatic scaling down during idle periods
- **Better Performance**: Scales up automatically during high demand
- **Balanced Approach**: Level 50 provides optimal cost/performance trade-off
- **Production Ready**: Higher default capacity suitable for production workloads
- **Clearer UX**: Snapshot options are now more intuitive and prevent user errors
- **Simpler Commands**: Smart defaults reduce command complexity for common use cases

## [0.2.0] - 2024-01-15

### Added - Automatic Snapshot Creation

- **Automatic Snapshot Creation**: New `--create-snapshot` flag that automatically creates a snapshot from the provisioned cluster before restoring
- **Snapshot Progress Monitoring**: Real-time progress updates during snapshot creation
- **Timestamped Snapshots**: Automatic naming with timestamps (e.g., `cluster-migration-20240115-143022`)
- **Wait for Completion**: Automatically waits for snapshot to be available before proceeding

### Added - Workgroup/Namespace Creation

- **Automatic Creation**: New `--create-if-missing` flag to create serverless resources automatically
- **Three Creation Modes**:
  1. Create from new snapshot (with `--create-snapshot`)
  2. Restore from existing snapshot (with `--snapshot-name`)
  3. Create empty namespace (with `--admin-password`)
- **Smart Detection**: Checks if resources exist before attempting creation
- **Full Configuration**: Automatically applies VPC, IAM, and tag settings from source cluster

### Added - Parameter Group Mapping

- **Parameter Extraction**: Extracts parameter values from provisioned cluster parameter groups
- **Compatibility Validation**: Validates which parameters can be migrated to serverless
- **10+ Supported Parameters**: Including `enable_user_activity_logging`, `query_group`, `max_query_execution_time`, etc.
- **Automatic Mapping**: Maps provisioned parameters to serverless equivalents
- **Default Filtering**: Only migrates non-default, custom parameter values

### Added - Scheduled Queries Migration

- **EventBridge Integration**: Discovers and migrates EventBridge Rules
- **Scheduler Support**: Supports both EventBridge Rules and EventBridge Scheduler
- **Automatic IAM Role**: Creates execution role for query scheduling
- **Schedule Preservation**: Maintains cron/rate expressions and enabled/disabled state
- **Query Validation**: Validates queries before migration

### Enhanced

- **CLI Output**: Rich terminal UI with colored tables and progress indicators
- **Error Handling**: Improved error messages and recovery
- **Documentation**: Comprehensive guides for all new features
- **Examples**: Added multiple example scripts demonstrating new features

### Documentation

- Added `docs/WORKGROUP_CREATION.md` - Complete guide for workgroup/namespace creation
- Added `docs/PARAMETER_GROUPS.md` - Parameter group migration guide
- Added `docs/SCHEDULED_QUERIES.md` - Scheduled queries migration guide
- Updated `README.md` with new features and usage examples
- Added `examples/snapshot_migration.py` - Complete migration example
- Added `examples/advanced_migration.py` - Advanced features demonstration

## [0.1.0] - 2024-01-01

### Initial Release

- **Core Extraction**: Extract configuration from Redshift Provisioned clusters
- **IAM Roles**: Migrate IAM roles with default role preservation
- **VPC Configuration**: Migrate subnets, security groups, and network settings
- **Snapshot Schedules**: Extract snapshot schedule information
- **Logging Configuration**: Extract logging settings
- **Tags**: Migrate cluster tags
- **CLI Interface**: Command-line tool with extract, apply, and migrate commands
- **Dry-Run Mode**: Preview changes before applying
- **Configuration Files**: JSON-based configuration export/import

### Commands

- `redshift-migrate extract` - Extract cluster configuration
- `redshift-migrate apply` - Apply configuration to serverless
- `redshift-migrate migrate` - Full migration in one command

### Documentation

- Initial README with project overview
- Quick start guide
- Contributing guidelines
- Architecture documentation

---

## Upgrade Guide

### From 0.1.0 to 0.2.0

No breaking changes. All existing commands continue to work as before.

**New optional flags:**
- Add `--create-if-missing` to automatically create workgroup/namespace
- Add `--create-snapshot` to automatically create and restore from snapshot
- Add `--max-capacity` to specify maximum RPU for new workgroups (default: 512)

**Example upgrade:**

Before (0.1.0):
```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --workgroup my-workgroup \
  --namespace my-namespace
```

After (0.2.0+) - with automatic creation:
```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --workgroup my-workgroup \
  --namespace my-namespace \
  --create-if-missing \
  --create-snapshot \
  --max-capacity 512
```

### From 0.2.0 to 0.3.0

**Breaking Change:** The `--base-capacity` flag has been replaced with `--max-capacity`.

**Migration:**
- Replace `--base-capacity` with `--max-capacity` in all scripts
- Consider increasing capacity values (new default is 512 instead of 128)
- Workgroups now use price-performance target for automatic scaling

Before (0.2.0):
```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --workgroup my-workgroup \
  --namespace my-namespace \
  --create-if-missing \
  --base-capacity 128
```

After (0.3.0):
```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --workgroup my-workgroup \
  --namespace my-namespace \
  --create-if-missing \
  --max-capacity 512
```

## Future Roadmap

### Planned Features

- [ ] Snapshot schedule migration to serverless
- [ ] Lambda-based scheduler migration
- [ ] Step Functions workflow migration
- [ ] Rollback capabilities
- [ ] Pre-migration validation suite
- [ ] Post-migration verification
- [ ] Web UI for non-CLI users
- [ ] Multi-cluster batch migrations
- [ ] Cost estimation before migration
- [ ] Performance comparison reports

### Under Consideration

- [ ] Terraform module generation
- [ ] CloudFormation template export
- [ ] Integration with AWS Migration Hub
- [ ] Automated testing framework
- [ ] Migration progress dashboard
- [ ] Slack/Teams notifications
- [ ] Audit trail and compliance reporting

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to this project.

## License

MIT License - See [LICENSE](LICENSE) file for details.
