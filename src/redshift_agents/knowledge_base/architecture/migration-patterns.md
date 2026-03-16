# Redshift Migration Patterns: Provisioned to Serverless

## Overview

Three architecture patterns for migrating from Redshift Provisioned to Serverless. Choose based on workload isolation needs, data sharing requirements, and organizational structure.

## Pattern 1: Hub-and-Spoke with Data Sharing

**Best for**: Organizations with shared datasets consumed by multiple teams.

### Architecture
- One **producer workgroup** handles ETL/write operations
- One or more **consumer workgroups** read data via Redshift data sharing
- Data is written once, read by many — no data duplication

### When to Choose
- Multiple teams or applications read the same data
- ETL and analytics workloads have different performance requirements
- Cost efficiency is important (no data duplication)
- WLM analysis shows distinct producer and consumer queue patterns

### Configuration
- `data_sharing.enabled = true`
- Producer workgroup: higher base RPU for write-heavy operations
- Consumer workgroups: price-performance mode for read-heavy analytics
- Create datashare on producer, grant usage to consumer namespaces

### Trade-offs
- Pros: Cost-efficient, single source of truth, independent scaling per workgroup
- Cons: Cross-workgroup query latency slightly higher than local, datashare setup complexity

## Pattern 2: Independent Warehouses

**Best for**: Strict isolation requirements or regulatory separation.

### Architecture
- Each workgroup is fully isolated with its own data copy
- No data sharing between workgroups
- Each workgroup has independent storage and compute

### When to Choose
- Regulatory or compliance requirements mandate data isolation
- Different teams need completely independent environments
- Workloads have no shared data dependencies
- Different SLAs require independent failure domains

### Configuration
- `data_sharing.enabled = false`
- Each workgroup gets its own snapshot restore
- Independent RPU sizing per workgroup

### Trade-offs
- Pros: Complete isolation, independent failure domains, simplest to reason about
- Cons: Data duplication increases storage costs, ETL must run in each workgroup

## Pattern 3: Hybrid

**Best for**: Complex organizations with mixed requirements.

### Architecture
- Some workgroups share data (hub-and-spoke subset)
- Other workgroups are fully independent
- Flexible combination based on team needs

### When to Choose
- Some teams share data while others need isolation
- Mix of regulated and non-regulated workloads
- Phased migration where some workloads move first

### Configuration
- Mix of `data_sharing.enabled = true` and `false` across workgroups
- Producer workgroup shares with some consumers, not all
- Independent workgroups get their own data copies

### Trade-offs
- Pros: Maximum flexibility, can accommodate diverse requirements
- Cons: Most complex to set up and manage, harder to estimate costs

## 1:1 Migration (Single Workgroup)

**Best for**: Purpose-built clusters with a single workload type.

### When to Choose
- Cluster serves a single application or team
- WLM has only one queue (or all queues serve the same workload)
- No contention problems — migration is for cost optimization or managed infrastructure
- Simple migration with minimal risk

### Configuration
- Single namespace, single workgroup
- `data_sharing.enabled = false`
- `workload_type = "mixed"`
- Price-performance mode at 50 (balanced)

### Trade-offs
- Pros: Simplest migration, lowest risk, fastest to complete
- Cons: No workload isolation, no independent scaling per workload type

## Decision Matrix

| Factor | Hub-and-Spoke | Independent | Hybrid | 1:1 |
|---|---|---|---|---|
| WLM queues > 1 with shared data | ✅ Best | ❌ | ✅ Good | ❌ |
| WLM queues > 1 with isolated data | ❌ | ✅ Best | ✅ Good | ❌ |
| Single WLM queue | ❌ | ❌ | ❌ | ✅ Best |
| Regulatory isolation needed | ❌ | ✅ Best | ✅ Good | ❌ |
| Cost optimization priority | ✅ Best | ❌ | ✅ Good | ✅ Good |
| Migration complexity | Medium | Medium | High | Low |
