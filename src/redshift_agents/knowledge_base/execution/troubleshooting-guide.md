# Migration Troubleshooting Guide

## IAM Permission Errors

### "Access Denied" on CreateNamespace
**Cause**: Lambda execution role missing `redshift-serverless:CreateNamespace`
**Fix**: Ensure the execution Lambda role has `AmazonRedshiftFullAccess` managed policy

### "Access Denied" on CreateClusterSnapshot
**Cause**: Lambda execution role missing `redshift:CreateClusterSnapshot`
**Fix**: Ensure the execution Lambda role has `AmazonRedshiftFullAccess` managed policy

### "Cannot access secret for this namespace"
**Cause**: Missing Secrets Manager permissions when using `manageAdminPassword=True`
**Fix**: Add `secretsmanager:CreateSecret`, `secretsmanager:GetSecretValue`, `secretsmanager:TagResource` to the Lambda role

### "User does not exist" on Data API calls
**Cause**: `DbUser` parameter specifies a user that doesn't exist in the Redshift cluster
**Fix**: Use IAM authentication without `DbUser`, or use the cluster's master username

## Namespace and Workgroup Errors

### "Namespace already exists"
**Cause**: A namespace with the same name already exists in the account/region
**Fix**: Use a unique namespace name, or delete the existing one if it's from a failed previous attempt

### "Workgroup already exists"
**Cause**: A workgroup with the same name already exists
**Fix**: Use a unique workgroup name, or delete the existing one

### Workgroup stuck in "CREATING" status
**Cause**: Resource provisioning is taking longer than expected
**Fix**: Wait up to 10 minutes. If still creating after 10 minutes, check CloudTrail for errors.

### Namespace stuck in "MODIFYING" after restore
**Cause**: Snapshot restore is in progress
**Fix**: Wait for restore to complete. Large datasets (>5TB) can take 30+ minutes.

## Snapshot Errors

### "Snapshot not found"
**Cause**: Snapshot ID is incorrect, or snapshot is in a different region
**Fix**: Verify the snapshot identifier and ensure it's in the same region as the target namespace

### "Snapshot is not in available state"
**Cause**: Snapshot is still being created
**Fix**: Wait for snapshot status to become `available` before attempting restore

### Restore fails with encryption error
**Cause**: Target namespace doesn't have access to the KMS key used to encrypt the snapshot
**Fix**: Ensure the namespace's IAM role has `kms:Decrypt` permission on the snapshot's KMS key

## Data Sharing Errors

### "Datashare not found"
**Cause**: Datashare hasn't been created yet, or wrong name
**Fix**: Create the datashare on the producer namespace first

### "Cannot grant to namespace"
**Cause**: Consumer namespace ID is incorrect
**Fix**: Use `get_namespace` to retrieve the correct namespace ID (not the name)

### Consumer can't see shared data
**Cause**: Consumer hasn't created a database from the datashare
**Fix**: On the consumer, run `CREATE DATABASE shared_db FROM DATASHARE <name> OF NAMESPACE '<producer_id>';`

## Performance Issues

### Queries slower on Serverless than Provisioned
**Possible causes**:
1. **Cold start**: First queries after idle period are slower. Run warm-up queries.
2. **Insufficient RPU**: Increase base RPU or switch to price-performance mode with higher target.
3. **Different query plan**: Serverless optimizer may choose different plans. Check `EXPLAIN` output.
4. **Data distribution**: After restore, run `VACUUM` and `ANALYZE` to optimize data layout.

### Recommended post-restore optimization
```sql
VACUUM FULL;
ANALYZE;
```

## Lambda Timeout Errors

### Lambda times out during execution
**Cause**: Operation takes longer than Lambda timeout (120 seconds for execution Lambda)
**Fix**: For long-running operations (snapshot creation, restore), the Lambda should initiate the operation and return immediately. The agent should poll for completion in subsequent calls.
