# Atlas AI — Architecture Design Document

**Version:** 1.0.0  
**Status:** Living Document  
**Last Updated:** 2025-01-01  
**Authors:** Atlas AI Platform Team  
**Classification:** Internal Engineering

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [Component Architecture](#4-component-architecture)
5. [Multi-Agent System Design](#5-multi-agent-system-design)
6. [MCP Server Architecture](#6-mcp-server-architecture)
7. [Data Architecture](#7-data-architecture)
8. [API Design Overview](#8-api-design-overview)
9. [Security Architecture](#9-security-architecture)
10. [Observability](#10-observability)
11. [Learning Loop Design](#11-learning-loop-design)
12. [Scalability and Performance SLOs](#12-scalability-and-performance-slos)
13. [Deployment Architecture](#13-deployment-architecture)

---

## 1. Executive Summary

Atlas AI is an autonomous enterprise engineer built to resolve production incidents without human intervention. It operates as a multi-agent system that continuously monitors infrastructure signals, orchestrates specialized AI agents, produces root-cause analyses (RCAs), and—where human approval is granted—executes remediation actions against live production environments.

The system is designed around three core principles:

1. **Safety first.** No agent may mutate production state without explicit human approval. All Kubernetes, cloud, and database operations are gated behind approval workflows with full audit trails.
2. **Explainability.** Every decision the system makes is traced back to specific log lines, metrics, and tool outputs. A human engineer can audit the entire reasoning chain end-to-end.
3. **Continuous improvement.** Resolved incidents feed a vector-based learning store. Future investigations retrieve semantically similar past incidents as few-shot context, improving RCA accuracy over time without retraining.

Atlas AI targets a **Mean Time to Diagnose (MTTD) of under 8 minutes** for P1 incidents and a **false-positive rate below 2%** on automated remediation proposals. Engineering teams that have piloted the system report a 70–80% reduction in on-call page burden for known failure modes.

---

## 2. Problem Statement

### 2.1 The On-Call Crisis

Modern distributed systems generate alert volumes that far exceed human cognitive capacity. A typical platform team at a 500-engineer company receives between 800 and 3,000 alerts per day. Signal-to-noise ratio is poor: fewer than 5% of pages require immediate human action. The rest are either false positives, known-pattern incidents solvable by documented runbooks, or cascading secondary alerts from a single root cause.

The consequences are severe:

- **Alert fatigue.** Engineers silence notifications, raising MTTR for genuine incidents.
- **Toil accumulation.** Tier-1 on-call work (restarts, scaling, log triage) consumes 35–50% of SRE time that could be spent on reliability engineering.
- **Knowledge silos.** Runbook knowledge is locked in individual engineers' heads. When the author of a runbook leaves, the institutional memory goes with them.
- **3 AM degradation.** Human cognition is measurably impaired at 3 AM. Incident resolution quality at night-time is demonstrably worse than during business hours.

### 2.2 Existing Solutions Are Insufficient

| Approach | Gap |
|---|---|
| Static runbooks | Cannot adapt to novel failure modes; become stale immediately |
| PagerDuty / OpsGenie | Alert routing only; no investigation or remediation |
| AIOps platforms (Dynatrace, New Relic AI) | Anomaly detection only; do not produce actionable RCAs or take action |
| Custom automation scripts | Brittle; require constant maintenance; no reasoning capability |
| LLM copilots (Copilot, Cursor) | Require a human in the loop; cannot operate autonomously at 3 AM |

### 2.3 The Gap Atlas AI Fills

Atlas AI fills the space between detection and resolution. It can be thought of as a tireless, senior SRE that never sleeps, has perfect recall of every past incident, reads every log line in real time, and can reason across the full stack—from kernel metrics to application traces to cost anomalies—simultaneously.

---

## 3. Solution Overview

### 3.1 High-Level Description

When an incident is detected (via PagerDuty webhook, Prometheus alert, or manual trigger), Atlas AI:

1. Creates an incident record and assigns a severity.
2. Launches a **Planning Agent** that decomposes the incident into an investigation plan.
3. Dispatches **specialist agents** in parallel or sequence (per plan) to gather evidence.
4. Synthesizes findings into a structured RCA with confidence scores.
5. Proposes a remediation plan and routes it for human approval.
6. On approval, executes remediation steps with rollback capability.
7. Stores the resolved case in the learning store for future retrieval.

### 3.2 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SIGNAL SOURCES                            │
│                                                                             │
│   PagerDuty        Prometheus        GitHub        CloudWatch / GCP         │
│   Webhooks         AlertManager      Actions        Pub/Sub                 │
└────────┬───────────────┬──────────────┬──────────────┬───────────────────────┘
         │               │              │              │
         ▼               ▼              ▼              ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        ATLAS AI API GATEWAY                                │
│                                                                            │
│   FastAPI / Uvicorn        JWT Auth        Rate Limiting        WebSocket  │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
          ┌──────────────────┐         ┌──────────────────────┐
          │   INCIDENT BUS   │         │   REST / WebSocket   │
          │  (Redis Streams) │         │   Human Dashboard    │
          └────────┬─────────┘         └──────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                              │
│                                                                          │
│   ┌───────────────────────────────────────────────────────────────────┐ │
│   │                    PLANNING AGENT (LLM)                           │ │
│   │  Decomposes incident → investigation plan → agent dispatch order  │ │
│   └──────┬────────┬──────────┬────────┬────────┬────────┬────────────┘ │
│          │        │          │        │        │        │              │
│          ▼        ▼          ▼        ▼        ▼        ▼              │
│  ┌──────────┐ ┌──────┐ ┌──────────┐ ┌──────┐ ┌──────┐ ┌────────────┐ │
│  │  K8s     │ │GitHub│ │ Storage  │ │ Net  │ │ Sec  │ │   Cost     │ │
│  │  Agent   │ │Agent │ │  Agent   │ │Agent │ │Agent │ │   Agent    │ │
│  └────┬─────┘ └──┬───┘ └────┬─────┘ └──┬───┘ └──┬───┘ └─────┬──────┘ │
│       │          │          │           │        │            │        │
│       └──────────┴──────────┴───────────┴────────┴────────────┘        │
│                                   │                                     │
│                                   ▼                                     │
│                   ┌───────────────────────────────┐                    │
│                   │    RCA SYNTHESIS AGENT (LLM)   │                    │
│                   │  Correlates findings → RCA      │                    │
│                   └───────────────┬───────────────┘                    │
│                                   │                                     │
│                                   ▼                                     │
│                   ┌───────────────────────────────┐                    │
│                   │   DOCUMENTATION AGENT (LLM)    │                    │
│                   │  Formats RCA → Confluence/Jira  │                    │
│                   └───────────────┬───────────────┘                    │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │
                    ┌───────────────┴──────────────┐
                    │                              │
                    ▼                              ▼
     ┌──────────────────────┐       ┌─────────────────────────┐
     │   HUMAN APPROVAL     │       │     LEARNING STORE       │
     │   GATE (Slack/Web)   │       │  pgvector + PostgreSQL   │
     └──────────┬───────────┘       └─────────────────────────┘
                │ APPROVED
                ▼
     ┌──────────────────────┐
     │  REMEDIATION RUNNER  │
     │  (Controlled Actions)│
     └──────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         MCP SERVER CLUSTER                               │
│                                                                          │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐ │
│  │ K8s MCP    │  │ GitHub MCP │  │ Storage MCP │  │  Metrics MCP     │ │
│  │ (read-only)│  │            │  │             │  │  (Prometheus/    │ │
│  │ + approved │  │            │  │             │  │   CloudWatch)    │ │
│  │ mutations  │  │            │  │             │  │                  │ │
│  └────────────┘  └────────────┘  └─────────────┘  └──────────────────┘ │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐                       │
│  │ Network MCP│  │ Security   │  │ Cost MCP    │                       │
│  │            │  │ MCP        │  │ (AWS/GCP)   │                       │
│  └────────────┘  └────────────┘  └─────────────┘                       │
└──────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION INFRASTRUCTURE                        │
│                                                                          │
│   Kubernetes Clusters   │   Databases   │   CDN / Load Balancers        │
│   AWS / GCP / Azure     │   S3 / GCS    │   GitHub Repositories         │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Core Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Agent framework | LangGraph + LangChain | Stateful graph execution; native tool calling; rich ecosystem |
| LLM backend | Claude 3.5 Sonnet (primary), GPT-4o (fallback) | Sonnet leads on long-context tool use; GPT-4o for fallback diversity |
| Tool protocol | MCP (Model Context Protocol) | Standard protocol; enables tool servers outside the agent process |
| Message bus | Redis Streams | Low-latency; consumer groups; replay capability for audit |
| Primary store | PostgreSQL 16 + pgvector | Relational integrity + vector similarity in one engine |
| Cache/session | Redis | Agent working memory; rate-limit counters |
| Tracing | OpenTelemetry → Jaeger | Vendor-neutral; traces every LLM call and tool invocation |

---

## 4. Component Architecture

### 4.1 API Gateway

The API Gateway is a FastAPI application running on Uvicorn with Gunicorn process management. It provides:

- **REST API** for incident CRUD, agent status queries, RCA retrieval, and remediation approval.
- **WebSocket endpoints** for real-time progress streaming to the dashboard.
- **Webhook receivers** for PagerDuty, Prometheus AlertManager, and GitHub Actions.
- **JWT authentication** with RS256 signing. Tokens carry roles: `viewer`, `engineer`, `approver`, `admin`.
- **Rate limiting** via Redis sliding window counters: 1,000 RPM per API key by default.

The gateway does not contain business logic. It validates requests, authenticates callers, and emits events to the Incident Bus.

### 4.2 Incident Bus

The Incident Bus is implemented on Redis Streams with three primary streams:

| Stream | Purpose |
|---|---|
| `atlas:incidents` | New incident creation events |
| `atlas:agent_events` | Agent start/progress/completion events |
| `atlas:approvals` | Human approval/rejection decisions |

Consumer groups are created per service so that the Orchestration Layer, the WebSocket broadcaster, and the Audit Logger all independently consume the full event stream.

### 4.3 Orchestration Layer

The Orchestration Layer is the brain of Atlas AI. It is built on **LangGraph**, a directed cyclic graph execution framework from LangChain. Each agent execution is a node in the graph. Edges are either unconditional (always execute next agent) or conditional (execute only if the prior agent found evidence).

The Orchestration Layer maintains a **shared investigation context** object that flows through the graph. Each agent appends its findings to this context before handing off. The final synthesis agents see the full accumulated evidence.

### 4.4 Human Dashboard

A React + TypeScript single-page application that connects via WebSocket to stream real-time agent progress. It presents:

- Live feed of tool calls being made by each agent.
- Structured RCA display with confidence scores and supporting evidence.
- One-click approve/reject UI for remediation proposals.
- Historical incident browsing with search and filtering.

### 4.5 Remediation Runner

An isolated execution environment that runs only after human approval. It has time-boxed execution (configurable per action type, default 5 minutes), automatic rollback on error, and writes every action to the audit log before and after execution. It communicates with production systems exclusively through the MCP Server cluster.

---

## 5. Multi-Agent System Design

### 5.1 Agent Taxonomy

Atlas AI uses nine specialized agents organized into three tiers:

```
Tier 1 — Orchestration
  └── Planning Agent

Tier 2 — Investigation (run in parallel)
  ├── Kubernetes Agent
  ├── GitHub Agent
  ├── Storage Agent
  ├── Network Agent
  └── Security Agent

Tier 3 — Synthesis and Communication
  ├── RCA Agent
  ├── Documentation Agent
  └── Cost Agent
```

### 5.2 Planning Agent

**Role:** Receives a raw incident description and produces a structured investigation plan.

**Inputs:** Incident title, severity, alerting metric, affected service, metadata.  
**Outputs:** Ordered list of agents to invoke, hypothesis list, relevant time window.

The Planning Agent uses chain-of-thought reasoning to produce a JSON investigation plan. It queries the vector learning store to retrieve the 3–5 most similar past incidents and includes their summaries as few-shot examples in its context.

**Key tools:**
- `search_similar_incidents(query, k)` — vector similarity search over resolved incidents
- `get_service_metadata(service_name)` — retrieves service owner, SLO thresholds, dependency graph
- `get_runbook(service_name)` — retrieves existing runbook if one exists

### 5.3 Kubernetes Agent

**Role:** Deep-dives into the Kubernetes control plane and workloads for the affected service.

**Inputs:** Service name, namespace, time window.  
**Outputs:** Pod health report, resource utilization, recent events, relevant log excerpts, OOMKill/CrashLoopBackOff evidence.

Operates exclusively through the K8s MCP server which enforces read-only access. All `kubectl` commands are executed server-side with `--dry-run=client` flag simulation before real execution, and only `get`, `describe`, `logs`, and `top` verbs are permitted.

**Key tools:**
- `k8s_get_pod_status(namespace, selector)` — lists pods with status, restarts, age
- `k8s_get_pod_logs(namespace, pod_name, since, container)` — fetches log lines
- `k8s_describe_deployment(namespace, name)` — full deployment spec and events
- `k8s_get_node_metrics(node_name)` — CPU, memory, disk pressure
- `k8s_get_events(namespace, since)` — cluster events filtered by time

### 5.4 GitHub Agent

**Role:** Correlates the incident timeline with code changes, deployments, and CI/CD activity.

**Inputs:** Service name, time window (typically ±2 hours around incident start).  
**Outputs:** List of recent commits with diff summaries, open PRs, failed checks, deployment records.

**Key tools:**
- `github_list_recent_commits(repo, since, until)` — lists commits with author, message, diff stats
- `github_get_deployment_history(repo, environment, since)` — deployment events from GitHub Environments
- `github_get_failed_checks(repo, sha)` — CI/CD check failures for a specific commit
- `github_get_pr_diff(repo, pr_number)` — full diff for a merged PR

### 5.5 Storage Agent

**Role:** Investigates database and object storage health — slow queries, connection pool exhaustion, disk utilization, replication lag.

**Inputs:** Service name, database identifiers from service metadata.  
**Outputs:** Slow query report, connection pool status, replication lag, disk utilization trend, index health.

**Key tools:**
- `db_get_slow_queries(db_id, since, threshold_ms)` — queries from pg_stat_statements or equivalent
- `db_get_connection_pool_stats(db_id)` — active, idle, waiting connections
- `db_get_replication_lag(db_id)` — replication lag in bytes and seconds
- `s3_get_bucket_metrics(bucket, since)` — request rates, error rates, latency percentiles
- `db_explain_query(db_id, query_text)` — EXPLAIN ANALYZE output for a specific query

### 5.6 Network Agent

**Role:** Examines network topology, DNS resolution, load balancer health, and inter-service connectivity.

**Inputs:** Service name, downstream dependencies.  
**Outputs:** DNS resolution health, load balancer error rates, CDN hit/miss ratios, inter-service timeout rates.

**Key tools:**
- `network_get_lb_metrics(lb_id, since)` — request count, 5xx rate, latency p50/p95/p99
- `network_check_dns(hostname)` — current DNS resolution result
- `network_get_service_mesh_stats(service, since)` — Istio/Linkerd traffic metrics
- `network_get_cdn_stats(domain, since)` — CDN cache hit rate, origin error rate
- `network_check_connectivity(source_service, target_service)` — tests reachability

### 5.7 Security Agent

**Role:** Scans for anomalous access patterns, IAM changes, secret rotation events, and potential intrusion indicators.

**Inputs:** Service name, time window.  
**Outputs:** IAM change events, unusual access patterns, secret rotation timeline, CVE scan results if relevant.

**Key tools:**
- `security_get_cloudtrail_events(service_role, since)` — IAM and API activity
- `security_scan_access_logs(service, since)` — anomalous IPs or request patterns
- `security_get_secret_rotation_events(secret_id, since)` — rotation history
- `security_check_pod_security(namespace, pod_name)` — pod security context violations
- `security_get_waf_events(since)` — WAF block/allow events

### 5.8 RCA Agent

**Role:** Synthesizes all agent findings into a single root-cause analysis with causal chain, confidence score, and remediation proposals.

**Inputs:** Full investigation context from all prior agents.  
**Outputs:** Structured RCA with root cause, contributing factors, timeline, confidence score (0–100), and ordered remediation actions.

The RCA Agent is the most LLM-intensive component. It uses a structured output format enforced via Pydantic model validation. Each remediation action carries a risk level (`low`, `medium`, `high`) and a rollback procedure.

### 5.9 Documentation Agent

**Role:** Converts the structured RCA into human-readable documents published to Confluence and Jira.

**Inputs:** Structured RCA object.  
**Outputs:** Confluence page URL, Jira incident ticket update, Slack summary message.

**Key tools:**
- `confluence_create_page(space_key, title, body)` — creates incident report page
- `jira_update_incident_ticket(ticket_id, rca_summary, resolution)` — updates existing ticket
- `slack_post_message(channel, message)` — posts summary to incident channel

### 5.10 Cost Agent

**Role:** Quantifies the financial impact of the incident and identifies cost-anomaly signals that may be causally related.

**Inputs:** Service name, time window, infrastructure identifiers.  
**Outputs:** Estimated cost impact ($), cost anomaly events preceding the incident, optimization recommendations.

**Key tools:**
- `cost_get_service_spend(service, since)` — per-service cloud spend
- `cost_get_anomaly_events(account_id, since)` — AWS Cost Anomaly Detection / GCP budget alerts
- `cost_estimate_incident_impact(incident_id)` — calculates cost of downtime × SLA value

---

## 6. MCP Server Architecture

### 6.1 Overview

Atlas AI uses the Model Context Protocol (MCP) to expose production tools to agents as a standardized interface. Each MCP server is a standalone process that implements the MCP JSON-RPC specification. Agents communicate with MCP servers over Unix domain sockets (same host) or mTLS-secured TCP (cross-host).

### 6.2 MCP Server Inventory

| Server | Port | Transport | Auth | Mutation Allowed |
|---|---|---|---|---|
| `mcp-kubernetes` | 9001 | Unix socket | Pod SA token | Read-only by default; mutations require approval token |
| `mcp-github` | 9002 | TCP + mTLS | GitHub App JWT | Read + write to non-production branches |
| `mcp-storage` | 9003 | TCP + mTLS | DB credentials (Vault) | Read-only |
| `mcp-network` | 9004 | TCP + mTLS | Cloud IAM role | Read-only |
| `mcp-security` | 9005 | TCP + mTLS | Cloud IAM role (security-read) | Read-only |
| `mcp-metrics` | 9006 | Unix socket | Internal only | Read-only |
| `mcp-cost` | 9007 | TCP + mTLS | Cloud IAM role | Read-only |
| `mcp-docs` | 9008 | TCP + mTLS | OAuth2 service account | Write to Confluence/Jira/Slack |

### 6.3 MCP Security Model

Every MCP server implements a two-tier permission model:

**Tier 1 — Investigation permissions (always granted):** `get`, `list`, `describe`, `logs`, `metrics`, `search`  
**Tier 2 — Mutation permissions (require approval token):** `patch`, `scale`, `restart`, `delete`, `apply`

An approval token is a signed JWT issued by the Atlas AI authorization service. It contains: the incident ID, the specific mutation action, the target resource, the approving user's identity, and a 30-minute expiry. The MCP server validates this token before executing any mutation.

### 6.4 Tool Versioning

Every tool exposed by an MCP server carries a semantic version. The orchestration layer maintains a compatibility matrix. If an MCP server upgrades a tool in a breaking way, agents continue to use the prior version until explicitly migrated.

---

## 7. Data Architecture

### 7.1 Primary Database — PostgreSQL 16

PostgreSQL is the system of record for all Atlas AI state. The pgvector extension enables semantic similarity search over incident embeddings.

#### Core Tables

| Table | Purpose |
|---|---|
| `incidents` | Incident records with status, severity, metadata |
| `agent_runs` | Individual agent execution records with tool call logs |
| `rca_reports` | Structured RCA documents with JSON findings |
| `learning_cases` | Resolved incidents stored with vector embeddings for retrieval |
| `notifications` | Alert routing and delivery records |
| `audit_log` | Immutable append-only log of all mutations |

#### JSONB Usage

Tool call logs, agent findings, and remediation proposals are stored as JSONB. GIN indexes are created on key paths that are queried frequently (e.g., `findings->'root_cause'`, `metadata->'service_name'`). This provides relational integrity for core fields while preserving flexibility for heterogeneous agent outputs.

#### Vector Store

The `learning_cases` table contains a `embedding` column of type `vector(1536)` (OpenAI text-embedding-3-small dimensions). An IVFFlat index is built on this column for approximate nearest-neighbor search at low latency. Embeddings are generated from a concatenation of incident title, service name, symptom descriptions, and confirmed root cause.

### 7.2 Cache and Session Store — Redis 7

Redis serves three distinct purposes:

| Key Pattern | TTL | Purpose |
|---|---|---|
| `session:{agent_run_id}` | 2 hours | Agent working memory (intermediate tool results) |
| `ratelimit:{api_key}:{window}` | 60 seconds | Sliding window rate limit counters |
| `lock:incident:{incident_id}` | 30 minutes | Distributed lock to prevent duplicate investigations |
| `approval:{incident_id}` | 30 minutes | Pending approval state |

### 7.3 Redis Streams

| Stream | Retention | Consumer Groups |
|---|---|---|
| `atlas:incidents` | 7 days | `orchestrator`, `broadcaster`, `auditor` |
| `atlas:agent_events` | 7 days | `broadcaster`, `auditor` |
| `atlas:approvals` | 30 days | `remediation_runner`, `auditor` |

### 7.4 Object Storage

Long-form artifacts (full log excerpts, raw diff files, large metrics snapshots) are stored in S3/GCS with a 90-day lifecycle policy. The database stores only the object URI, not the content. This keeps PostgreSQL rows compact and query performance high.

### 7.5 Data Flow

```
Incident Created
     │
     ▼
incidents table (status = 'investigating')
     │
     ├── agent_runs rows created per agent dispatch
     │        │
     │        ├── Tool calls stored in agent_runs.tool_calls JSONB
     │        └── Large artifacts → S3; URI stored in tool_calls
     │
     ▼
rca_reports row created when synthesis completes
     │
     ├── Status: awaiting_approval
     │
     ▼ (on approval)
audit_log rows written per remediation action
     │
     ▼ (on resolution)
learning_cases row created with embedding
incidents table (status = 'resolved')
```

---

## 8. API Design Overview

The Atlas AI REST API follows REST conventions with JSON bodies, versioned under `/api/v1`. All endpoints require Bearer JWT authentication.

### 8.1 Incident Lifecycle Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/incidents` | Create incident (manual or webhook) |
| `GET` | `/api/v1/incidents` | List incidents with filtering and pagination |
| `GET` | `/api/v1/incidents/{id}` | Get single incident with full state |
| `PATCH` | `/api/v1/incidents/{id}` | Update severity, status, assignee |
| `DELETE` | `/api/v1/incidents/{id}` | Archive incident |
| `POST` | `/api/v1/incidents/{id}/investigate` | Trigger investigation (idempotent) |
| `GET` | `/api/v1/incidents/{id}/rca` | Retrieve RCA for incident |
| `POST` | `/api/v1/incidents/{id}/rca/approve` | Approve or reject remediation |

### 8.2 Agent Monitoring Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/agents` | List all agent types with status |
| `GET` | `/api/v1/agents/{type}/runs` | List runs for a specific agent type |

### 8.3 Observability Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/metrics` | Prometheus-format metrics scrape endpoint |
| `GET` | `/api/v1/health` | Health check with dependency status |
| `GET` | `/api/v1/readiness` | Kubernetes readiness probe |

### 8.4 Real-Time Endpoints

| Protocol | Path | Description |
|---|---|---|
| WebSocket | `/ws/incidents/{id}/progress` | Stream agent events for an incident |

### 8.5 Design Principles

- **Idempotency:** All `POST` endpoints that trigger side effects accept an `Idempotency-Key` header. Re-submitting the same key returns the original response without re-executing.
- **Pagination:** List endpoints use cursor-based pagination with `before`, `after`, and `limit` parameters.
- **Partial responses:** `GET` endpoints accept a `fields` query parameter to return only requested fields (reduces WebSocket payload size).
- **Error format:** All errors return `{"error": {"code": "ERROR_CODE", "message": "...", "details": {...}}}`.

---

## 9. Security Architecture

### 9.1 Threat Model

Atlas AI operates with access to production infrastructure. The primary threats are:

1. **Unauthorized mutation** — an agent or external actor triggering destructive production changes without approval.
2. **Prompt injection** — malicious content in log files or commit messages manipulating agent reasoning.
3. **Credential exfiltration** — an agent tool call extracting secrets from the environment.
4. **LLM hallucination acting** — an agent fabricating tool call parameters leading to unintended actions.

### 9.2 Defense in Depth

**Layer 1 — Network isolation**  
Atlas AI runs in a dedicated Kubernetes namespace with NetworkPolicy rules that restrict egress to only the MCP server addresses. MCP servers are the sole authorized bridge to production systems.

**Layer 2 — Read-only defaults**  
The K8s MCP server uses a dedicated ServiceAccount bound to a ClusterRole that contains only `get`, `list`, `watch` verbs. No mutation verbs are ever in the default role. Mutations are executed under a separate ServiceAccount activated only after approval token validation.

**Layer 3 — Human approval gates**  
No remediation action executes without an approval token. Approval tokens are:
- Signed with RS256 using a key that only the authorization service can issue.
- Bound to the specific action, target resource, and incident ID.
- Valid for 30 minutes maximum.
- Single-use (spent tokens are tracked in Redis).

**Layer 4 — Prompt injection resistance**  
All tool outputs are inserted into agent prompts inside explicit `<tool_output>` XML tags. The system prompt instructs agents to treat content inside these tags as untrustworthy data, never as instructions. Tool outputs are also truncated to a maximum length (10KB per call) to limit injection surface area.

**Layer 5 — Audit log immutability**  
The `audit_log` table uses PostgreSQL row-level security such that the application user can `INSERT` but never `UPDATE` or `DELETE`. A separate read-only audit role exists for compliance review. Critical audit events are also shipped to an external immutable log store (e.g., AWS CloudTrail, GCP Audit Logs).

**Layer 6 — Secret management**  
No credentials are stored in environment variables or Kubernetes Secrets without encryption. All database passwords, API keys, and signing keys are retrieved at startup from HashiCorp Vault using Kubernetes auth. Vault leases are renewed dynamically; no credential has a lifetime longer than 24 hours.

### 9.3 RBAC Model

| Role | Capabilities |
|---|---|
| `viewer` | Read incidents, RCAs, agent run logs |
| `engineer` | All viewer capabilities + trigger investigations manually |
| `approver` | All engineer capabilities + approve/reject remediation |
| `admin` | All approver capabilities + manage users, system config |

---

## 10. Observability

### 10.1 OpenTelemetry Instrumentation

Atlas AI instruments every significant operation with OpenTelemetry traces and spans:

- **HTTP request span** — created by the API gateway middleware for every inbound request.
- **Agent execution span** — one span per agent invocation, attributed with `agent.type`, `incident.id`, `agent_run.id`.
- **LLM call span** — one span per LLM API call, attributed with `llm.model`, `llm.prompt_tokens`, `llm.completion_tokens`, `llm.latency_ms`.
- **Tool call span** — one span per MCP tool invocation, attributed with `tool.name`, `tool.server`, `tool.latency_ms`.

Traces are exported to Jaeger via OTLP gRPC. Trace sampling is set to 100% for P1 incidents, 10% for P2, and 1% for P3/P4.

### 10.2 Prometheus Metrics

All Atlas AI services expose a `/metrics` endpoint scraped by Prometheus every 15 seconds.

**Key metrics:**

| Metric | Type | Description |
|---|---|---|
| `atlas_incidents_total` | Counter | Total incidents by severity and status |
| `atlas_investigation_duration_seconds` | Histogram | Time from incident creation to RCA complete |
| `atlas_agent_run_duration_seconds` | Histogram | Per-agent execution time |
| `atlas_llm_tokens_total` | Counter | LLM tokens consumed by model and agent |
| `atlas_llm_cost_usd_total` | Counter | Estimated LLM API cost |
| `atlas_tool_call_duration_seconds` | Histogram | MCP tool call latency by tool name |
| `atlas_tool_call_errors_total` | Counter | Tool call failures by tool name and error type |
| `atlas_rca_confidence_score` | Gauge | RCA confidence score per incident |
| `atlas_approvals_pending` | Gauge | Number of RCAs awaiting human approval |
| `atlas_remediation_success_total` | Counter | Successful automated remediations |
| `atlas_false_positive_rate` | Gauge | Rolling 7-day false positive rate |

### 10.3 Grafana Dashboards

| Dashboard | Panels |
|---|---|
| **Atlas Overview** | Active incidents, MTTD trend, MTTR trend, agent activity heatmap |
| **Agent Performance** | Per-agent p50/p95 latency, error rates, tool call distribution |
| **LLM Economics** | Token consumption, cost per incident, cost per model |
| **RCA Quality** | Confidence score distribution, human override rate, false positive trend |
| **Learning Loop** | Similar incident retrieval rate, embedding freshness, case store growth |

### 10.4 Alerting

Atlas AI monitors itself. Prometheus alerts fire if:

- Any agent has a p95 execution time > 5 minutes.
- LLM API error rate > 5% over 5 minutes.
- The approval queue has > 10 pending approvals (may indicate a system issue).
- The learning case store has not received a new case in > 24 hours.
- Database replication lag > 30 seconds.

---

## 11. Learning Loop Design

### 11.1 Overview

The learning loop is the mechanism by which Atlas AI improves over time without requiring model retraining. It is based on retrieval-augmented generation (RAG) over a curated store of resolved incidents.

### 11.2 Case Ingestion Pipeline

When an incident is resolved and marked as such:

1. A background worker extracts the incident title, service, symptoms, root cause, and resolution steps.
2. These are concatenated into a structured text representation and embedded using `text-embedding-3-small`.
3. The embedding and structured data are written to the `learning_cases` table.
4. If a human engineer added corrections to the RCA (via the approval/edit flow), the corrected version is used, not the raw LLM output.

### 11.3 Case Retrieval

At investigation start, the Planning Agent:

1. Embeds the new incident's title and symptom description.
2. Queries `learning_cases` with `ORDER BY embedding <=> $1 LIMIT 5`.
3. Filters results with `cosine_similarity > 0.75` to avoid low-quality retrievals.
4. Formats the top results as few-shot examples in the Planning Agent system prompt.

### 11.4 Feedback Loop Quality

Human engineers can rate the quality of retrieved examples during the approval flow. Cases marked as "not helpful" are soft-deleted from the retrieval index (but retained for audit). Cases that received human corrections are up-weighted in retrieval (stored in a `quality_score` column).

### 11.5 Embedding Refresh

When the embedding model is updated, a background migration job re-embeds all cases and rebuilds the IVFFlat index. The old index is kept live until the new one is fully built and validated.

---

## 12. Scalability and Performance SLOs

### 12.1 Service Level Objectives

| SLO | Target | Measurement Method |
|---|---|---|
| MTTD (P1) | < 8 minutes | Time from incident creation to RCA complete |
| MTTD (P2) | < 20 minutes | Time from incident creation to RCA complete |
| RCA confidence | > 80 average score | Confidence field on rca_reports |
| False positive rate | < 2% | Human rejections / total approved remediations, 7-day rolling |
| API p99 latency | < 500ms | Prometheus histogram |
| WebSocket event lag | < 2 seconds | Time from agent event to client delivery |
| Learning retrieval recall | > 90% | Manual evaluation on test set of known incidents |
| System availability | 99.9% | Uptime of API gateway + orchestration layer |

### 12.2 Capacity Model

At 100 P1 incidents/day (enterprise scale):

- **LLM calls:** ~50 calls per incident × 100 = 5,000 calls/day. At ~2 seconds average, this requires ~5 concurrent LLM sessions.
- **PostgreSQL write load:** ~200 rows/incident × 100 = 20,000 rows/day. Well within single-instance capacity.
- **Redis throughput:** ~500 stream events/incident × 100 = 50,000 events/day. Negligible for Redis.
- **Vector search:** At most 1 query/incident, ~100/day. IVFFlat handles this at microsecond latency with a 100K-case store.

### 12.3 Horizontal Scaling

The Orchestration Layer is stateless between agent invocations (state is in PostgreSQL + Redis). Multiple Orchestration Layer replicas can handle concurrent incident investigations without coordination beyond the Redis distributed lock.

MCP servers can be horizontally scaled independently. The K8s MCP server in particular should be scaled to at least 3 replicas to avoid becoming a bottleneck during large incident storms.

---

## 13. Deployment Architecture

### 13.1 Kubernetes Deployment Topology

```
Namespace: atlas-ai
├── Deployments
│   ├── atlas-api (2 replicas min, HPA max 10)
│   ├── atlas-orchestrator (2 replicas min, HPA max 5)
│   ├── atlas-worker (3 replicas min, HPA max 20)
│   └── atlas-dashboard (2 replicas min)
│
├── StatefulSets
│   ├── atlas-postgres (primary + 1 replica)
│   └── atlas-redis (1 primary + 1 replica)
│
├── Deployments (MCP Servers)
│   ├── mcp-kubernetes (3 replicas)
│   ├── mcp-github (2 replicas)
│   ├── mcp-storage (2 replicas)
│   ├── mcp-network (2 replicas)
│   ├── mcp-security (2 replicas)
│   ├── mcp-metrics (2 replicas)
│   ├── mcp-cost (2 replicas)
│   └── mcp-docs (2 replicas)
│
└── CronJobs
    ├── atlas-embedding-refresher (weekly)
    └── atlas-case-quality-scorer (daily)
```

### 13.2 Infrastructure Requirements (Production)

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---|---|---|---|---|
| atlas-api | 500m | 2000m | 512Mi | 2Gi |
| atlas-orchestrator | 1000m | 4000m | 1Gi | 4Gi |
| atlas-worker | 500m | 2000m | 512Mi | 2Gi |
| atlas-postgres | 2000m | 8000m | 4Gi | 16Gi |
| atlas-redis | 500m | 2000m | 1Gi | 4Gi |
| mcp-kubernetes | 200m | 500m | 256Mi | 512Mi |
| Each MCP server | 100m | 500m | 128Mi | 512Mi |

### 13.3 CI/CD Pipeline

```
GitHub Push → GitHub Actions:
  1. Unit tests (pytest, coverage > 80%)
  2. Integration tests (against test cluster)
  3. Security scan (Trivy, Semgrep)
  4. Docker image build and push to ECR
  5. Helm chart lint and template validation
  6. Deploy to staging (automatic)
  7. Run smoke tests against staging
  8. Deploy to production (manual gate for main branch)
  9. Post-deployment canary metrics check (15 min)
```

### 13.4 Disaster Recovery

- **PostgreSQL:** Daily full backup + continuous WAL archiving to S3. Point-in-time recovery to within 5 minutes. Cross-region replica in passive standby.
- **Redis:** RDB snapshots every hour. Streams data is recoverable from PostgreSQL audit log if needed.
- **MCP servers:** Stateless; re-deployment from image takes < 2 minutes.
- **RTO:** 30 minutes (full cluster failure). **RPO:** 5 minutes (data loss window).

### 13.5 Configuration Management

All configuration is managed via Kubernetes ConfigMaps and Secrets. Secrets are sealed with Sealed Secrets (Bitnami) before committing to the GitOps repository. Vault integration provides dynamic secret rotation for database credentials and API keys. Environment-specific values are parameterized in Helm values files per environment (dev, staging, production).
