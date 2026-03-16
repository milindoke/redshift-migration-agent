# RPU Sizing Guide for Redshift Serverless

## Overview

Redshift Processing Units (RPUs) determine the compute capacity of a Serverless workgroup. Proper sizing ensures good performance without overspending.

## Minimum RPU: 32

All workgroups must have a minimum of 32 RPU. This is required for AI-driven scaling and price-performance features. Never recommend less than 32 RPU.

## Scaling Modes

### Price-Performance Mode (Recommended)

Price-performance mode lets Redshift automatically manage compute capacity based on workload demands and a cost-performance balance target.

- **Target 1**: Minimum cost. Redshift aggressively minimizes compute, longer query times expected.
- **Target 25**: Cost-optimized. Redshift considers compute reduction, accepts longer query times.
- **Target 50**: Balanced (RECOMMENDED DEFAULT). Good trade-off between cost and performance.
- **Target 75**: Performance-optimized. Redshift allocates more compute for faster queries.
- **Target 100**: Maximum performance. Highest compute allocation, highest cost.

When to use price-performance mode:
- Most workloads — it's the simplest and most cost-effective option
- Variable or unpredictable workloads
- When you don't have strong opinions about specific RPU values
- New migrations where optimal RPU is unknown

### Base RPU Mode

Base RPU mode sets a fixed minimum compute capacity with optional burst via max RPU.

- `base_rpu`: Minimum always-available compute (minimum 8, recommended 32)
- `max_rpu`: Maximum burst capacity (must be > base_rpu)

**CRITICAL**: When using base RPU mode, always set `max_rpu` greater than `base_rpu`. Setting `max_rpu` equal to `base_rpu` disables bursting and causes performance degradation under load. Also always use `extra-compute-for-automatic-optimization` option with base RPU mode.

When to use base RPU mode:
- Predictable, steady-state workloads with known resource requirements
- When you need guaranteed minimum capacity for SLA compliance
- Cost-sensitive environments where you want to cap maximum spend

## Sizing from Provisioned Cluster Metrics

### Node Type to RPU Mapping (Starting Points)

| Provisioned Node Type | Nodes | Suggested Base RPU | Suggested Max RPU |
|---|---|---|---|
| dc2.large | 2-8 | 32-64 | 128 |
| dc2.large | 9+ | 64-128 | 256 |
| dc2.8xlarge | 2-8 | 128-256 | 512 |
| dc2.8xlarge | 5+ | 256-512 | 1024 |
| ra3.xlplus | 2-8 | 32-64 | 128 |
| ra3.xlplus | 9+ | 64-128 | 512 |
| ra3.4xlarge | 2-8 | 128-256 | 512 |
| ra3.4xlarge | 9+ | 256-512 | 1024 |
| ra3.16xlarge | 2-4 | 256-512 | 1024 |
| ra3.16xlarge | 5+ | 512+ | 1024+ |

These are starting points. Actual RPU needs depend on query complexity, concurrency, and data volume.

### Adjusting Based on WLM Metrics

- **High CPU utilization (>70%)**: Increase base RPU by 25%
- **Frequent disk spill**: Increase base RPU — spill indicates insufficient memory
- **High concurrency (>50 concurrent queries)**: Increase max RPU by 100% 
- **Long wait times**: Consider splitting into multiple workgroups rather than increasing RPU

### Adjusting Based on Query Patterns

- **ETL/batch workloads**: Higher base RPU (memory-intensive transforms)
- **BI/dashboard queries**: Lower base RPU, higher max RPU (bursty pattern)
- **Ad-hoc analytics**: Price-performance mode at 50 (unpredictable)
- **Real-time/streaming**: Higher base RPU for consistent low latency

## Cost Estimation

RPU pricing is per RPU-hour. Estimate monthly costs:

- **Minimum cost**: base_rpu * hours_per_month * price_per_rpu_hour
- **Maximum cost**: max_rpu * hours_per_month * price_per_rpu_hour
- **Typical cost**: Usually 40-60% of maximum, depending on workload variability

For price-performance mode, costs are automatically optimized based on the target setting.

## Multi-Workgroup Considerations

When splitting into multiple workgroups:
- Each workgroup has independent RPU settings
- Total cost is the sum of all workgroups
- Workgroups can have different scaling modes (one on price-performance, another on base RPU)
- Data sharing between workgroups does not consume additional RPU on the producer
