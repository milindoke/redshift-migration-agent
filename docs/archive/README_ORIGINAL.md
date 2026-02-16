# Redshift Provisioned to Serverless Migration Tool

A Python CLI tool and conversational AI agent to migrate Amazon Redshift Provisioned cluster configurations to Redshift Serverless workgroups.

## Problem Statement

When migrating from Redshift Provisioned to Serverless, snapshot restore handles data and permissions, but compute configurations (IAM roles, VPC settings, scheduled queries, etc.) must be manually recreated. This tool automates that gap.

## Two Ways to Use

### 1. CLI Tool (Traditional)
Command-line interface for scripting and automation.

### 2. AI Agent (Conversational)
Strand-powered conversational agent that guides you through migration.

**Quick start with the agent:**
```bash
./deploy_agent.sh
python redshift_agent.py
```

See [AGENT_README.md](AGENT_README.md) for details.

## Features

- ✅ Extract IAM roles from provisioned clusters
- ✅ Migrate VPC and security group configurations
- ✅ Transfer snapshot schedules
- ✅ Migrate scheduled queries (EventBridge rules)
- ✅ Extract and map parameter group settings
- ✅ Apply parameter group equivalents to serverless
- ✅ Preserve logging and monitoring settings
- ✅ Automatic snapshot creation and restore
- ✅ Create serverless workgroups and namespaces
- ✅ Validation and dry-run mode
- ✅ Comprehensive CLI with rich output

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Extract configuration from provisioned cluster
redshift-migrate extract --cluster-id my-cluster --output config.json

# Preview changes (dry-run)
redshift-migrate apply --config config.json --dry-run

# Apply to serverless workgroup
redshift-migrate apply --config config.json

# Full migration with automatic snapshot creation (recommended)
# Uses smart defaults: workgroup = cluster-id, namespace = cluster-id
redshift-migrate migrate \
  --cluster-id my-cluster \
  --create-if-missing \
  --create-snapshot \
  --max-capacity 512

# Or with custom names
redshift-migrate migrate \
  --cluster-id my-cluster \
  --workgroup my-workgroup \
  --namespace my-namespace \
  --create-if-missing \
  --create-snapshot \
  --max-capacity 512
```

## Requirements

- Python 3.9+
- AWS credentials configured
- Appropriate IAM permissions for Redshift and related services

## Documentation

- [Quick Start Guide](docs/QUICKSTART.md)
- [Workgroup Creation](docs/WORKGROUP_CREATION.md)
- [Parameter Group Migration](docs/PARAMETER_GROUPS.md)
- [Scheduled Queries Migration](docs/SCHEDULED_QUERIES.md)
- [Contributing Guide](CONTRIBUTING.md)

## Architecture

```
Extract → Transform → Validate → Apply
```

## License

MIT
