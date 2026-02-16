"""Command-line interface for Redshift migration tool."""

import json
import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from .extractors import ProvisionedClusterExtractor
from .transformers import ConfigMapper
from .appliers import ServerlessWorkgroupApplier, WorkgroupCreator

console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """Redshift Provisioned to Serverless Migration Tool."""
    pass


@main.command()
@click.option("--cluster-id", required=True, help="Provisioned cluster identifier")
@click.option("--output", type=click.Path(), help="Output file for configuration")
@click.option("--region", help="AWS region")
def extract(cluster_id: str, output: str, region: str) -> None:
    """Extract configuration from a provisioned cluster."""
    console.print(f"[bold blue]Extracting configuration from cluster: {cluster_id}[/bold blue]")
    
    try:
        extractor = ProvisionedClusterExtractor(region=region)
        config = extractor.extract(cluster_id)
        
        # Display summary
        _display_config_summary(config)
        
        # Save to file if specified
        if output:
            with open(output, "w") as f:
                json.dump(config.model_dump(), f, indent=2, default=str)
            console.print(f"[green]✓ Configuration saved to {output}[/green]")
        else:
            rprint(config.model_dump_json(indent=2))
            
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise click.Abort()


@main.command()
@click.option("--config", type=click.Path(exists=True), required=True, help="Config file")
@click.option("--workgroup", help="Serverless workgroup name (default: <cluster-id>-serverless)")
@click.option("--namespace", help="Serverless namespace name (default: same as workgroup)")
@click.option("--create-if-missing", is_flag=True, help="Create workgroup/namespace if they don't exist")
@click.option("--create-snapshot", is_flag=True, help="Create a new snapshot from cluster before restoring (mutually exclusive with --snapshot-name)")
@click.option("--snapshot-name", help="Snapshot name to restore from (mutually exclusive with --create-snapshot)")
@click.option("--admin-username", default="admin", help="Admin username for new namespace")
@click.option("--admin-password", help="Admin password for new namespace")
@click.option("--max-capacity", type=int, default=512, help="Maximum capacity for workgroup (RPU, default: 512)")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--region", help="AWS region")
def apply(
    config: str,
    workgroup: str,
    namespace: str,
    create_if_missing: bool,
    create_snapshot: bool,
    snapshot_name: str,
    admin_username: str,
    admin_password: str,
    max_capacity: int,
    dry_run: bool,
    region: str,
) -> None:
    """Apply configuration to a serverless workgroup."""
    
    try:
        # Load configuration
        with open(config, "r") as f:
            config_data = json.load(f)
        
        from .models import ProvisionedClusterConfig
        provisioned_config = ProvisionedClusterConfig(**config_data)
        
        # Apply smart defaults
        if not workgroup:
            workgroup = provisioned_config.cluster_identifier
            console.print(f"[dim]Using default workgroup name: {workgroup}[/dim]")
        
        if not namespace:
            namespace = workgroup  # Same as workgroup
            console.print(f"[dim]Using default namespace name: {namespace}[/dim]")
        
        console.print(f"[bold blue]Applying configuration to workgroup: {workgroup}[/bold blue]")
        
        # Validate mutually exclusive options
        if create_snapshot and snapshot_name:
            console.print("[red]✗ Error: --create-snapshot and --snapshot-name are mutually exclusive[/red]")
            console.print("  Use --create-snapshot to create a new snapshot automatically")
            console.print("  OR use --snapshot-name to restore from an existing snapshot")
            raise click.Abort()
        
        if dry_run:
            console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")
        
        # Create workgroup/namespace if requested
        if create_if_missing and not dry_run:
            console.print(f"\n[bold cyan]Checking if workgroup/namespace exist...[/bold cyan]")
            creator = WorkgroupCreator(region=region, dry_run=dry_run)
            
            # Create snapshot and restore
            if create_snapshot:
                console.print(f"[bold yellow]Creating new snapshot from cluster: {provisioned_config.cluster_identifier}[/bold yellow]")
                result = creator.create_snapshot_and_restore(
                    cluster_identifier=provisioned_config.cluster_identifier,
                    namespace_name=namespace,
                    workgroup_name=workgroup,
                    subnet_ids=provisioned_config.vpc_config.subnet_ids,
                    security_group_ids=provisioned_config.vpc_config.security_group_ids,
                    publicly_accessible=provisioned_config.vpc_config.publicly_accessible,
                    max_capacity=max_capacity,
                    iam_roles=[role.role_arn for role in provisioned_config.iam_roles],
                    tags=provisioned_config.tags,
                )
                console.print(f"[green]✓ {result['message']}[/green]")
            # Restore from existing snapshot
            elif snapshot_name:
                console.print(f"Restoring namespace from snapshot: {snapshot_name}")
                result = creator.create_from_snapshot(
                    namespace_name=namespace,
                    workgroup_name=workgroup,
                    snapshot_name=snapshot_name,
                    subnet_ids=provisioned_config.vpc_config.subnet_ids,
                    security_group_ids=provisioned_config.vpc_config.security_group_ids,
                    publicly_accessible=provisioned_config.vpc_config.publicly_accessible,
                    max_capacity=max_capacity,
                    iam_roles=[role.role_arn for role in provisioned_config.iam_roles],
                    tags=provisioned_config.tags,
                )
                console.print(f"[green]✓ {result['message']}[/green]")
            else:
                # Create namespace
                namespace_result = creator.ensure_namespace_exists(
                    namespace_name=namespace,
                    admin_username=admin_username,
                    admin_password=admin_password,
                    iam_roles=[role.role_arn for role in provisioned_config.iam_roles],
                    tags=provisioned_config.tags,
                )
                console.print(f"[green]✓ {namespace_result['message']}[/green]")
                
                # Create workgroup
                workgroup_result = creator.ensure_workgroup_exists(
                    workgroup_name=workgroup,
                    namespace_name=namespace,
                    subnet_ids=provisioned_config.vpc_config.subnet_ids,
                    security_group_ids=provisioned_config.vpc_config.security_group_ids,
                    publicly_accessible=provisioned_config.vpc_config.publicly_accessible,
                    max_capacity=max_capacity,
                    tags=provisioned_config.tags,
                )
                console.print(f"[green]✓ {workgroup_result['message']}[/green]")
        
        # Transform configuration
        mapper = ConfigMapper()
        serverless_config = mapper.transform(provisioned_config, workgroup, namespace)
        
        # Apply configuration
        applier = ServerlessWorkgroupApplier(region=region, dry_run=dry_run)
        result = applier.apply(serverless_config, provisioned_config.scheduled_queries)
        
        # Display results
        if dry_run:
            rprint(result)
        else:
            _display_apply_results(result)
            
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise click.Abort()


@main.command()
@click.option("--cluster-id", required=True, help="Provisioned cluster identifier")
@click.option("--workgroup", help="Serverless workgroup name (default: same as cluster-id)")
@click.option("--namespace", help="Serverless namespace name (default: same as cluster-id)")
@click.option("--create-if-missing", is_flag=True, help="Create workgroup/namespace if they don't exist")
@click.option("--create-snapshot", is_flag=True, help="Create a new snapshot from cluster before restoring (mutually exclusive with --snapshot-name)")
@click.option("--snapshot-name", help="Snapshot name to restore from (mutually exclusive with --create-snapshot)")
@click.option("--admin-username", default="admin", help="Admin username for new namespace")
@click.option("--admin-password", help="Admin password for new namespace")
@click.option("--max-capacity", type=int, default=512, help="Maximum capacity for workgroup (RPU, default: 512)")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--region", help="AWS region")
def migrate(
    cluster_id: str,
    workgroup: str,
    namespace: str,
    create_if_missing: bool,
    create_snapshot: bool,
    snapshot_name: str,
    admin_username: str,
    admin_password: str,
    max_capacity: int,
    dry_run: bool,
    region: str,
) -> None:
    """Full migration: extract and apply in one command."""
    
    # Apply smart defaults
    if not workgroup:
        workgroup = cluster_id
        console.print(f"[dim]Using default workgroup name: {workgroup}[/dim]")
    
    if not namespace:
        namespace = cluster_id  # Same as cluster-id
        console.print(f"[dim]Using default namespace name: {namespace}[/dim]")
    
    console.print("[bold blue]Starting full migration...[/bold blue]")
    
    # Validate mutually exclusive options
    if create_snapshot and snapshot_name:
        console.print("[red]✗ Error: --create-snapshot and --snapshot-name are mutually exclusive[/red]")
        console.print("  Use --create-snapshot to create a new snapshot automatically")
        console.print("  OR use --snapshot-name to restore from an existing snapshot")
        raise click.Abort()
    
    try:
        # Extract
        console.print(f"\n[1/4] Extracting from cluster: {cluster_id}")
        extractor = ProvisionedClusterExtractor(region=region)
        provisioned_config = extractor.extract(cluster_id)
        _display_config_summary(provisioned_config)
        
        # Create workgroup/namespace if requested
        if create_if_missing and not dry_run:
            console.print(f"\n[2/4] Creating workgroup/namespace")
            creator = WorkgroupCreator(region=region, dry_run=dry_run)
            
            # Create snapshot and restore
            if create_snapshot:
                console.print(f"[bold yellow]Creating new snapshot from cluster: {cluster_id}[/bold yellow]")
                result = creator.create_snapshot_and_restore(
                    cluster_identifier=cluster_id,
                    namespace_name=namespace,
                    workgroup_name=workgroup,
                    subnet_ids=provisioned_config.vpc_config.subnet_ids,
                    security_group_ids=provisioned_config.vpc_config.security_group_ids,
                    publicly_accessible=provisioned_config.vpc_config.publicly_accessible,
                    max_capacity=max_capacity,
                    iam_roles=[role.role_arn for role in provisioned_config.iam_roles],
                    tags=provisioned_config.tags,
                )
                console.print(f"[green]✓ {result['message']}[/green]")
                if result.get("snapshot"):
                    console.print(f"  Snapshot: {result['snapshot']['snapshot_identifier']}")
            # Restore from existing snapshot
            elif snapshot_name:
                console.print(f"Restoring namespace from snapshot: {snapshot_name}")
                result = creator.create_from_snapshot(
                    namespace_name=namespace,
                    workgroup_name=workgroup,
                    snapshot_name=snapshot_name,
                    subnet_ids=provisioned_config.vpc_config.subnet_ids,
                    security_group_ids=provisioned_config.vpc_config.security_group_ids,
                    publicly_accessible=provisioned_config.vpc_config.publicly_accessible,
                    max_capacity=max_capacity,
                    iam_roles=[role.role_arn for role in provisioned_config.iam_roles],
                    tags=provisioned_config.tags,
                )
                console.print(f"[green]✓ {result['message']}[/green]")
            else:
                # Create namespace
                namespace_result = creator.ensure_namespace_exists(
                    namespace_name=namespace,
                    admin_username=admin_username,
                    admin_password=admin_password,
                    iam_roles=[role.role_arn for role in provisioned_config.iam_roles],
                    tags=provisioned_config.tags,
                )
                console.print(f"[green]✓ {namespace_result['message']}[/green]")
                
                # Create workgroup
                workgroup_result = creator.ensure_workgroup_exists(
                    workgroup_name=workgroup,
                    namespace_name=namespace,
                    subnet_ids=provisioned_config.vpc_config.subnet_ids,
                    security_group_ids=provisioned_config.vpc_config.security_group_ids,
                    publicly_accessible=provisioned_config.vpc_config.publicly_accessible,
                    max_capacity=max_capacity,
                    tags=provisioned_config.tags,
                )
                console.print(f"[green]✓ {workgroup_result['message']}[/green]")
        else:
            console.print(f"\n[2/4] Skipping workgroup/namespace creation")
        
        # Transform
        console.print(f"\n[3/4] Transforming configuration")
        mapper = ConfigMapper()
        serverless_config = mapper.transform(provisioned_config, workgroup, namespace)
        
        # Apply
        console.print(f"\n[4/4] Applying to workgroup: {workgroup}")
        if dry_run:
            console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")
        
        # Apply configuration
        applier = ServerlessWorkgroupApplier(region=region, dry_run=dry_run)
        result = applier.apply(serverless_config, provisioned_config.scheduled_queries)
        
        # Display results
        if dry_run:
            rprint(result)
        else:
            _display_apply_results(result)
            
            # Check if there were any errors
            has_errors = any(
                details.get("status") == "error" 
                for details in result.values() 
                if isinstance(details, dict)
            )
            
            if has_errors:
                console.print("\n[yellow]⚠ Migration completed with some errors. Review the details above.[/yellow]")
            else:
                console.print("\n[bold green]✓ Migration completed successfully![/bold green]")
            
    except Exception as e:
        console.print(f"[red]✗ Migration failed: {e}[/red]")
        raise click.Abort()


def _display_config_summary(config) -> None:
    """Display a summary of extracted configuration."""
    table = Table(title="Extracted Configuration")
    table.add_column("Component", style="cyan")
    table.add_column("Details", style="white")
    
    table.add_row("Cluster ID", config.cluster_identifier)
    table.add_row("IAM Roles", str(len(config.iam_roles)))
    table.add_row("VPC ID", config.vpc_config.vpc_id)
    table.add_row("Subnets", str(len(config.vpc_config.subnet_ids)))
    table.add_row("Security Groups", str(len(config.vpc_config.security_group_ids)))
    table.add_row("Snapshot Schedules", str(len(config.snapshot_schedules)))
    table.add_row("Scheduled Queries", str(len(config.scheduled_queries)))
    
    # Parameter group info
    if config.parameter_group_info:
        param_count = len(config.parameter_group_info.parameters)
        table.add_row("Parameter Group", config.parameter_group_info.name)
        table.add_row("Mappable Parameters", str(param_count))
    
    table.add_row("Tags", str(len(config.tags)))
    
    console.print(table)
    
    # Show parameter details if available
    if config.parameter_group_info and config.parameter_group_info.parameters:
        console.print("\n[bold cyan]Parameter Group Details:[/bold cyan]")
        param_table = Table()
        param_table.add_column("Parameter", style="yellow")
        param_table.add_column("Value", style="white")
        
        for param_name, param_info in config.parameter_group_info.parameters.items():
            param_table.add_row(param_name, str(param_info.get("value", "")))
        
        console.print(param_table)
    
    # Show scheduled queries if available
    if config.scheduled_queries:
        console.print("\n[bold cyan]Scheduled Queries:[/bold cyan]")
        query_table = Table()
        query_table.add_column("Rule Name", style="yellow")
        query_table.add_column("Schedule", style="white")
        query_table.add_column("Database", style="white")
        query_table.add_column("Enabled", style="green")
        
        for query in config.scheduled_queries:
            query_table.add_row(
                query.rule_name,
                query.schedule_expression,
                query.database,
                "✓" if query.enabled else "✗",
            )
        
        console.print(query_table)


def _display_apply_results(result: dict) -> None:
    """Display results of applying configuration."""
    table = Table(title="Apply Results")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Details", style="dim")
    
    has_errors = False
    
    for component, details in result.items():
        status = details.get("status", "unknown")
        status_color = "green" if status == "success" else "red"
        
        # Get error details if present
        error_msg = ""
        if status == "error":
            has_errors = True
            error_msg = details.get("error", "Unknown error")
        elif status == "skipped":
            error_msg = details.get("reason", "")
        
        table.add_row(
            component, 
            f"[{status_color}]{status}[/{status_color}]",
            error_msg
        )
    
    console.print(table)
    
    # Show detailed error information if there were errors
    if has_errors:
        console.print("\n[yellow]⚠ Some operations encountered errors. Details above.[/yellow]")
    console.print(table)


if __name__ == "__main__":
    main()
