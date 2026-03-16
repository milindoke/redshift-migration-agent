# Redshift Cluster Assessment Guide

## Overview

When assessing a Redshift Provisioned cluster for migration to Serverless, focus on three areas: cluster configuration, performance metrics, and WLM queue contention.

## Cluster Configuration Analysis

Key configuration attributes to evaluate:

- **Node type and count**: ra3 nodes indicate modern storage-compute separation. dc2 nodes use local SSD storage. Migration from dc2 to Serverless may show different I/O patterns.
- **Encryption**: If the cluster is encrypted with KMS, the Serverless namespace will also need encryption. Snapshots from encrypted clusters produce encrypted restores.
- **Enhanced VPC routing**: If enabled on Provisioned, network traffic stays within the VPC. Serverless workgroups should be configured in the same VPC for consistency.
- **Publicly accessible**: Serverless endpoints are not publicly accessible by default. Applications that connect via public endpoints will need VPC connectivity changes.
- **Multiple WLM queues**: Clusters with multiple WLM queues will surely benefit from multiple target serverless workgroups, one workgroup per WLM queue.
- **Single WLM queues**: Clusters with single WLM queue showing heavy utilization will benefit from producer-consumer architecture, a dedicated producer for ETL with data sharing to a separate dedicated consumer workgroup for queries.

## CloudWatch Metrics Interpretation

### CPU Utilization
- **< 30% average**: Cluster is over-provisioned. Serverless will auto-scale down and save costs.
- **30-70% average**: Healthy utilization. Serverless base RPU should match current capacity.
- **> 70% average**: Cluster is under pressure. Serverless max RPU should accommodate peaks.
- **Sustained > 90%**: Critical. Migration should include capacity increase.

### Database Connections
- **Steady pattern**: Predictable workload, good candidate for price-performance mode.
- **Spiky pattern**: Bursty workload, Serverless auto-scaling is ideal.
- **> 500 concurrent**: May need multiple workgroups to isolate connection pools.

### Disk Space Usage
- **> 80%**: Storage pressure. Serverless managed storage eliminates this concern.
- **Rapid growth**: Plan for data growth in cost estimates.

### Network Throughput
- High network throughput indicates data-intensive queries. Ensure Serverless workgroup is in the same AZ as data sources.

### Read/Write Latency
- High write latency suggests storage bottleneck — Serverless managed storage typically improves this.
- High read latency may indicate insufficient memory — RPU sizing should account for working set size.

## WLM Queue Contention Analysis

### Identifying Contention Problems

**Wait-to-Execution Ratio**:
- Ratio < 0.1: No contention. Queries execute immediately.
- Ratio 0.1 - 0.5: Mild contention. Some queuing during peaks.
- Ratio 0.5 - 1.0: Significant contention. Queries wait as long as they execute.
- Ratio > 1.0: Severe contention. Queries spend more time waiting than executing. Strong case for multi-workgroup split.

**Disk Spill**:
- Any disk spill indicates queries exceeding their memory allocation.
- Frequent spill in a queue means that queue's workload needs more memory — translate to higher RPU in Serverless.
- Spill > 1024MB per query: Consider dedicated workgroup with higher base RPU.

**Saturation Percentage**:
- < 50%: Queue has headroom. May not need its own workgroup.
- 50-80%: Queue is busy. Dedicated workgroup recommended.
- > 80%: Queue is saturated. Dedicated workgroup with higher RPU required.

### Queue-to-Workgroup Mapping Rules

1. **ETL/batch queues** (high write, high memory): Map to producer workgroup with higher base RPU.
2. **Analytics/BI queues** (read-heavy, many concurrent users): Map to consumer workgroup with price-performance mode.
3. **Short query queues** (low latency, high concurrency): Map to dedicated workgroup with lower base RPU but high max RPU for burst.
4. **Superuser/admin queues**: Usually don't need a dedicated workgroup — admin access works across all workgroups.

## Assessment Output Checklist

Before completing assessment, verify:
- [ ] All clusters in the region have been listed
- [ ] Target cluster configuration is fully captured
- [ ] CloudWatch metrics cover at least 24 hours (ideally 7 days)
- [ ] All WLM queues have been analyzed with per-queue metrics
- [ ] Contention narrative clearly explains why migration is beneficial
- [ ] Output matches the AssessmentResult JSON schema
