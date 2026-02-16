# Migrating WLM Queues to Redshift Serverless

Complete guide for handling multiple WLM (Workload Management) queues when migrating from Redshift Provisioned to Serverless.

## Overview

WLM queues in Redshift Provisioned clusters control query execution by allocating resources to different workloads. When migrating to Serverless, you have two options:

1. **Single Workgroup**: Migrate all queues to one serverless workgroup
2. **Multiple Workgroups**: Create one workgroup per WLM queue for workload isolation

## Quick Start

```bash
# Start the chat interface
./chat

# Check WLM queues
You: Get WLM queues for cluster my-cluster in us-east-2

# If multiple queues found, choose migration approach
You: Create multiple workgroups from WLM queues for cluster my-cluster
```

## Understanding WLM Queues

### What are WLM Queues?

WLM queues provide workload isolation in provisioned clusters:
- **Concurrency**: Number of queries that can run simultaneously
- **Memory**: Percentage of cluster memory allocated
- **Priority**: Query execution priority
- **Timeout**: Maximum query execution time
- **User/Query Groups**: Which users/queries use this queue

### Common Queue Configurations

**ETL Queue**
- High concurrency (10-15)
- High memory (40-50%)
- For batch processing

**Reporting Queue**
- Medium concurrency (5-10)
- Medium memory (30-40%)
- For business intelligence

**Ad-hoc Queue**
- Low concurrency (3-5)
- Low memory (20-30%)
- For exploratory queries

## Checking WLM Configuration

```bash
./chat
```

```
You: Get WLM queues for cluster prod-db-1 in us-east-2

Agent: Here's the WLM configuration for cluster 'prod-db-1':

{
  "cluster_id": "prod-db-1",
  "parameter_group": "custom-wlm-config",
  "wlm_queues_count": 3,
  "wlm_queues": [
    {
      "name": "etl",
      "concurrency": 15,
      "memory_percent": 50,
      "user_group": ["etl_users"],
      "query_group": ["etl"],
      "timeout": 7200
    },
    {
      "name": "reporting",
      "concurrency": 10,
      "memory_percent": 30,
      "user_group": ["bi_users"],
      "query_group": ["reporting"],
      "timeout": 3600
    },
    {
      "name": "adhoc",
      "concurrency": 5,
      "memory_percent": 20,
      "user_group": ["analysts"],
      "query_group": ["adhoc"],
      "timeout": 1800
    }
  ],
  "migration_options": {
    "single_workgroup": "Migrate all queues to one workgroup: prod-db-1",
    "multiple_workgroups": "Create 3 workgroups (one per queue): prod-db-1-etl, prod-db-1-reporting, prod-db-1-adhoc"
  }
}

You have 3 WLM queues. Would you like to:
1. Migrate to a single workgroup (simpler, lower cost)
2. Create multiple workgroups (workload isolation, independent scaling)
```

## Migration Options

### Option 1: Single Workgroup

**When to Use:**
- Workloads don't need strict isolation
- Simpler management preferred
- Cost optimization is priority
- Small to medium workloads

**Pros:**
- ✅ Simpler management (one workgroup)
- ✅ Lower cost (one set of RPUs)
- ✅ Easier monitoring
- ✅ Automatic resource sharing

**Cons:**
- ❌ No workload isolation
- ❌ One workload can impact others
- ❌ Single scaling configuration

**How to Migrate:**
```
You: Migrate cluster prod-db-1 to serverless with single workgroup
```

### Option 2: Multiple Workgroups

**When to Use:**
- Need workload isolation
- Different scaling requirements per workload
- Critical workloads need guaranteed resources
- Large enterprise workloads

**Pros:**
- ✅ Workload isolation maintained
- ✅ Independent scaling per workload
- ✅ Separate usage limits per workgroup
- ✅ Better cost attribution

**Cons:**
- ❌ More complex management
- ❌ Higher minimum cost (multiple workgroups)
- ❌ Need to route queries to correct workgroup

**How to Migrate:**
```
You: Create multiple workgroups from WLM queues for cluster prod-db-1
```

## Creating Multiple Workgroups

### Preview (Dry Run)

```
You: Create multiple workgroups from WLM queues for cluster prod-db-1 with dry-run

Agent: Planning workgroups based on WLM queues...

{
  "cluster_id": "prod-db-1",
  "namespace_name": "prod-db-1",
  "dry_run": true,
  "wlm_queues_count": 3,
  "workgroups_created": 3,
  "workgroups": [
    {
      "workgroup_name": "prod-db-1-etl",
      "namespace_name": "prod-db-1",
      "source_queue": "etl",
      "max_capacity": 384,
      "concurrency": 15,
      "status": "planned"
    },
    {
      "workgroup_name": "prod-db-1-reporting",
      "namespace_name": "prod-db-1",
      "source_queue": "reporting",
      "max_capacity": 256,
      "concurrency": 10,
      "status": "planned"
    },
    {
      "workgroup_name": "prod-db-1-adhoc",
      "namespace_name": "prod-db-1",
      "source_queue": "adhoc",
      "max_capacity": 128,
      "concurrency": 5,
      "status": "planned"
    }
  ],
  "message": "Planned 3 workgroups from WLM queues"
}

This will create 3 workgroups with capacity based on queue concurrency.
```

### Execute Migration

```
You: Create multiple workgroups from WLM queues for cluster prod-db-1

Agent: Creating workgroups...

✅ Created: prod-db-1-etl (384 RPUs max)
✅ Created: prod-db-1-reporting (256 RPUs max)
✅ Created: prod-db-1-adhoc (128 RPUs max)

All workgroups share namespace 'prod-db-1' (same data).
Each workgroup provides isolated compute resources.
```

## Workgroup Naming Convention

Workgroups are named using the pattern: `{cluster-id}-{queue-name}`

Examples:
- Cluster: `prod-db-1`, Queue: `etl` → Workgroup: `prod-db-1-etl`
- Cluster: `analytics`, Queue: `reporting` → Workgroup: `analytics-reporting`
- Cluster: `data-warehouse`, Queue: `adhoc` → Workgroup: `data-warehouse-adhoc`

## Workgroup Sizing

The agent automatically calculates max capacity based on queue concurrency:

```
Base Capacity: 128 RPUs
Concurrency Factor: queue_concurrency / 5 (normalized to default)
Max Capacity: base_capacity × concurrency_factor
Range: 128-512 RPUs
```

Examples:
- Concurrency 5 → 128 RPUs (baseline)
- Concurrency 10 → 256 RPUs (2x baseline)
- Concurrency 15 → 384 RPUs (3x baseline)
- Concurrency 20+ → 512 RPUs (capped)

## Routing Queries to Workgroups

After creating multiple workgroups, route queries appropriately:

### Method 1: Connection String

```python
# ETL workload
conn = redshift_connector.connect(
    host='prod-db-1-etl.123456.us-east-2.redshift-serverless.amazonaws.com',
    database='dev',
    user='etl_user'
)

# Reporting workload
conn = redshift_connector.connect(
    host='prod-db-1-reporting.123456.us-east-2.redshift-serverless.amazonaws.com',
    database='dev',
    user='bi_user'
)
```

### Method 2: Query Groups (if preserved)

```sql
-- Set query group
SET query_group TO 'etl';

-- Run query (routed to appropriate workgroup)
SELECT * FROM large_table;
```

### Method 3: Application Configuration

Update application configs to use correct workgroup endpoints:
- ETL jobs → `prod-db-1-etl` endpoint
- BI tools → `prod-db-1-reporting` endpoint
- Analysts → `prod-db-1-adhoc` endpoint

## Complete Migration Example

```
You: Get WLM queues for prod-db-1 in us-east-2

Agent: Found 3 WLM queues: etl, reporting, adhoc

You: I want to maintain workload isolation. Create multiple workgroups.

Agent: Creating multiple workgroups from WLM queues...

You: Create multiple workgroups from WLM queues for cluster prod-db-1 with dry-run

Agent: [Shows plan for 3 workgroups]

You: Looks good. Create them for real.

Agent: Creating workgroups...

✅ prod-db-1-etl (384 RPUs)
✅ prod-db-1-reporting (256 RPUs)
✅ prod-db-1-adhoc (128 RPUs)

All workgroups share namespace 'prod-db-1'.

Next steps:
1. Update application connection strings
2. Set usage limits per workgroup
3. Configure monitoring per workgroup
```

## Shared Namespace

All workgroups created from WLM queues share the same namespace:
- ✅ Same database
- ✅ Same tables and views
- ✅ Same users and permissions
- ✅ Same data (no duplication)
- 🔄 Separate compute resources
- 🔄 Independent scaling
- 🔄 Isolated workloads

## Cost Considerations

### Single Workgroup

```
Scenario: 128 RPUs average, 24/7 usage

Monthly cost: 128 RPUs × 24 hours × 30 days × $0.375/RPU-hour
            = $34,560/month
```

### Multiple Workgroups

```
Scenario: 3 workgroups, varying usage

ETL (384 RPUs, 8 hours/day):
  384 × 8 × 30 × $0.375 = $34,560/month

Reporting (256 RPUs, 12 hours/day):
  256 × 12 × 30 × $0.375 = $34,560/month

Ad-hoc (128 RPUs, 4 hours/day):
  128 × 4 × 30 × $0.375 = $5,760/month

Total: $74,880/month
```

**Key Insight**: Multiple workgroups cost more but provide:
- Workload isolation
- Independent scaling
- Better resource utilization
- Clearer cost attribution

## Best Practices

### 1. Analyze Queue Usage First

Before deciding, analyze actual queue usage:
```sql
-- Check query distribution across queues
SELECT 
    service_class,
    COUNT(*) as query_count,
    AVG(total_exec_time) as avg_exec_time
FROM stl_query
WHERE starttime > DATEADD(day, -7, GETDATE())
GROUP BY service_class;
```

### 2. Start with Single Workgroup

For initial migration:
1. Migrate to single workgroup
2. Monitor for 1-2 weeks
3. If workload contention occurs, split into multiple workgroups

### 3. Use Usage Limits

Set usage limits per workgroup:
```
You: Create usage limit for workgroup prod-db-1-etl with 200 RPU-hours per day
You: Create usage limit for workgroup prod-db-1-reporting with 150 RPU-hours per day
You: Create usage limit for workgroup prod-db-1-adhoc with 50 RPU-hours per day
```

### 4. Monitor Per Workgroup

Set up CloudWatch dashboards per workgroup:
- RPU usage
- Query count
- Query duration
- Usage limit breaches

### 5. Document Routing Logic

Create documentation for your team:
- Which workgroup for which workload
- Connection strings per workgroup
- Usage limits per workgroup
- Escalation procedures

## Troubleshooting

### No WLM Queues Found

**Problem:** "No custom WLM queues configured"

**Cause:** Cluster uses default queue only

**Solution:** Use single workgroup migration:
```
You: Migrate cluster my-cluster to serverless
```

### Workgroup Already Exists

**Problem:** "ConflictException: Workgroup already exists"

**Cause:** Workgroup with that name already created

**Solution:** Either:
1. Use existing workgroup
2. Delete and recreate
3. Choose different naming

### Query Routing Issues

**Problem:** Queries going to wrong workgroup

**Solution:**
1. Check connection strings
2. Verify query group settings
3. Update application configurations

## Comparison: Single vs Multiple Workgroups

| Aspect | Single Workgroup | Multiple Workgroups |
|--------|------------------|---------------------|
| Management | Simple | Complex |
| Cost | Lower | Higher |
| Isolation | None | Full |
| Scaling | Unified | Independent |
| Monitoring | Single dashboard | Per-workgroup dashboards |
| Usage Limits | One limit | Per-workgroup limits |
| Best For | Small/medium workloads | Enterprise workloads |

## Next Steps

After creating workgroups:

1. ✅ Update application connection strings
2. ✅ Set usage limits per workgroup
3. ✅ Configure monitoring per workgroup
4. ✅ Test query routing
5. ✅ Document workgroup assignments
6. ✅ Train team on new architecture

## Related Documentation

- [Migration Guide](CHAT_GUIDE.md)
- [Usage Limits](USAGE_LIMITS.md)
- [Maintenance & Snapshots](MAINTENANCE_AND_SNAPSHOTS.md)
- [AWS Redshift Serverless Workgroups](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-workgroup-namespace.html)

---

**Quick Commands:**

```bash
# Check WLM queues
./chat → "Get WLM queues for my-cluster"

# Preview multiple workgroups
./chat → "Create multiple workgroups from WLM queues for my-cluster with dry-run"

# Create multiple workgroups
./chat → "Create multiple workgroups from WLM queues for my-cluster"
```

**Maintain workload isolation with multiple workgroups!** 🎉
