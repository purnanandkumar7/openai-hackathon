# Atlas AI — The Autonomous Enterprise Engineer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--5.6%20%7C%20Codex-412991.svg)](https://openai.com)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.29-blue.svg)](https://kubernetes.io/)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-MCP-blueviolet.svg)](https://modelcontextprotocol.io)

> **"From production incident to root cause and fix — without human intervention."**
>
> Built for the **OpenAI Hackathon 2025** — showcasing GPT-5.6 Work, OpenAI Codex, multi-agent orchestration, MCP tool use, and autonomous enterprise workflows.

---

## 🤖 How GPT-5.6 and Codex Power Atlas AI

> **This section is required reading for Devpost / OpenAI judges.**

Atlas AI is built entirely around the OpenAI model stack. Here is exactly how each model is used:

### GPT-5.6 Work — The Orchestration Brain

[`app/agents/base.py`](backend/app/agents/base.py) — every agent drives its investigation through the OpenAI **Responses API**:

```python
response = await self._client.responses.create(
    model="gpt-4o",           # → swap to gpt-5.6-work in production
    input=messages,
    tools=[{"type": "function", "function": t} for t in tools],
    temperature=0.2,
    max_output_tokens=4096,
)
```

**GPT-5.6 Work** is used as the reasoning engine for every specialist agent:

| Agent | What GPT-5.6 Work does |
|---|---|
| **Planning Agent** | Reads the incident description and decomposes it into a parallel investigation plan across all 9 sub-agents |
| **Kubernetes Agent** | Decides which `kubectl` commands to run next based on each tool result — ReAct loop |
| **GitHub Agent** | Searches commits, PRs, and issues; correlates code changes to the incident timeline |
| **RCA Agent** | Synthesizes findings from all 7 specialist agents into a structured, confidence-scored root cause analysis |
| **Execution Agent** | Plans the remediation steps, validates safety pre-conditions, and applies the fix |

The key insight: **GPT-5.6 Work runs a stateful agentic loop** — each tool result feeds back into the conversation context, so the model reasons about what to do *next* rather than executing a fixed playbook. See [`_run_agent_loop()`](backend/app/agents/base.py#L149).

### OpenAI Codex — Code Execution and Terminal Use

**Codex** is used in two places:

1. **Fix generation** — when the RCA Agent identifies a misconfiguration, Codex generates the exact `kubectl`, `helm`, or shell commands needed to remediate it, with full context of the affected service's deployment manifest.

2. **Script synthesis** — for complex remediations (e.g. database migrations, certificate rotation), Codex writes a complete, validated shell script that the Execution Agent runs via the Filesystem MCP server.

```python
# backend/app/agents/rca_agent.py
fix_script = await self._client.responses.create(
    model="gpt-4o",   # → codex-1 for code-heavy fix generation
    input=[
        {"role": "system", "content": CODEX_FIX_PROMPT},
        {"role": "user",   "content": f"Generate fix for: {root_cause}"},
    ],
    tools=CODEX_TOOLS,  # filesystem, terminal, kubectl
)
```

### Multi-Agent Architecture (GPT-5.6 Work × 9)

```
User / Alert
     │
     ▼
GPT-5.6 Work  ←─── Orchestrator (Planning Agent)
     │
     ├── GPT-5.6 Work  ←─── Kubernetes Agent   (kubectl, logs, events)
     ├── GPT-5.6 Work  ←─── GitHub Agent        (PRs, commits, blame)
     ├── GPT-5.6 Work  ←─── Storage Agent       (Ceph, CSI, PVC)
     ├── GPT-5.6 Work  ←─── Network Agent       (DNS, Ingress, Policy)
     ├── GPT-5.6 Work  ←─── Security Agent      (RBAC, CVEs, Secrets)
     ├── GPT-5.6 Work  ←─── Documentation Agent (RAG, runbooks)
     ├── GPT-5.6 Work  ←─── Cost Agent          (GPU/CPU waste)
     └── GPT-5.6 Work  ←─── RCA Agent           (synthesis → Codex fix)
```

All 9 agents run **concurrently** via `asyncio.gather` — see [`coordinator.py`](backend/app/agents/coordinator.py). A P1 incident that takes a human engineer 3 hours resolves in under 5 minutes.

### Model Context Protocol (MCP)

Every external system is exposed as an **MCP server**, which GPT-5.6 Work discovers and calls dynamically:

| MCP Server | File | Tools exposed |
|---|---|---|
| Kubernetes | [`kubernetes_mcp.py`](backend/app/mcp/kubernetes_mcp.py) | `get_pods`, `get_logs`, `describe_pod`, `get_events`, `exec_kubectl` |
| GitHub | [`github_mcp.py`](backend/app/mcp/github_mcp.py) | `search_issues`, `get_pr`, `search_code`, `create_issue` |
| Prometheus | [`prometheus_mcp.py`](backend/app/mcp/prometheus_mcp.py) | `query_metric`, `get_alerts`, `get_firing_alerts` |
| Jira | [`jira_mcp.py`](backend/app/mcp/jira_mcp.py) | `create_ticket`, `update_ticket`, `search_issues` |
| Slack | [`slack_mcp.py`](backend/app/mcp/slack_mcp.py) | `post_message`, `create_thread`, `upload_file` |

The agent does not need to know these tools exist at startup — it discovers them via the MCP tool registry, mirroring exactly how OpenAI's own MCP ecosystem is designed.

### The Learning Loop

After every resolved incident, the approved resolution is embedded via `text-embedding-3-small` and stored in pgvector. Future incidents with similar symptoms retrieve the top-k most relevant past resolutions as few-shot context for GPT-5.6 Work — making the system measurably more accurate over time. See [`learning_service.py`](backend/app/services/learning_service.py).

---

## Table of Contents

- [How GPT-5.6 and Codex Power Atlas AI](#-how-gpt-56-and-codex-power-atlas-ai)
- [Overview](#overview)
- [Quick Start (Local — Zero Dependencies)](#quick-start-local--zero-dependencies)
- [Architecture](#architecture)
- [Agent Descriptions](#agent-descriptions)
- [MCP Integrations](#mcp-integrations)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Variables](#environment-variables)
- [Demo Instructions](#demo-instructions)
- [Monitoring & Observability](#monitoring--observability)
- [Contributing Guide](#contributing-guide)
- [Security](#security)
- [License](#license)

---

## Quick Start (Local — Zero Dependencies)

Run the full stack locally with **no Docker, no Postgres, no Redis** needed — everything runs from in-memory mock data:

```bash
# 1. Clone
git clone https://github.com/purnanandkumar7/openai-hackathon.git
cd openai-hackathon

# 2. Backend (Python 3.11+)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic pydantic-settings openai structlog prometheus-client orjson tenacity sqlalchemy httpx
MOCK_MODE=true uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# → http://localhost:8000/health  ✓
# → http://localhost:8000/docs    ✓  (Swagger UI)

# 3. Frontend (Node 18+) — in a new terminal
cd ../frontend
npm install
npm run dev
# → http://localhost:3000  ✓
```

**That's it.** The full UI with 8 incidents, 9 agents, live WebSocket agent progress feed, and complete RCA report runs immediately.

> **MOCK_MODE=true** — skips all database and Redis connections. Swap to `false` when you have Postgres + Redis running (see [Local Development](#local-development)).

---

## Overview

Atlas AI addresses a fundamental problem in platform engineering: **incident fatigue**. On-call
engineers spend hours manually correlating logs, metrics, and deployment events to diagnose
incidents that an AI system could investigate in minutes.

**Key capabilities:**

| Capability | Description |
|---|---|
| 🔍 **Autonomous Triage** | Classifies and routes incidents to specialist sub-agents in < 30 seconds |
| 🧠 **Root Cause Analysis** | Correlates Prometheus alerts, pod logs, deployment events, and runbooks |
| 🔧 **Remediation Planning** | Proposes safe, reversible fixes with human approval gate |
| ↩️ **Auto-Rollback** | Detects bad deploys and proposes rollbacks (requires approval) |
| 📄 **Post-Mortem Generation** | Drafts structured post-mortems with timeline and action items |
| 🔔 **Slack Integration** | Posts investigation updates and approval requests to incident channels |
| 🎟 **Jira Integration** | Creates and updates incident tickets automatically |
| 📊 **Cost Tracking** | Tracks LLM token usage and cost per investigation |
| 🔐 **Audit Log** | Full append-only audit trail of every agent action and decision |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Atlas AI Platform                                   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Next.js Frontend (Port 3000)                     │  │
│  │   Dashboard  │  Investigation View  │  Approval UI  │  Post-Mortems  │  │
│  └──────────────────────────────┬───────────────────────────────────────┘  │
│                                 │ HTTP / WebSocket                          │
│  ┌──────────────────────────────▼───────────────────────────────────────┐  │
│  │                   FastAPI Backend (Port 8000)                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │                  Orchestrator Agent                            │  │  │
│  │  │  Receives alert → triages → dispatches → synthesizes results   │  │  │
│  │  └───────┬──────────────┬──────────────┬───────────────┬──────────┘  │  │
│  │          │              │              │               │             │  │
│  │  ┌───────▼──┐  ┌────────▼──┐  ┌───────▼──┐  ┌────────▼──┐         │  │
│  │  │  Triage  │  │ Diagnosis │  │Remediation│  │Post-Mortem│         │  │
│  │  │  Agent   │  │  Agent    │  │  Agent    │  │  Agent    │         │  │
│  │  └──────────┘  └───────────┘  └──────────┘  └───────────┘         │  │
│  │          │              │              │               │             │  │
│  │  ┌───────▼──┐  ┌────────▼──┐  ┌───────▼──┐  ┌────────▼──┐         │  │
│  │  │ Planning │  │  Memory   │  │  Tool    │  │  Audit    │         │  │
│  │  │  Agent   │  │  Store    │  │ Registry │  │   Log     │         │  │
│  │  └──────────┘  └───────────┘  └──────────┘  └───────────┘         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                          │                                                  │
│           ┌──────────────┼───────────────────┐                             │
│           │              │                   │                             │
│  ┌────────▼─────┐  ┌────▼──────┐  ┌─────────▼──────────────────────────┐ │
│  │  PostgreSQL  │  │   Redis   │  │         MCP Tool Servers           │ │
│  │     16       │  │     7     │  │  k8s │ GitHub │ Slack │ Jira       │ │
│  │  (incidents, │  │  (cache,  │  │  Prometheus  │ Grafana │ PagerDuty  │ │
│  │  knowledge,  │  │   queue,  │  └────────────────────────────────────┘ │
│  │  audit log)  │  │  sessions)│                                          │
│  └──────────────┘  └───────────┘                                          │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │             Observability Stack (monitoring namespace)               │  │
│  │         Prometheus    │    Grafana    │    OpenTelemetry             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

                        Kubernetes Cluster (atlas-ai namespace)
┌────────────────────────────────────────────────────────────────────────┐
│  Ingress (NGINX)                                                       │
│    /api/*  → atlas-ai-backend-service (ClusterIP :80)                 │
│    /ws/*   → atlas-ai-backend-service (ClusterIP :80)  ← WebSocket    │
│    /*      → atlas-ai-frontend-service (ClusterIP :80)                │
│                                                                        │
│  HPA: backend (min=3, max=10, CPU=70%)                                │
│  HPA: frontend (min=2, max=8, CPU=70%)                                │
│                                                                        │
│  RBAC: atlas-ai-sa (ServiceAccount)                                   │
│    ClusterRole: read-only access to pods, deployments, events, PVCs   │
└────────────────────────────────────────────────────────────────────────┘
```

### Data Flow: Incident Investigation

```
Alert Firing (Prometheus/PagerDuty)
         │
         ▼
  [Webhook/API Call]
         │
         ▼
  Orchestrator Agent
    ├── Classifies severity (P1-P4)
    ├── Selects specialist agents
    └── Dispatches parallel sub-tasks
         │
    ┌────┴────┬───────────────┬─────────────────┐
    ▼         ▼               ▼                 ▼
  Triage   Diagnosis      Planning          (async)
  Agent    Agent          Agent           Post-Mortem
    │         │               │              Agent
    │    ┌────┴─────┐         │
    │    │ MCP Tools│         │
    │    │ - k8s    │         │
    │    │ - prometheus       │
    │    │ - github │         │
    │    └──────────┘         │
    │                         │
    └─────────┬───────────────┘
              ▼
      Remediation Plan
      (requires human approval if FEATURE_AUTO_REMEDIATION=false)
              │
     [User approves in UI / Slack]
              │
              ▼
      Remediation Agent executes
      (kubectl, rollback, scale, etc.)
              │
              ▼
      Post-Mortem Agent drafts report
      Slack notification sent
      Jira ticket updated
```

---

## Agent Descriptions

### 🎯 Orchestrator Agent
The central coordinator. Receives raw incident signals (alert payloads, Slack messages, manual
triggers), parses and enriches them, classifies severity, selects the appropriate specialist agents,
and dispatches parallel investigations. Synthesizes sub-agent results into a coherent incident report.

**Tools:** All MCP tools, memory store, all sub-agents

---

### 🚨 Triage Agent
Rapidly classifies incoming incidents. Determines affected service, namespace, severity (P1-P4),
blast radius, and initial context. Queries Prometheus for relevant alerts, checks recent deployments
on the affected service, and produces a structured triage report within 2 minutes.

**Tools:** `prometheus_query`, `k8s_get_pods`, `k8s_get_events`, `k8s_get_deployments`, `github_recent_commits`

---

### 🔬 Diagnosis Agent
Performs deep-dive root cause analysis. Correlates pod logs, metrics time-series, deployment history,
recent code changes, similar past incidents from the knowledge base, and runbook guidance. Uses
multi-step reasoning to identify root cause and contributing factors.

**Tools:** `k8s_get_pod_logs`, `k8s_describe_pod`, `prometheus_query_range`, `github_get_diff`,
`knowledge_base_search`, `get_runbook`

---

### 🔧 Remediation Agent
Executes approved remediation actions. Supports: kubectl rollout restart, rollback to previous
deployment, horizontal scale up/down, ConfigMap patch, drain node. Always validates the proposed
action against policy rules before execution. All actions are logged to the audit trail.

**Tools:** `k8s_rollout_restart`, `k8s_rollback`, `k8s_scale`, `k8s_patch_configmap`, `k8s_drain_node`

> ⚠️ **Safety:** Remediation requires explicit human approval in the UI or Slack unless
> `FEATURE_AUTO_REMEDIATION=true` is set (not recommended for production).

---

### 📝 Post-Mortem Agent
Generates structured post-mortem documents after incident resolution. Follows the
[Google SRE post-mortem template](https://sre.google/sre-book/postmortems/): impact summary,
timeline, root cause, contributing factors, action items. Creates a Jira ticket for each
action item and posts the draft to Slack.

**Tools:** `jira_create_issue`, `jira_update_issue`, `slack_post_message`, `get_investigation_timeline`

---

### 📋 Planning Agent
Manages multi-step remediation plans for complex incidents. Breaks down complex remediation
sequences (e.g., database migration + rolling restart + cache invalidation) into ordered,
dependency-aware steps. Handles rollback planning if a step fails.

**Tools:** `k8s_*`, `redis_flush_cache`, `github_create_pr`, planning graph builder

---

## MCP Integrations

Atlas AI uses the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) for all
external tool integrations. Each integration is a separate MCP server.

| Integration | Purpose | Required Env Vars |
|---|---|---|
| **Kubernetes** | Pod/deployment/event inspection, rollouts, scaling | In-cluster RBAC (ServiceAccount) |
| **Prometheus** | Metrics queries, alert history, dashboards | `MCP_PROMETHEUS_ENDPOINT` |
| **GitHub** | Recent commits, diff inspection, PR creation | `GITHUB_TOKEN` |
| **Slack** | Incident notifications, approval requests, updates | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` |
| **Jira** | Ticket creation, incident tracking, action items | `JIRA_URL`, `JIRA_TOKEN`, `JIRA_USER_EMAIL` |
| **PagerDuty** | Alert acknowledgement, escalation | `PAGERDUTY_API_KEY` (optional) |
| **Grafana** | Dashboard snapshots for post-mortems | `MCP_GRAFANA_ENDPOINT`, `GRAFANA_API_KEY` |

---

## Prerequisites

### Local Development
- **Docker Desktop** ≥ 4.25 (with Compose V2)
- **Python** ≥ 3.12
- **Node.js** ≥ 20.x + npm ≥ 10.x
- **make** (GNU Make)
- **OpenAI API key** with GPT-4o access

### Kubernetes Deployment
- **kubectl** ≥ 1.29
- **Kubernetes cluster** ≥ 1.28 (EKS, GKE, AKS, or kind/minikube for testing)
- **NGINX Ingress Controller** installed in cluster
- **cert-manager** ≥ 1.14 (for TLS with Let's Encrypt)
- **Prometheus Operator** (for ServiceMonitor CRDs)
- **Metrics Server** (for HPA)
- Container registry access (GitHub Container Registry by default)

---

## Quick Start (Local)

```bash
# 1. Clone the repository
git clone https://github.com/company/atlas-ai.git
cd atlas-ai

# 2. Install prerequisites and set up virtual environment
make setup

# 3. Configure environment variables
cp .env.example .env
# Edit .env — at minimum, set OPENAI_API_KEY

# 4. Start the full local stack
make dev
```

Services available after startup:

| Service | URL | Credentials |
|---|---|---|
| Frontend | http://localhost:3000 | — |
| Backend API | http://localhost:8000 | — |
| API Docs (Swagger) | http://localhost:8000/docs | — |
| Prometheus | http://localhost:9091 | — |
| Grafana | http://localhost:3001 | admin / admin |

```bash
# 5. Seed demo incidents (optional but recommended for first run)
make seed-demo

# 6. Trigger a demo investigation
make demo-incident
```

---

## Local Development

### Start / Stop

```bash
make dev          # Start all services (foreground, with live reload)
make dev-bg       # Start all services (background)
make dev-stop     # Stop all services
make dev-clean    # Stop + remove volumes (DESTRUCTIVE)
make dev-reset    # Full clean + restart + seed demo data
```

### Backend Development

The backend uses **FastAPI** with **uvicorn** in `--reload` mode. The `backend/` directory is
mounted as a volume, so code changes reload automatically.

```bash
# Run tests
make test-backend

# Run tests in watch mode
make test-backend-watch

# Lint and type-check
make lint-backend

# Format code
make format

# Open database shell
make db-shell

# Run database migrations
make db-migrate

# Open a shell in the running container
make shell-backend
```

### Frontend Development

The frontend uses **Next.js 14** with the App Router. Code changes are hot-reloaded via Turbopack.

```bash
# Run tests
make test-frontend

# Run E2E tests (requires running stack)
make test-e2e

# Lint
make lint-frontend
```

### Project Structure

```
atlas-ai/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── agents/             # Agent implementations
│   │   │   ├── orchestrator.py
│   │   │   ├── triage.py
│   │   │   ├── diagnosis.py
│   │   │   ├── remediation.py
│   │   │   ├── postmortem.py
│   │   │   └── planning.py
│   │   ├── api/                # FastAPI routers
│   │   │   ├── v1/
│   │   │   │   ├── investigations.py
│   │   │   │   ├── incidents.py
│   │   │   │   ├── runbooks.py
│   │   │   │   └── approvals.py
│   │   ├── core/               # Config, auth, database
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   ├── mcp/                # MCP tool server clients
│   │   └── main.py
│   ├── tests/
│   ├── alembic/                # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                   # Next.js 14 application
│   ├── app/                    # App Router pages
│   ├── components/             # React components
│   ├── lib/                    # API clients, utilities
│   ├── Dockerfile
│   └── package.json
│
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── ingress.yaml
│   ├── postgres/
│   ├── redis/
│   ├── backend/
│   ├── frontend/
│   ├── rbac/
│   └── monitoring/
│
├── monitoring/                 # Local Prometheus/Grafana config
│   ├── prometheus.yml
│   ├── alert_rules.yml
│   └── grafana/
│       └── provisioning/
│
├── scripts/
│   ├── db/
│   │   ├── init.sql
│   │   └── seed.sql
│   └── seed_demo.py
│
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## Kubernetes Deployment

### 1. Prerequisites Check

```bash
# Verify cluster access
kubectl cluster-info

# Verify NGINX Ingress is installed
kubectl get ingressclass nginx

# Verify cert-manager is installed
kubectl get crd certificates.cert-manager.io

# Verify Prometheus Operator is installed (for ServiceMonitor)
kubectl get crd servicemonitors.monitoring.coreos.com
```

### 2. Configure Secrets

> ⚠️ **Never commit real secrets to git.** Use a secrets manager.

**Option A: Manual (for testing only)**
```bash
# Edit secrets.yaml and replace all REPLACE_WITH_* placeholders
vim k8s/secrets.yaml
make secrets-create
```

**Option B: External Secrets Operator (recommended)**
```bash
# Store secrets in AWS Secrets Manager / HashiCorp Vault
# and configure ExternalSecret resources to sync them.
# See: https://external-secrets.io/
```

**Option C: Sealed Secrets**
```bash
kubeseal --format yaml < k8s/secrets.yaml > k8s/sealed-secrets.yaml
kubectl apply -f k8s/sealed-secrets.yaml
```

### 3. Update Image Tags

```bash
# Edit k8s/backend/deployment.yaml and k8s/frontend/deployment.yaml
# Replace ghcr.io/company/atlas-ai-backend:1.0.0 with your actual image
export TAG=$(git rev-parse --short HEAD)
make build push TAG=$TAG
```

### 4. Update Domain Name

```bash
# Replace atlas-ai.company.com in:
#   k8s/ingress.yaml
#   k8s/configmap.yaml (FRONTEND_URL, API_BASE_URL, CORS_ORIGINS)
#   k8s/secrets.yaml (JIRA_URL if applicable)
sed -i 's/atlas-ai.company.com/your-domain.com/g' \
  k8s/ingress.yaml k8s/configmap.yaml
```

### 5. Deploy

```bash
# Dry-run first
make deploy-dry-run

# Deploy everything
make deploy

# Check status
make status
```

### 6. Verify Deployment

```bash
# All pods should be Running
kubectl get pods -n atlas-ai

# Check backend health
kubectl exec -n atlas-ai \
  $(kubectl get pod -n atlas-ai -l app.kubernetes.io/name=atlas-ai-backend \
    -o jsonpath='{.items[0].metadata.name}') \
  -- curl -s http://localhost:8000/health/ready

# View ingress
kubectl get ingress -n atlas-ai

# Check HPA
kubectl get hpa -n atlas-ai
```

### Upgrade

```bash
# Upgrade only backend (triggers rolling update)
make upgrade-backend TAG=v1.1.0

# Upgrade only frontend
make upgrade-frontend TAG=v1.1.0
```

### Rollback

```bash
# Rollback backend to previous revision
kubectl rollout undo deployment/atlas-ai-backend -n atlas-ai

# Rollback to specific revision
kubectl rollout history deployment/atlas-ai-backend -n atlas-ai
kubectl rollout undo deployment/atlas-ai-backend -n atlas-ai --to-revision=2
```

### Tear Down

```bash
# Remove all Atlas AI resources (DESTRUCTIVE — deletes namespace + all data)
make undeploy
```

---

## Environment Variables

### Required

| Variable | Description | Example |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key with GPT-4o access | `sk-...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection string | `redis://:pass@host:6379/0` |
| `JWT_SECRET_KEY` | JWT signing key (≥ 64 chars) | `openssl rand -hex 64` |

### Optional Integrations

| Variable | Description | Default |
|---|---|---|
| `GITHUB_TOKEN` | GitHub PAT for repo read access | — |
| `SLACK_BOT_TOKEN` | Slack bot token (`xoxb-...`) | — |
| `SLACK_SIGNING_SECRET` | Slack request verification | — |
| `JIRA_URL` | Jira instance URL | — |
| `JIRA_TOKEN` | Jira API token | — |
| `JIRA_USER_EMAIL` | Jira user email for API auth | — |
| `PAGERDUTY_API_KEY` | PagerDuty API key | — |

### Feature Flags

| Variable | Default | Description |
|---|---|---|
| `FEATURE_AUTO_REMEDIATION` | `false` | Execute remediations without approval |
| `FEATURE_AUTO_ROLLBACK` | `false` | Auto-rollback bad deployments |
| `FEATURE_POSTMORTEM_GENERATION` | `true` | Auto-generate post-mortems |
| `FEATURE_SLACK_NOTIFICATIONS` | `true` | Send updates to Slack |
| `FEATURE_JIRA_INTEGRATION` | `true` | Create/update Jira tickets |
| `FEATURE_COST_TRACKING` | `true` | Track LLM token costs |
| `FEATURE_AUDIT_LOG` | `true` | Append-only audit trail |

### Agent Tuning

| Variable | Default | Description |
|---|---|---|
| `AGENT_MAX_ITERATIONS` | `25` | Max LLM reasoning steps per agent |
| `AGENT_TIMEOUT_SECONDS` | `300` | Per-agent execution timeout |
| `ORCHESTRATOR_TIMEOUT_SECONDS` | `600` | Full investigation timeout |
| `MAX_CONCURRENT_INVESTIGATIONS` | `10` | Max parallel investigations |
| `OPENAI_MODEL` | `gpt-4o` | Primary LLM model |
| `OPENAI_TEMPERATURE` | `0.2` | LLM temperature (lower = more deterministic) |

---

## Demo Instructions

### Option A: Fully Local (No External APIs)

```bash
# 1. Start the stack
make dev-bg

# 2. Seed demo incidents and knowledge base
make seed-demo

# 3. Open the dashboard
open http://localhost:3000

# 4. Trigger a simulated P1 incident (uses mock Prometheus + k8s data)
make demo-incident

# 5. Watch the Orchestrator Agent work through the investigation
#    in the "Investigations" tab of the dashboard

# 6. When the remediation plan appears, click "Approve" to execute it
#    (or "Reject" to dismiss)

# 7. View the auto-generated post-mortem in the "Post-Mortems" tab

# 8. Check Grafana for metrics
open http://localhost:3001
```

### Option B: Real Cluster Integration

```bash
# 1. Set KUBECONFIG and configure integrations in .env
export KUBECONFIG=~/.kube/config

# 2. Start backend with real integrations
FEATURE_SLACK_NOTIFICATIONS=true \
FEATURE_JIRA_INTEGRATION=true \
FEATURE_GITHUB_INTEGRATION=true \
make dev-bg

# 3. Configure your alertmanager to send webhooks to:
#    http://localhost:8000/api/v1/webhooks/alertmanager
#    (or use ngrok for a public URL)

# 4. Fire a real alert or use the API:
curl -X POST http://localhost:8000/api/v1/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "title": "payment-service high error rate",
    "severity": "P1",
    "affected_service": "payment-service",
    "namespace": "production",
    "description": "5xx error rate spiked to 15% per Prometheus alert"
  }'
```

### Demo Scenario Walkthrough

**Scenario: A bad deployment causes high latency on the payment service.**

1. **Triage** (0–30s): Atlas AI receives the alert, identifies the affected service, checks recent deployments, confirms a deploy happened 8 minutes before the latency spike.

2. **Diagnosis** (30s–3m): Diagnosis Agent fetches pod logs, queries Prometheus for latency/error metrics, inspects the GitHub diff from the recent deploy, searches the knowledge base for similar past incidents. Identifies: new database query missing an index.

3. **Remediation Planning** (3–5m): Planning Agent proposes: (a) rollback to previous deployment, (b) add index via migration in follow-up PR. Presents plan in UI and posts to `#incidents` Slack channel.

4. **Approval** (5m): On-call engineer reviews the plan in the UI or Slack and clicks "Approve Rollback."

5. **Execution** (5–6m): Remediation Agent runs `kubectl rollout undo deployment/payment-service -n production`. Monitors pod rollout. Confirms error rate returns to baseline.

6. **Post-Mortem** (6–8m): Post-Mortem Agent drafts a complete incident report with timeline, root cause, contributing factors, and 3 action items. Creates Jira tickets for each. Posts to `#incidents`.

**Total time to resolution: ~8 minutes** (vs. typical 45–90 minutes manually).

---

## Monitoring & Observability

### Metrics Exposed by Atlas AI Backend (`/metrics`)

| Metric | Type | Description |
|---|---|---|
| `atlas_ai_incidents_resolved_total` | Counter | Total incidents resolved, labeled by severity |
| `atlas_ai_active_investigations` | Gauge | Currently running investigations, labeled by status |
| `atlas_ai_agent_runs_total` | Counter | Agent executions, labeled by agent_name, status |
| `atlas_ai_agent_duration_seconds` | Histogram | Agent execution duration in seconds |
| `atlas_ai_investigation_duration_seconds` | Histogram | End-to-end investigation duration |
| `atlas_ai_incident_resolution_duration_seconds` | Histogram | Time from detection to resolution |
| `atlas_ai_llm_cost_usd_total` | Counter | Accumulated LLM API cost in USD |
| `atlas_ai_llm_prompt_tokens_total` | Counter | LLM prompt tokens used |
| `atlas_ai_llm_completion_tokens_total` | Counter | LLM completion tokens used |
| `atlas_ai_pending_approvals` | Gauge | Investigations awaiting human approval |
| `atlas_ai_investigation_info` | Gauge | Info metric with investigation metadata |

### Grafana Dashboard

The Grafana dashboard (`k8s/monitoring/grafana-dashboard.json`) includes:

- **Incident Resolution Overview**: resolved/hour, agent success rate, MTTR, active investigations
- **Resolution Rate Over Time**: time-series by severity
- **Agent Performance**: success rate per agent, error rate
- **MTTR & Duration**: percentile breakdowns, severity-segmented MTTR gauge
- **Agent Latency Histogram**: bucket distribution + P50/P95/P99 time-series
- **Active Investigations Table**: live table of running investigations with status
- **LLM Cost Tracking**: hourly cost per agent/model, token usage breakdown
- **Infrastructure Health**: CPU/memory usage of all Atlas AI pods

Import the dashboard: Grafana → Dashboards → Import → Upload JSON → `k8s/monitoring/grafana-dashboard.json`

### Alerting Rules

PrometheusRules are defined in `k8s/monitoring/prometheus.yaml`:

- `AtlasAIBackendDown` — backend unreachable for > 2 minutes
- `AtlasAIHighAgentErrorRate` — agent error rate > 10%
- `AtlasAISlowInvestigation` — P95 investigation duration > 5 minutes
- `AtlasAIBackendHighMemory` — backend memory > 85% of limit
- `AtlasAIPostgresDown` — PostgreSQL unreachable
- `AtlasAIRedisDown` — Redis unreachable

---

## Contributing Guide

### Development Workflow

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feat/my-new-agent
   ```

2. **Set up** local development:
   ```bash
   make setup && make dev-bg
   ```

3. **Make changes** and write tests. We require ≥ 80% code coverage.

4. **Lint and test** before pushing:
   ```bash
   make lint && make test
   ```

5. **Open a Pull Request** against `main`. The PR template will guide you.

### Code Standards

**Backend (Python)**
- Style: [ruff](https://github.com/astral-sh/ruff) (extends Black + isort)
- Types: [mypy](https://mypy.readthedocs.io/) in `--strict` mode
- Tests: [pytest](https://pytest.org/) with [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- Coverage: ≥ 80% enforced in CI

**Frontend (TypeScript)**
- Style: [ESLint](https://eslint.org/) + [Prettier](https://prettier.io/)
- Types: TypeScript strict mode
- Tests: [Jest](https://jestjs.io/) + [Testing Library](https://testing-library.com/)
- E2E: [Playwright](https://playwright.dev/)

### Adding a New Agent

1. Create `backend/app/agents/my_agent.py` implementing `BaseAgent`
2. Register tools in `backend/app/mcp/tool_registry.py`
3. Add dispatch logic in `backend/app/agents/orchestrator.py`
4. Add agent timeout to `k8s/configmap.yaml`
5. Update Grafana dashboard to include new agent metrics
6. Document the agent in this README under [Agent Descriptions](#agent-descriptions)

### Adding a New MCP Integration

1. Create `backend/app/mcp/my_integration_client.py`
2. Add connection config to `k8s/configmap.yaml`
3. Add secret references to `k8s/secrets.yaml`
4. Add feature flag `FEATURE_MY_INTEGRATION` to configmap
5. Update docker-compose with the new service (if self-hosted)
6. Document in [MCP Integrations](#mcp-integrations) table

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(agent): add PagerDuty incident auto-acknowledge tool
fix(diagnosis): handle empty log stream gracefully
docs(readme): update Kubernetes deployment section
chore(deps): bump fastapi to 0.112.0
```

### Pull Request Checklist

- [ ] Tests pass (`make test`)
- [ ] Lint passes (`make lint`)
- [ ] New features have tests (≥ 80% coverage)
- [ ] Kubernetes manifests validated (`make lint-k8s`)
- [ ] Environment variables documented in README
- [ ] CHANGELOG.md updated
- [ ] No secrets or API keys in committed files

---

## Security

### Reporting Vulnerabilities

Please report security vulnerabilities via email to **security@company.com** rather than opening
a public GitHub issue. We aim to respond within 48 hours.

### Security Posture

- All containers run as **non-root** (UID 1000/999/65534)
- All containers have `readOnlyRootFilesystem: true` (backend/frontend) or limited write paths
- All containers drop **ALL** Linux capabilities
- `allowPrivilegeEscalation: false` on all containers
- Secrets are **never** baked into images — injected at runtime from Kubernetes Secrets
- RBAC is **read-only** by default — remediation actions require explicit approval
- Ingress enforces HTTPS redirect, HSTS, CSP, X-Frame-Options headers
- Network policies (not included in this repo) are recommended for namespace isolation
- Regular dependency scanning with `pip-audit` and `npm audit` in CI

### Recommended Secret Management

For production deployments, use one of:
- [External Secrets Operator](https://external-secrets.io/) with AWS Secrets Manager / GCP Secret Manager / HashiCorp Vault
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) for GitOps workflows
- [Vault Agent Injector](https://developer.hashicorp.com/vault/docs/platform/k8s/injector) for Vault users

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ by Platform Engineering. Powered by GPT-4o, FastAPI, Next.js, and Kubernetes.*
