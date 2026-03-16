# Migration Execution Guide: Provisioned to Serverless

## Execution Order (Critical)

Follow this exact order. Do NOT skip steps or reorder.

1. **Create snapshot** of the source Provisioned cluster
2. **Create namespace** — wait for AVAILABLE status
3. **Create workgroup(s)** — wait for AVAILABLE status
4. **Verify association** — namespace and workgroup must be associated
5. **Restore snapshot** into the namespace
6. **Set up data sharing** (if hub-and-spoke pattern)
7. **Validate data** — run sample queries
8. **Plan user migration** — connection string changes
9. **Performance validation** — compare against baseline
10. **Cutover planning** — DNS/endpoint switch

## Step Details

### Creating Snapshots

- Always create a fresh manual snapshot before migration — don't rely on automated snapshots
- Tag the snapshot with `created-by: redshift-modernization-agent` for tracking
- Snapshot creation time depends on cluster size and change rate
- For large clusters (>10TB), snapshot may take 30+ minutes

### Creating Namespace

- Use `manageAdminPassword=True` to let Secrets Manager handle admin credentials
- Namespace names must be unique within the account and region
- Wait for status `AVAILABLE` before creating workgroups
- If creation fails, check: namespace name conflicts, service quotas, IAM permissions

### Creating Workgroups

- Each workgroup must be associated with exactly one namespace
- Workgroup names must be unique within the account and region
- Prefer to use price-performance mode, set the target via `pricePerformanceTarget`
- Else set `baseCapacity` (base RPU) and `maxCapacity` (max RPU) per architecture spec
- Wait for status `AVAILABLE` before proceeding to snapshot restore

### Restoring Snapshots

- Restore overwrites the namespace's data
- Restore from encrypted snapshots requires the same KMS key access
- Restore time depends on data volume: ~1TB per 10-15 minutes typically
- After restore, verify data by running: `SELECT COUNT(*) FROM information_schema.tables;`

### Common Errors and Solutions

| Error | Cause | Solution |
|---|---|---|
| `NamespaceNotFound` | Namespace not yet available | Wait and retry |
| `ConflictException` | Resource already exists | Check if previous attempt partially succeeded |
| `AccessDenied` | Missing IAM permissions | Check Lambda execution role |
| `InvalidParameterValue` | Invalid RPU value | Ensure base_rpu >= 32 and is a valid RPU increment |
| `ServiceQuotaExceeded` | Account limit reached | Request quota increase via AWS Support |
| `SnapshotNotFound` | Snapshot doesn't exist or wrong region | Verify snapshot ID and region |

## Rollback Procedures

Every step must have a rollback. Execute rollbacks in reverse order:

1. **Snapshot restore rollback**: Drop all tables in the namespace, or delete and recreate namespace
2. **Workgroup rollback**: `DeleteWorkgroup` — removes compute but preserves namespace data
3. **Namespace rollback**: `DeleteNamespace` — removes all data and the namespace
4. **Snapshot rollback**: `DeleteClusterSnapshot` — removes the migration snapshot

## Performance Validation

Run representative queries on both Provisioned and Serverless to compare:

```sql
-- Check table counts
SELECT schemaname, COUNT(*) as table_count 
FROM pg_tables 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
GROUP BY schemaname;

-- Check row counts for key tables
SELECT COUNT(*) FROM <your_table>;

-- Run a typical analytical query and measure execution time
-- Compare with the same query on the Provisioned cluster
```

Acceptable performance delta: within 20% of Provisioned cluster baseline. If Serverless is >20% slower on critical queries, consider increasing RPU.

## Cutover Planning

### Zero-Downtime Approach
1. Keep Provisioned cluster running during migration
2. Set up Serverless with restored data
3. Run dual-write period (optional, for real-time data)
4. Switch application endpoints to Serverless
5. Monitor for 1-2 hours
6. Keep Provisioned cluster for 72-hour rollback window
7. Decommission Provisioned cluster after validation period

### Maintenance Window Approach
1. Pause writes to Provisioned cluster
2. Take final snapshot
3. Restore to Serverless
4. Switch endpoints
5. Resume operations on Serverless
6. Estimated downtime: 15-60 minutes depending on data volume
