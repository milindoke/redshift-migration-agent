# Product Overview

Redshift Modernization Agents is an AI-powered multi-agent system that helps customers migrate AWS Redshift Provisioned clusters to Serverless.

## What It Does

The system walks customers through a 4-phase modernization workflow:
1. **Assessment** — Analyzes cluster configuration, security, performance, and usage patterns
2. **Scoring** — Evaluates best practices across security (35%), performance (35%), and cost (30%), producing a 0–100 score with A–F grade
3. **Architecture Design** — Designs multi-warehouse topology with workload separation
4. **Execution Planning** — Creates a phased 12–18 week migration plan with validation gates

## Key Constraints

- Single-account deployment: all agents (orchestrator + subagents) run within the customer account.
- No service account or cross-account dependency.
- Customer data never leaves the customer account.
- Conversation isolation via namespace-based sessions keyed by `customer_account_id`.
- Default AWS region is `us-east-2`.
