"""Create Redshift Serverless workgroups and namespaces."""

import boto3
import time
from typing import Optional, Dict, Any, List
from datetime import datetime


class WorkgroupCreator:
    """Create and manage Redshift Serverless workgroups and namespaces."""

    def __init__(self, region: Optional[str] = None, dry_run: bool = False):
        self.redshift_serverless = boto3.client("redshift-serverless", region_name=region)
        self.redshift = boto3.client("redshift", region_name=region)
        self.dry_run = dry_run
        self.region = region or boto3.Session().region_name

    def ensure_namespace_exists(
        self,
        namespace_name: str,
        admin_username: str = "admin",
        admin_password: Optional[str] = None,
        db_name: str = "dev",
        iam_roles: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Ensure namespace exists, create if it doesn't."""
        if self.dry_run:
            return {
                "dry_run": True,
                "action": "create_namespace",
                "namespace_name": namespace_name,
            }

        # Check if namespace exists
        try:
            response = self.redshift_serverless.get_namespace(namespaceName=namespace_name)
            return {
                "status": "exists",
                "namespace": response.get("namespace"),
                "message": f"Namespace {namespace_name} already exists",
            }
        except self.redshift_serverless.exceptions.ResourceNotFoundException:
            # Namespace doesn't exist, create it
            return self._create_namespace(
                namespace_name, admin_username, admin_password, db_name, iam_roles, tags
            )

    def _create_namespace(
        self,
        namespace_name: str,
        admin_username: str,
        admin_password: Optional[str],
        db_name: str,
        iam_roles: Optional[List[str]],
        tags: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Create a new namespace."""
        create_params = {
            "namespaceName": namespace_name,
            "adminUsername": admin_username,
            "dbName": db_name,
        }

        if admin_password:
            create_params["adminUserPassword"] = admin_password

        if iam_roles:
            create_params["iamRoles"] = iam_roles
            if iam_roles:
                create_params["defaultIamRoleArn"] = iam_roles[0]

        if tags:
            create_params["tags"] = [
                {"key": k, "value": v} for k, v in tags.items()
            ]

        try:
            response = self.redshift_serverless.create_namespace(**create_params)
            return {
                "status": "created",
                "namespace": response.get("namespace"),
                "message": f"Namespace {namespace_name} created successfully",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to create namespace {namespace_name}",
            }

    def ensure_workgroup_exists(
        self,
        workgroup_name: str,
        namespace_name: str,
        subnet_ids: List[str],
        security_group_ids: Optional[List[str]] = None,
        publicly_accessible: bool = False,
        max_capacity: int = 512,
        config_parameters: Optional[List[Dict[str, str]]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Ensure workgroup exists, create if it doesn't."""
        if self.dry_run:
            return {
                "dry_run": True,
                "action": "create_workgroup",
                "workgroup_name": workgroup_name,
                "namespace_name": namespace_name,
            }

        # Check if workgroup exists
        try:
            response = self.redshift_serverless.get_workgroup(workgroupName=workgroup_name)
            return {
                "status": "exists",
                "workgroup": response.get("workgroup"),
                "message": f"Workgroup {workgroup_name} already exists",
            }
        except self.redshift_serverless.exceptions.ResourceNotFoundException:
            # Workgroup doesn't exist, create it
            return self._create_workgroup(
                workgroup_name,
                namespace_name,
                subnet_ids,
                security_group_ids,
                publicly_accessible,
                max_capacity,
                config_parameters,
                tags,
            )

    def _create_workgroup(
        self,
        workgroup_name: str,
        namespace_name: str,
        subnet_ids: List[str],
        security_group_ids: Optional[List[str]],
        publicly_accessible: bool,
        max_capacity: int,
        config_parameters: Optional[List[Dict[str, str]]],
        tags: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Create a new workgroup with price-performance optimization."""
        create_params = {
            "workgroupName": workgroup_name,
            "namespaceName": namespace_name,
            "subnetIds": subnet_ids,
            "publiclyAccessible": publicly_accessible,
            # Use price-performance target instead of base capacity
            "maxCapacity": max_capacity,
            "pricePerformanceTarget": {
                "level": 50,  # Target level (1-100)
                "status": "ENABLED"
            },
        }

        if security_group_ids:
            create_params["securityGroupIds"] = security_group_ids

        if config_parameters:
            create_params["configParameters"] = config_parameters

        if tags:
            create_params["tags"] = [
                {"key": k, "value": v} for k, v in tags.items()
            ]

        try:
            response = self.redshift_serverless.create_workgroup(**create_params)
            return {
                "status": "created",
                "workgroup": response.get("workgroup"),
                "message": f"Workgroup {workgroup_name} created with price-performance optimization (target: 50, balanced)",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to create workgroup {workgroup_name}",
            }

    def create_snapshot_and_restore(
        self,
        cluster_identifier: str,
        namespace_name: str,
        workgroup_name: str,
        subnet_ids: List[str],
        security_group_ids: Optional[List[str]] = None,
        publicly_accessible: bool = False,
        max_capacity: int = 512,
        iam_roles: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
        wait_for_snapshot: bool = True,
    ) -> Dict[str, Any]:
        """Create a snapshot from provisioned cluster and restore to serverless.

        Process:
        1. Create snapshot from provisioned cluster
        2. Wait for snapshot to complete
        3. Create empty namespace
        4. Create workgroup linked to namespace
        5. Wait for both to be available
        6. Restore snapshot data into the namespace
        """
        if self.dry_run:
            return {
                "dry_run": True,
                "action": "create_snapshot_and_restore",
                "cluster_identifier": cluster_identifier,
                "namespace_name": namespace_name,
                "workgroup_name": workgroup_name,
            }

        try:
            # Step 1: Create snapshot
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            snapshot_name = f"{cluster_identifier}-migration-{timestamp}"

            print(f"Creating snapshot: {snapshot_name}")
            self.redshift.create_cluster_snapshot(
                SnapshotIdentifier=snapshot_name,
                ClusterIdentifier=cluster_identifier,
            )

            snapshot_info = {
                "snapshot_identifier": snapshot_name,
                "status": "creating",
                "cluster_identifier": cluster_identifier,
            }

            # Step 2: Wait for snapshot to complete
            if wait_for_snapshot:
                print(f"Waiting for snapshot to complete (this may take several minutes)...")
                self._wait_for_snapshot(snapshot_name)
                snapshot_info["status"] = "available"
                print(f"✓ Snapshot {snapshot_name} is ready")

            # Step 3: Create empty namespace
            print(f"Creating namespace: {namespace_name}")
            namespace_params = {
                "namespaceName": namespace_name,
                "adminUsername": "admin",
                "adminUserPassword": self._generate_temp_password(),
            }

            if iam_roles:
                namespace_params["iamRoles"] = iam_roles
                namespace_params["defaultIamRoleArn"] = iam_roles[0]

            if tags:
                namespace_params["tags"] = [{"key": k, "value": v} for k, v in tags.items()]

            namespace_response = self.redshift_serverless.create_namespace(**namespace_params)
            print(f"✓ Namespace creation initiated")
            
            # Wait for namespace to be AVAILABLE before creating workgroup
            print(f"Waiting for namespace to be ready...")
            self._wait_for_namespace_available(namespace_name)

            # Step 4: Create workgroup
            print(f"Creating workgroup: {workgroup_name}")
            workgroup_result = self._create_workgroup(
                workgroup_name,
                namespace_name,
                subnet_ids,
                security_group_ids,
                publicly_accessible,
                max_capacity,
                None,
                tags,
            )
            
            if workgroup_result.get("status") == "error":
                error_msg = workgroup_result.get("error", "Unknown error")
                print(f"✗ Workgroup creation failed: {error_msg}")
                raise Exception(f"Failed to create workgroup: {error_msg}")
            
            print(f"✓ Workgroup creation initiated")

            # Step 5: Wait for workgroup to be available
            self._wait_for_workgroup_available(workgroup_name)

            # Step 6: Restore snapshot data into the namespace
            print(f"Restoring snapshot data into namespace...")
            snapshot_response = self.redshift.describe_cluster_snapshots(
                SnapshotIdentifier=snapshot_name
            )
            snapshot_arn = snapshot_response["Snapshots"][0].get("SnapshotArn")

            print(f"  Snapshot ARN: {snapshot_arn}")
            restore_response = self.redshift_serverless.restore_from_snapshot(
                namespaceName=namespace_name,
                workgroupName=workgroup_name,
                snapshotArn=snapshot_arn,
            )

            print(f"✓ Snapshot restore initiated")
            print(f"  Waiting for restore to complete (this may take 10-30 minutes)...")

            # Wait for restore to complete
            self._wait_for_namespace_available(namespace_name)
            print(f"✓ Restore completed successfully")

            return {
                "status": "success",
                "snapshot": snapshot_info,
                "namespace": namespace_response.get("namespace"),
                "workgroup": workgroup_result,
                "message": f"Successfully created and restored to {namespace_name}",
            }

        except Exception as e:
            import traceback
            print(f"✗ Error: {str(e)}")
            print(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to create snapshot and restore: {str(e)}",
            }

    def _generate_temp_password(self) -> str:
        """Generate a temporary secure password for namespace creation.
        
        AWS Redshift requires passwords to use only printable ASCII characters
        except for: / @ " ' \ and space
        """
        import secrets
        import string

        # Use only allowed characters: letters, digits, and safe special chars
        alphabet = string.ascii_letters + string.digits + "!#$%&()*+,-.:<=>?[]^_{|}~"
        password = ''.join(secrets.choice(alphabet) for i in range(32))
        return password


    def _wait_for_snapshot(
        self, snapshot_identifier: str, max_wait_time: int = 3600
    ) -> None:
        """Wait for snapshot to become available."""
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                raise TimeoutError(
                    f"Snapshot {snapshot_identifier} did not complete within {max_wait_time} seconds"
                )
            
            try:
                response = self.redshift.describe_cluster_snapshots(
                    SnapshotIdentifier=snapshot_identifier
                )
                
                if response["Snapshots"]:
                    snapshot = response["Snapshots"][0]
                    status = snapshot.get("Status")
                    
                    if status == "available":
                        return
                    elif status == "failed":
                        raise Exception(f"Snapshot creation failed")
                    
                    # Print progress
                    progress = snapshot.get("CurrentBackupRateInMegaBytesPerSecond", 0)
                    if progress:
                        print(f"  Snapshot progress: {progress:.2f} MB/s")
                
            except Exception as e:
                if "SnapshotNotFound" not in str(e):
                    raise
            
            time.sleep(30)  # Check every 30 seconds

    def _wait_for_workgroup_available(
        self, workgroup_name: str, max_wait_time: int = 1800
    ) -> None:
        """Wait for workgroup to become available."""
        print(f"Waiting for workgroup to become available (this may take 5-15 minutes)...")
        start_time = time.time()
        last_status = None
        check_count = 0
        
        while True:
            elapsed = time.time() - start_time
            check_count += 1
            
            if elapsed > max_wait_time:
                print(f"\n✗ Timeout after {check_count} checks over {elapsed/60:.1f} minutes")
                print(f"  Last known status: {last_status}")
                print(f"\nPlease check the AWS console for workgroup status and any error messages.")
                raise TimeoutError(
                    f"Workgroup {workgroup_name} did not become available within {max_wait_time/60:.0f} minutes"
                )
            
            try:
                response = self.redshift_serverless.get_workgroup(
                    workgroupName=workgroup_name
                )
                
                workgroup = response.get("workgroup", {})
                status = workgroup.get("status")
                
                # Print status changes
                if status != last_status:
                    print(f"  Workgroup status: {status} (check #{check_count}, elapsed: {elapsed/60:.1f} min)")
                    last_status = status
                
                if status == "AVAILABLE":
                    print(f"✓ Workgroup {workgroup_name} is available")
                    return
                elif status in ["DELETING", "FAILED"]:
                    # Get more details about the failure
                    print(f"\n✗ Workgroup is in {status} state")
                    print(f"  Workgroup details: {workgroup}")
                    raise Exception(f"Workgroup {workgroup_name} is in {status} state")
                
            except Exception as e:
                error_str = str(e)
                if "ResourceNotFoundException" in error_str:
                    # Workgroup not found yet, keep waiting
                    if last_status != "NOT_FOUND":
                        print(f"  Workgroup status: Creating (not visible yet) - check #{check_count}")
                        last_status = "NOT_FOUND"
                else:
                    # Some other error
                    print(f"\n✗ Error checking workgroup status: {error_str}")
                    raise
            
            time.sleep(15)  # Check every 15 seconds

    def _wait_for_namespace_available(
        self, namespace_name: str, max_wait_time: int = 1800
    ) -> None:
        """Wait for namespace to become available."""
        print(f"Waiting for namespace to become available (this may take 10-30 minutes)...")
        start_time = time.time()
        last_status = None
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                raise TimeoutError(
                    f"Namespace {namespace_name} did not become available within {max_wait_time/60:.0f} minutes"
                )
            
            try:
                response = self.redshift_serverless.get_namespace(
                    namespaceName=namespace_name
                )
                
                namespace = response.get("namespace", {})
                status = namespace.get("status")
                
                # Print status changes
                if status != last_status:
                    print(f"  Namespace status: {status}")
                    last_status = status
                
                if status == "AVAILABLE":
                    print(f"✓ Namespace {namespace_name} is available")
                    return
                elif status in ["DELETING", "FAILED"]:
                    raise Exception(f"Namespace {namespace_name} is in {status} state")
                
            except Exception as e:
                error_str = str(e)
                if "ResourceNotFoundException" in error_str:
                    # Namespace not found yet, keep waiting
                    if last_status != "NOT_FOUND":
                        print(f"  Namespace status: Creating (not visible yet)")
                        last_status = "NOT_FOUND"
                else:
                    raise
            
            time.sleep(15)  # Check every 15 seconds

    def get_latest_snapshot(self, cluster_identifier: str) -> Optional[str]:
        """Get the most recent snapshot for a cluster."""
        try:
            response = self.redshift.describe_cluster_snapshots(
                ClusterIdentifier=cluster_identifier,
                SnapshotType="manual",
            )
            
            snapshots = response.get("Snapshots", [])
            if not snapshots:
                return None
            
            # Sort by creation time, most recent first
            snapshots.sort(
                key=lambda x: x.get("SnapshotCreateTime", datetime.min),
                reverse=True,
            )
            
            return snapshots[0].get("SnapshotIdentifier")
            
        except Exception as e:
            print(f"Warning: Could not get latest snapshot: {e}")
            return None

    def create_from_snapshot(
        self,
        namespace_name: str,
        workgroup_name: str,
        snapshot_name: str,
        subnet_ids: List[str],
        security_group_ids: Optional[List[str]] = None,
        publicly_accessible: bool = False,
        max_capacity: int = 512,
        iam_roles: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create namespace and workgroup from a snapshot."""
        if self.dry_run:
            return {
                "dry_run": True,
                "action": "create_from_snapshot",
                "snapshot_name": snapshot_name,
                "namespace_name": namespace_name,
                "workgroup_name": workgroup_name,
            }

        try:
            # Get the full snapshot ARN
            print(f"Looking up snapshot details...")
            try:
                snapshot_response = self.redshift.describe_cluster_snapshots(
                    SnapshotIdentifier=snapshot_name
                )
                if snapshot_response.get("Snapshots"):
                    snapshot_arn = snapshot_response["Snapshots"][0].get("SnapshotArn")
                    snapshot_cluster_id = snapshot_response["Snapshots"][0].get("ClusterIdentifier")
                    print(f"  Found snapshot ARN: {snapshot_arn}")
                    print(f"  Source cluster: {snapshot_cluster_id}")
                    
                    # Check if namespace name conflicts with existing cluster
                    if namespace_name == snapshot_cluster_id:
                        print(f"  ⚠ Warning: Namespace name matches source cluster name")
                        print(f"  This may cause conflicts. Consider using a different name.")
                else:
                    raise Exception(f"Snapshot {snapshot_name} not found")
            except Exception as e:
                print(f"✗ Error looking up snapshot: {e}")
                raise
            
            # Restore namespace from snapshot
            print(f"Calling restore_from_snapshot API...")
            
            # Try with both snapshotArn and snapshotName for compatibility
            namespace_params = {
                "namespaceName": namespace_name,
                "workgroupName": workgroup_name,
                "snapshotArn": snapshot_arn,
            }

            # Note: IAM roles cannot be set during restore, they must be added after
            # the namespace is created via update_namespace

            print(f"  Namespace: {namespace_name}")
            print(f"  Workgroup: {workgroup_name}")
            print(f"  Snapshot ARN: {snapshot_arn}")
            print(f"  Attempting restore...")
            
            try:
                namespace_response = self.redshift_serverless.restore_from_snapshot(
                    **namespace_params
                )
            except Exception as e:
                error_msg = str(e)
                print(f"✗ Restore failed: {error_msg}")
                
                # If it's a "not found" error, it might be a naming conflict
                if "not found" in error_msg.lower() and namespace_name == snapshot_cluster_id:
                    print(f"\n⚠ The namespace name '{namespace_name}' matches the source cluster name.")
                    print(f"  This may cause a conflict. Try using a different namespace name:")
                    print(f"  --namespace {namespace_name}-serverless")
                
                raise
            
            print(f"✓ Restore initiated successfully")
            print(f"  Namespace status: {namespace_response.get('namespace', {}).get('status', 'UNKNOWN')}")
            print(f"  Workgroup status: {namespace_response.get('workgroup', {}).get('status', 'UNKNOWN')}")

            # The restore creates both namespace and workgroup, so we don't need to create workgroup separately
            # But we may need to update it with additional settings
            
            # Wait for resources to be available before updating
            # (This will be done by the caller)

            return {
                "status": "created",
                "namespace": namespace_response.get("namespace"),
                "workgroup": namespace_response.get("workgroup"),
                "message": f"Created from snapshot {snapshot_name}",
                "iam_roles_pending": iam_roles,  # Store for later update
                "tags_pending": tags,  # Store for later update
            }

        except Exception as e:
            error_msg = str(e)
            print(f"✗ Error during restore: {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "message": f"Failed to create from snapshot {snapshot_name}",
            }
