"""Example: Advanced migration with parameter groups and scheduled queries."""

from redshift_migrate.extractors import (
    ProvisionedClusterExtractor,
    ParameterGroupExtractor,
    ScheduledQueryExtractor,
)
from redshift_migrate.transformers import ConfigMapper
from redshift_migrate.appliers import ServerlessWorkgroupApplier


def main():
    """Run an advanced migration with all features."""
    # Configuration
    cluster_id = "my-provisioned-cluster"
    workgroup_name = "my-serverless-workgroup"
    namespace_name = "my-serverless-namespace"
    region = "us-east-1"
    
    print("=" * 80)
    print("REDSHIFT PROVISIONED TO SERVERLESS MIGRATION")
    print("=" * 80)
    
    # Step 1: Extract configuration
    print(f"\n[1/5] Extracting configuration from cluster: {cluster_id}")
    extractor = ProvisionedClusterExtractor(region=region)
    config = extractor.extract(cluster_id)
    
    print(f"  ✓ Found {len(config.iam_roles)} IAM roles")
    print(f"  ✓ Found {len(config.vpc_config.subnet_ids)} subnets")
    print(f"  ✓ Found {len(config.vpc_config.security_group_ids)} security groups")
    
    # Step 2: Display parameter group information
    if config.parameter_group_info:
        print(f"\n[2/5] Parameter Group: {config.parameter_group_info.name}")
        print(f"  ✓ Found {len(config.parameter_group_info.parameters)} mappable parameters")
        
        for param_name, param_info in config.parameter_group_info.parameters.items():
            print(f"    - {param_name}: {param_info['value']}")
    else:
        print("\n[2/5] No custom parameter group found")
    
    # Step 3: Display scheduled queries
    if config.scheduled_queries:
        print(f"\n[3/5] Found {len(config.scheduled_queries)} scheduled queries")
        for query in config.scheduled_queries:
            print(f"  ✓ {query.rule_name}")
            print(f"    Schedule: {query.schedule_expression}")
            print(f"    Database: {query.database}")
            print(f"    Enabled: {query.enabled}")
    else:
        print("\n[3/5] No scheduled queries found")
    
    # Step 4: Transform configuration
    print(f"\n[4/5] Transforming configuration for serverless")
    mapper = ConfigMapper()
    serverless_config = mapper.transform(config, workgroup_name, namespace_name)
    
    print(f"  ✓ Mapped {len(serverless_config.config_parameters)} parameters")
    print(f"  ✓ Configured {len(serverless_config.iam_roles)} IAM roles")
    
    # Step 5: Apply configuration (dry-run)
    print(f"\n[5/5] Dry-run preview for workgroup: {workgroup_name}")
    applier = ServerlessWorkgroupApplier(region=region, dry_run=True)
    result = applier.apply(serverless_config, config.scheduled_queries)
    
    print("\nDry-run results:")
    print(f"  Workgroup: {result['workgroup_name']}")
    print(f"  Namespace: {result['namespace_name']}")
    
    if "scheduled_queries" in result.get("changes", {}):
        sq_info = result["changes"]["scheduled_queries"]
        print(f"  Scheduled Queries: {sq_info.get('total_queries', 0)} to be created")
    
    print("\n" + "=" * 80)
    print("DRY-RUN COMPLETE - No changes were made")
    print("=" * 80)
    print("\nTo apply these changes for real, run:")
    print(f"  redshift-migrate migrate \\")
    print(f"    --cluster-id {cluster_id} \\")
    print(f"    --workgroup {workgroup_name} \\")
    print(f"    --namespace {namespace_name} \\")
    print(f"    --region {region}")


if __name__ == "__main__":
    main()
