# Amazon Redshift Sizing Guide

## Deployment Modes

Amazon Redshift offers two deployment modes:
- **Cluster (Provisioned)** — MPP machine with multiple nodes. You choose node type and node count.
- **Workgroup (Serverless)** — You specify RPU (Redshift Processing Units). Each RPU = 16 GB memory.

### Provisioned Node Types (RA3 family, smallest to largest)
- `ra3.large`
- `ra3.xlplus` (32 GB memory per node)
- `ra3.4xlarge` (3x resources vs xlplus)
- `ra3.16xlarge` (4x resources vs 4xlarge)

---

## Serverless RPU Sizing

### Why RPU selection matters
- Too low → queries spill to disk → 5–10x slower
- Higher RPU = faster queries, often at the same cost

Example: a 60-min query at 32 RPU = a 15-min query at 128 RPU, both cost $11.52 at $0.36/RPU-Hr.

### AI-Driven Scaling (price-performance targets)
Available since 2023. Instead of picking an RPU number, set a price-performance target:
- `50/Balanced` — recommended default
- `75/Performance` — for slower-than-expected queries
- `100/Performance` — maximum performance focus
- `25/Cost` — cost focus
- `1/Cost` — maximum cost focus

Redshift automatically provisions secondary compute for heavy queries without impacting regular workloads.

---

## Sizing Scenarios

### New project (exploratory phase)
Start with **Base 8 RPU** (128 GB). Scale up to 16 or 24 RPU if queries are too slow.

### Project maturing / production
Move to **Base 32 RPU** (512 GB), then after 30+ minutes enable AI-driven scaling at `50/Balanced`.

> AI-driven scaling requires Base RPU between 32 and 512.

### Skip straight to AI-driven scaling
Start directly with AI-driven scaling at `50/Balanced`. Adjust:
- Too slow → increase to `75` or `100`
- Too expensive → decrease to `25`

### Switching existing workgroup from Base RPU to price-performance
| Current Base RPU | Recommended starting target |
|---|---|
| 128 RPU or higher | 50/Balanced |
| Less than 128 RPU | 75/Performance |
| 64–32 RPU | 100/Performance |

---

## Data Scan Capacity Reference

| Base RPU | Memory | Approx. data scan capacity |
|---|---|---|
| 32 RPU | 512 GB | ~100 GB |
| 64 RPU | 1 TB | ~250 GB |
| 128 RPU | 2 TB | ~500 GB |

Use `SYS_QUERY_*` tables (Superuser required) to check actual data scanned by queries.

---

## Serverless vs. Provisioned Cost Comparison

Monthly cost for 128 GB memory, 24x7, US East (Ohio):

| Type | Billing | Monthly Cost |
|---|---|---|
| 8 RPU Serverless | On-demand | $2,108.16 |
| ra3.xlplus 4-node Cluster | On-demand | $3,171.12 (+50%) |
| ra3.xlplus 4-node Cluster | 1-Yr No Upfront RI | $2,219.78 (+5%) |
| ra3.xlplus 4-node Cluster | 3-Yr No Upfront RI | $1,379.70 (-35%) |

**Serverless Reservations** (launched Apr 2025): commit to RPUs for 1-year or 3-year term examples
- 1-year No-upfront: 20% discount off on-demand
- 1-year All-upfront: 24% discount
- 3-year No-upfront: 45% discount off on-demand

---

## When to Use Provisioned Clusters

Best fit for very repeatable, static workloads running 24x7 with little variability (e.g., continuous IoT streaming + ETL). Pair with 3-year RIs for maximum savings.

---

## Multi-Workgroup Strategy

- Each new project → new Workgroup (don't resize existing cluster)
- Share data across workgroups via **Redshift Data Sharing**
  - Read: create a data share from source cluster, consume from new workgroup
  - Write: use multi-data warehouse writes through data sharing
- Protect costs with **Query Monitoring Rules** and **Max RPU** limits
- Manage multiple workgroups centrally via **AWS IAM Identity Center** (SSO, shared across clusters/workgroups, CloudTrail auditing)

---

## Key Rules of Thumb

1. Default to Serverless with AI-driven scaling at `50/Balanced` for any new project.
2. Minimum Base RPU for AI-driven scaling: **32 RPU**.
3. Higher RPU = faster queries, often at the same or lower total cost.
4. Serverless costs scale with utilization — idle time costs nothing.
5. Provisioned 3-yr RI is only cheaper if utilization is consistently 24x7.
6. Never resize an existing cluster for a new project — provision a new workgroup instead.
