"""
Tools for Redshift cluster analysis and management.

These tools use boto3 to interact with AWS Redshift and CloudWatch services.
Public API is available via direct module imports:
  from tools.redshift_tools import analyze_redshift_cluster, ...
  from tools.cluster_lock import acquire_lock, release_lock
  from tools.audit_logger import emit_audit_event
"""
