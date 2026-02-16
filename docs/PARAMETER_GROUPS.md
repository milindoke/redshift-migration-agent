# Parameter Group Migration

## Overview

Parameter groups in Redshift Provisioned clusters contain database configuration settings. When migrating to Serverless, these parameters need to be mapped to workgroup configuration parameters.

## Supported Parameters

The following parameters can be automatically migrated from provisioned to serverless:

| Provisioned Parameter | Serverless Parameter | Description |
|----------------------|---------------------|-------------|
| `enable_user_activity_logging` | `enable_user_activity_logging` | Enable user activity logging |
| `query_group` | `query_group` | Query group for workload management |
| `max_query_execution_time` | `max_query_execution_time` | Maximum query execution time |
| `enable_case_sensitive_identifier` | `enable_case_sensitive_identifier` | Case-sensitive identifiers |
| `search_path` | `search_path` | Schema search path |
| `statement_timeout` | `statement_timeout` | Statement timeout |
| `datestyle` | `datestyle` | Date style format |
| `timezone` | `timezone` | Timezone setting |
| `require_ssl` | `require_ssl` | Require SSL connections |
| `use_fips_ssl` | `use_fips_ssl` | Use FIPS SSL |

## How It Works

1. **Extraction**: The tool reads the parameter group associated with your provisioned cluster
2. **Filtering**: Only non-default, modified parameters are extracted
3. **Mapping**: Parameters are mapped to their serverless equivalents
4. **Validation**: The tool validates which parameters are compatible with serverless
5. **Application**: Compatible parameters are applied to the serverless workgroup

## Usage

### Extract Parameter Information

```bash
redshift-migrate extract \
  --cluster-id my-cluster \
  --output config.json
```

The output will include parameter group information:

```json
{
  "parameter_group_info": {
    "name": "my-parameter-group",
    "family": "redshift-1.0",
    "parameters": {
      "enable_user_activity_logging": {
        "value": "true",
        "data_type": "boolean"
      },
      "max_query_execution_time": {
        "value": "3600000",
        "data_type": "integer"
      }
    }
  }
}
```

### Preview Parameter Migration

```bash
redshift-migrate apply \
  --config config.json \
  --workgroup my-workgroup \
  --namespace my-namespace \
  --dry-run
```

### Apply Parameters

```bash
redshift-migrate apply \
  --config config.json \
  --workgroup my-workgroup \
  --namespace my-namespace
```

## Incompatible Parameters

Some provisioned cluster parameters are not available in Serverless:

- Node-specific settings (node type, number of nodes)
- Cluster-specific maintenance settings
- Some WLM (Workload Management) parameters

The tool will warn you about incompatible parameters during extraction.

## Manual Configuration

For parameters that cannot be automatically migrated, you'll need to:

1. Review the incompatible parameters list
2. Manually configure equivalent settings in Serverless (if available)
3. Update your application configuration as needed

## Best Practices

1. **Test First**: Always use `--dry-run` to preview changes
2. **Review Parameters**: Check the extracted parameters before applying
3. **Document Changes**: Keep track of any manual adjustments needed
4. **Validate**: Test your workload after migration to ensure parameters are working correctly

## Troubleshooting

### "Parameter not found in parameter group"
- The parameter group may be using default values
- Check if the parameter group is correctly associated with the cluster

### "Parameter not supported in Serverless"
- Some parameters are provisioned-only
- Check the Serverless documentation for alternatives

### "Permission denied"
- Ensure your IAM role has `redshift:DescribeClusterParameters` permission
