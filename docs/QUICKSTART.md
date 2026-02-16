# Quick Start Guide

## Prerequisites

1. **AWS Credentials**: Configure AWS credentials with appropriate permissions
2. **Python 3.9+**: Ensure Python is installed
3. **Existing Resources**:
   - A Redshift Provisioned cluster to migrate from
   - A Redshift Serverless namespace and workgroup (can be created via snapshot restore)

## Installation

```bash
pip install -e .
```

## Basic Usage

### 1. Extract Configuration

Extract configuration from your provisioned cluster:

```bash
redshift-migrate extract \
  --cluster-id my-cluster \
  --output cluster-config.json \
  --region us-east-1
```

This will save the configuration to `cluster-config.json`.

### 2. Preview Changes (Dry Run)

Preview what changes will be made without actually applying them:

```bash
redshift-migrate apply \
  --config cluster-config.json \
  --workgroup my-workgroup \
  --namespace my-namespace \
  --dry-run \
  --region us-east-1
```

### 3. Apply Configuration

Apply the configuration to your serverless workgroup:

```bash
redshift-migrate apply \
  --config cluster-config.json \
  --workgroup my-workgroup \
  --namespace my-namespace \
  --region us-east-1
```

### 4. Full Migration (One Command)

Or do everything in one command:

```bash
redshift-migrate migrate \
  --cluster-id my-cluster \
  --workgroup my-workgroup \
  --namespace my-namespace \
  --region us-east-1
```

## What Gets Migrated

✅ **Currently Supported:**
- IAM roles (including default role)
- VPC configuration (subnets, security groups)
- Network accessibility settings
- Tags
- Basic configuration parameters

🚧 **Coming Soon:**
- Snapshot schedules
- Scheduled queries (EventBridge rules)
- Parameter group values
- Logging configuration
- Maintenance window settings

## Required IAM Permissions

Your AWS credentials need the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift:DescribeClusters",
        "redshift:DescribeClusterSubnetGroups",
        "redshift:DescribeSnapshotSchedules",
        "redshift:DescribeTags",
        "redshift-serverless:UpdateWorkgroup",
        "redshift-serverless:UpdateNamespace",
        "redshift-serverless:GetWorkgroup",
        "redshift-serverless:GetNamespace"
      ],
      "Resource": "*"
    }
  ]
}
```

## Troubleshooting

### "Cluster not found"
- Verify the cluster identifier is correct
- Ensure you're using the correct AWS region
- Check your AWS credentials have permission to describe clusters

### "Access denied"
- Verify your IAM permissions
- Ensure your credentials are properly configured

### "Workgroup not found"
- Ensure the serverless workgroup exists
- Verify the workgroup name is correct
- Check you're using the correct region

## Next Steps

- Review the [Architecture](ARCHITECTURE.md) document
- Check out [examples/](../examples/) for more usage patterns
- Read [CONTRIBUTING.md](../CONTRIBUTING.md) to contribute
