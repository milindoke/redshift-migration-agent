"""Example: Simple migration using smart defaults for naming."""

from redshift_migrate.extractors import ProvisionedClusterExtractor
from redshift_migrate.transformers import ConfigMapper
from redshift_migrate.appliers import ServerlessWorkgroupApplier, WorkgroupCreator


def main():
    """Run a simple migration using smart defaults.
    
    This example demonstrates the simplest migration approach:
    - Workgroup name automatically set to cluster_id
    - Namespace name automatically set to cluster_id (same as workgroup)
    - Automatic snapshot creation
    - Price-performance optimization enabled
    """
    # Configuration
    cluster_id = "prod-cluster"
    region = "us-east-1"
    max_capacity = 512  # RPU
    
    # Smart defaults will be applied:
    # - workgroup_name = "prod-cluster"
    # - namespace_name = "prod-cluster"
    
    print("=" * 80)
    print("SIMPLE MIGRATION WITH SMART DEFAULTS")
    print("=" * 80)
    print(f"\nCluster ID: {cluster_id}")
    print(f"Workgroup (default): {cluster_id}")
    print(f"Namespace (default): {cluster_id}-ns")
    print(f"Max Capacity: {max_capacity} RPU")
    print(f"Price-Performance: Level 50 (balanced)")
    
    # Step 1: Extract configuration
    print(f"\n[1/4] Extracting configuration from cluster: {cluster_id}")
    extractor = ProvisionedClusterExtractor(region=region)
    config = extractor.extract(cluster_id)
    
    print(f"  ✓ Found {len(config.iam_roles)} IAM roles")
    print(f"  ✓ Found {len(config.vpc_config.subnet_ids)} subnets")
    print(f"  ✓ Found {len(config.scheduled_queries)} scheduled queries")
    
    if config.parameter_group_info:
        print(f"  ✓ Found {len(config.parameter_group_info.parameters)} parameters")
    
    # Step 2: Create snapshot and restore with smart defaults
    print(f"\n[2/4] Creating snapshot and restoring to serverless")
    print(f"  Using smart defaults:")
    print(f"    Workgroup: {cluster_id}")
    print(f"    Namespace: {cluster_id}-ns")
    
    creator = WorkgroupCreator(region=region, dry_run=False)
    
    result = creator.create_snapshot_and_restore(
        cluster_identifier=cluster_id,
        namespace_name=cluster_id,  # Smart default: same as cluster_id
        workgroup_name=cluster_id,  # Smart default: same as cluster_id
        subnet_ids=config.vpc_config.subnet_ids,
        security_group_ids=config.vpc_config.security_group_ids,
        publicly_accessible=config.vpc_config.publicly_accessible,
        max_capacity=max_capacity,
        iam_roles=[role.role_arn for role in config.iam_roles],
        tags=config.tags,
    )
    
    if result["status"] == "success":
        print(f"  ✓ Snapshot created: {result['snapshot']['snapshot_identifier']}")
        print(f"  ✓ Namespace restored: {cluster_id}")
        print(f"  ✓ Workgroup created: {cluster_id}")
    else:
        print(f"  ✗ Error: {result.get('error')}")
        return
    
    # Step 3: Transform configuration
    print(f"\n[3/4] Transforming configuration")
    mapper = ConfigMapper()
    serverless_config = mapper.transform(
        config, 
        cluster_id,  # workgroup name
        cluster_id   # namespace name
    )
    
    print(f"  ✓ Mapped {len(serverless_config.config_parameters)} parameters")
    print(f"  ✓ Configured {len(serverless_config.iam_roles)} IAM roles")
    
    # Step 4: Apply additional configuration
    print(f"\n[4/4] Applying additional configuration")
    applier = ServerlessWorkgroupApplier(region=region, dry_run=False)
    apply_result = applier.apply(serverless_config, config.scheduled_queries)
    
    print(f"  ✓ Workgroup configuration applied")
    print(f"  ✓ Namespace IAM roles updated")
    
    if config.scheduled_queries:
        print(f"  ✓ {len(config.scheduled_queries)} scheduled queries migrated")
    
    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE!")
    print("=" * 80)
    print(f"\nYour serverless workgroup is ready:")
    print(f"  Namespace: {cluster_id}")
    print(f"  Workgroup: {cluster_id}")
    print(f"  Max Capacity: {max_capacity} RPU")
    print(f"  Price-Performance: Level 50 (balanced)")
    print(f"  Snapshot: {result['snapshot']['snapshot_identifier']}")
    print(f"\nConnection endpoint:")
    print(f"  Use the same database name and credentials as your provisioned cluster")
    print(f"  Update your connection string to use the new serverless endpoint")
    print(f"\nNext steps:")
    print(f"  1. Verify workgroup is in 'AVAILABLE' state")
    print(f"  2. Test database connectivity")
    print(f"  3. Update application connection strings")
    print(f"  4. Monitor performance and adjust capacity as needed")
    print(f"\nCLI equivalent:")
    print(f"  redshift-migrate migrate \\")
    print(f"    --cluster-id {cluster_id} \\")
    print(f"    --create-if-missing \\")
    print(f"    --create-snapshot \\")
    print(f"    --max-capacity {max_capacity} \\")
    print(f"    --region {region}")


if __name__ == "__main__":
    main()
