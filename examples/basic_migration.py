"""Example: Basic migration from provisioned to serverless."""

from redshift_migrate.extractors import ProvisionedClusterExtractor
from redshift_migrate.transformers import ConfigMapper
from redshift_migrate.appliers import ServerlessWorkgroupApplier


def main():
    """Run a basic migration."""
    # Configuration
    cluster_id = "my-provisioned-cluster"
    workgroup_name = "my-serverless-workgroup"
    namespace_name = "my-serverless-namespace"
    region = "us-east-1"
    
    # Step 1: Extract configuration from provisioned cluster
    print(f"Extracting configuration from {cluster_id}...")
    extractor = ProvisionedClusterExtractor(region=region)
    provisioned_config = extractor.extract(cluster_id)
    
    print(f"Found {len(provisioned_config.iam_roles)} IAM roles")
    print(f"Found {len(provisioned_config.vpc_config.subnet_ids)} subnets")
    
    # Step 2: Transform to serverless configuration
    print("\nTransforming configuration...")
    mapper = ConfigMapper()
    serverless_config = mapper.transform(
        provisioned_config,
        workgroup_name,
        namespace_name
    )
    
    # Step 3: Apply to serverless workgroup (dry-run first)
    print("\nDry-run preview...")
    applier = ServerlessWorkgroupApplier(region=region, dry_run=True)
    dry_run_result = applier.apply(serverless_config)
    print(dry_run_result)
    
    # Step 4: Apply for real (uncomment when ready)
    # print("\nApplying configuration...")
    # applier = ServerlessWorkgroupApplier(region=region, dry_run=False)
    # result = applier.apply(serverless_config)
    # print(result)


if __name__ == "__main__":
    main()
