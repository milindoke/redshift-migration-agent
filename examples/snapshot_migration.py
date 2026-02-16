"""Example: Complete migration with automatic snapshot creation."""

from redshift_migrate.extractors import ProvisionedClusterExtractor
from redshift_migrate.transformers import ConfigMapper
from redshift_migrate.appliers import ServerlessWorkgroupApplier, WorkgroupCreator


def main():
    """Run a complete migration with automatic snapshot creation.
    
    Note: When using create_snapshot_and_restore(), you don't need to provide
    a snapshot name. The tool automatically creates a new snapshot with a
    timestamped name (e.g., 'cluster-migration-20240115-143022').
    
    This example uses explicit names, but you could also use smart defaults:
    - workgroup_name would default to cluster_id
    - namespace_name would default to f"{workgroup_name}-ns"
    """
    # Configuration
    cluster_id = "prod-cluster"
    workgroup_name = "prod-serverless"  # Or use cluster_id for default
    namespace_name = "prod-namespace"   # Or use f"{workgroup_name}-ns" for default
    region = "us-east-1"
    max_capacity = 512  # RPU (maximum capacity with price-performance target)
    
    print("=" * 80)
    print("COMPLETE MIGRATION WITH AUTOMATIC SNAPSHOT")
    print("=" * 80)
    
    # Step 1: Extract configuration
    print(f"\n[1/4] Extracting configuration from cluster: {cluster_id}")
    extractor = ProvisionedClusterExtractor(region=region)
    config = extractor.extract(cluster_id)
    
    print(f"  ✓ Found {len(config.iam_roles)} IAM roles")
    print(f"  ✓ Found {len(config.vpc_config.subnet_ids)} subnets")
    print(f"  ✓ Found {len(config.scheduled_queries)} scheduled queries")
    
    if config.parameter_group_info:
        print(f"  ✓ Found {len(config.parameter_group_info.parameters)} parameters")
    
    # Step 2: Create snapshot and restore
    print(f"\n[2/4] Creating snapshot and restoring to serverless")
    creator = WorkgroupCreator(region=region, dry_run=False)
    
    # Option 1: Automatically create a new snapshot (recommended)
    # This creates a timestamped snapshot automatically
    result = creator.create_snapshot_and_restore(
        cluster_identifier=cluster_id,
        namespace_name=namespace_name,
        workgroup_name=workgroup_name,
        subnet_ids=config.vpc_config.subnet_ids,
        security_group_ids=config.vpc_config.security_group_ids,
        publicly_accessible=config.vpc_config.publicly_accessible,
        max_capacity=max_capacity,
        iam_roles=[role.role_arn for role in config.iam_roles],
        tags=config.tags,
    )
    
    # Option 2: Use an existing snapshot (alternative approach)
    # Uncomment the following to restore from an existing snapshot instead:
    # result = creator.create_from_snapshot(
    #     namespace_name=namespace_name,
    #     workgroup_name=workgroup_name,
    #     snapshot_name="my-existing-snapshot",
    #     subnet_ids=config.vpc_config.subnet_ids,
    #     security_group_ids=config.vpc_config.security_group_ids,
    #     publicly_accessible=config.vpc_config.publicly_accessible,
    #     max_capacity=max_capacity,
    #     iam_roles=[role.role_arn for role in config.iam_roles],
    #     tags=config.tags,
    # )
    
    if result["status"] == "success":
        print(f"  ✓ Snapshot created: {result['snapshot']['snapshot_identifier']}")
        print(f"  ✓ Namespace restored: {namespace_name}")
        print(f"  ✓ Workgroup created: {workgroup_name}")
    else:
        print(f"  ✗ Error: {result.get('error')}")
        return
    
    # Step 3: Transform configuration
    print(f"\n[3/4] Transforming configuration")
    mapper = ConfigMapper()
    serverless_config = mapper.transform(config, workgroup_name, namespace_name)
    
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
    print(f"  Namespace: {namespace_name}")
    print(f"  Workgroup: {workgroup_name}")
    print(f"  Max Capacity: {max_capacity} RPU")
    print(f"  Price-Performance: Level 50 (balanced)")
    print(f"  Snapshot: {result['snapshot']['snapshot_identifier']}")
    print(f"\nNext steps:")
    print(f"  1. Verify workgroup is in 'AVAILABLE' state")
    print(f"  2. Test database connectivity")
    print(f"  3. Update application connection strings")
    print(f"  4. Monitor performance and adjust capacity as needed")


if __name__ == "__main__":
    main()
