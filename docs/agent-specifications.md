# Atlas AI — Agent Specifications

**Version:** 1.0.0  
**Status:** Living Document  
**Last Updated:** 2025-01-01  
**Authors:** Atlas AI Platform Team

---

## Table of Contents

1. [Specification Format](#1-specification-format)
2. [Planning Agent](#2-planning-agent)
3. [Kubernetes Agent](#3-kubernetes-agent)
4. [GitHub Agent](#4-github-agent)
5. [Storage Agent](#5-storage-agent)
6. [Network Agent](#6-network-agent)
7. [Security Agent](#7-security-agent)
8. [RCA Agent](#8-rca-agent)
9. [Documentation Agent](#9-documentation-agent)
10. [Cost Agent](#10-cost-agent)

---

## 1. Specification Format

Each agent specification includes:

- **Purpose** — what the agent does and why it exists.
- **Trigger conditions** — what causes this agent to be invoked.
- **Tools** — every tool available to the agent with full parameter schemas.
- **System prompt** — the exact system prompt used in production.
- **Example run transcript** — an annotated example of a complete agent execution.
- **Output schema** — the Pydantic model defining the agent's structured output.
- **Performance targets** — SLOs specific to this agent.

---

## 2. Planning Agent

### 2.1 Purpose

The Planning Agent is the first agent invoked for every incident. Its job is to understand the incident, retrieve relevant historical context, and produce a structured investigation plan that directs all subsequent agents. It acts as the investigative director—it does not gather evidence itself but decides who should gather what.

### 2.2 Trigger Conditions

- Fired immediately upon incident creation (status transitions to `investigating`).
- Re-fired if an investigation is manually restarted.
- Re-fired if the RCA confidence score is below 60 and a human requests a deeper investigation.

### 2.3 Tools

#### `search_similar_incidents`
Performs vector similarity search over resolved incidents in the learning store.

```json
{
  "name": "search_similar_incidents",
  "description": "Search for past incidents that are semantically similar to the current incident. Returns the most relevant resolved incidents with their root causes and resolutions.",
  "parameters": {
    "query": {
      "type": "string",
      "description": "Natural language description of the incident symptoms to search for. Include service name, error types, and observable symptoms."
    },
    "k": {
      "type": "integer",
      "description": "Number of similar incidents to retrieve. Default 5, max 10.",
      "default": 5
    },
    "min_similarity": {
      "type": "number",
      "description": "Minimum cosine similarity threshold (0.0 to 1.0). Default 0.75.",
      "default": 0.75
    }
  },
  "required": ["query"]
}
```

#### `get_service_metadata`
Retrieves service registry information including owner, dependencies, and SLO thresholds.

```json
{
  "name": "get_service_metadata",
  "description": "Retrieve metadata for a service from the service registry. Returns owner team, on-call contact, downstream dependencies, upstream dependents, SLO targets, and infrastructure identifiers.",
  "parameters": {
    "service_name": {
      "type": "string",
      "description": "The canonical service name as registered in the service catalog."
    }
  },
  "required": ["service_name"]
}
```

#### `get_runbook`
Retrieves an existing runbook for a service or incident type if one exists.

```json
{
  "name": "get_runbook",
  "description": "Retrieve an existing runbook for a service or symptom pattern. Returns structured runbook steps if found, or null if no runbook exists.",
  "parameters": {
    "service_name": {
      "type": "string",
      "description": "The service name to look up runbooks for."
    },
    "symptom_keywords": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Optional list of symptom keywords to narrow runbook search (e.g., ['OOMKill', 'CrashLoopBackOff', 'high_latency'])."
    }
  },
  "required": ["service_name"]
}
```

#### `get_recent_alert_history`
Retrieves recent alert history for the affected service to identify patterns.

```json
{
  "name": "get_recent_alert_history",
  "description": "Retrieve the alert history for a service over the past 30 days. Useful for identifying recurring incidents or escalating patterns.",
  "parameters": {
    "service_name": {
      "type": "string",
      "description": "The service name."
    },
    "days_back": {
      "type": "integer",
      "description": "How many days of history to retrieve. Default 30, max 90.",
      "default": 30
    }
  },
  "required": ["service_name"]
}
```

### 2.4 System Prompt

```
You are the Planning Agent for Atlas AI, an autonomous incident investigation system.

Your role is to analyze an incoming production incident and produce a structured investigation plan that will direct a team of specialized agents.

## Your Responsibilities
1. Understand the incident: parse the title, severity, affected service, alerting metrics, and any initial context.
2. Retrieve similar past incidents using the search_similar_incidents tool.
3. Retrieve service metadata to understand dependencies and infrastructure.
4. Check for an existing runbook.
5. Formulate 3-5 specific hypotheses about what might be causing this incident.
6. Decide which specialist agents to invoke and in what order (parallel where possible, sequential where evidence from one agent is needed by another).
7. Define the relevant time window for investigation (typically: 2 hours before incident start to present).

## Available Specialist Agents
- kubernetes_agent: Pod health, resource limits, OOMKills, CrashLoops, deployment events
- github_agent: Recent code changes, deployments, CI failures
- storage_agent: Database slow queries, connection pools, replication lag, disk usage
- network_agent: Load balancer health, DNS, CDN, inter-service connectivity
- security_agent: IAM changes, anomalous access, secret rotation, WAF events
- cost_agent: Cloud spend anomalies, resource cost impact

## Investigation Plan Format
Produce your investigation plan as a JSON object matching the InvestigationPlan schema. Think step by step before writing the JSON. Explain your reasoning in the "reasoning" field.

## Rules
- Do not speculate without evidence. If you have no basis for a hypothesis, do not include it.
- Always invoke at least kubernetes_agent and github_agent for any service incident.
- If the incident involves data anomalies, always include storage_agent.
- If the incident started within 30 minutes of a deployment, prioritize github_agent.
- If the alert is cost-related, lead with cost_agent.
- Set the investigation time window to cover at least 2 hours before the incident start time.
- If a matching runbook exists, include its steps in the plan as a reference — but still run the full investigation; runbooks can be outdated.

## Similar Incident Examples
{similar_incidents_block}
```

### 2.5 Example Run Transcript

```
INCIDENT: payment-service high error rate — P1
Severity: P1
Service: payment-service
Alert: error_rate > 5% for 3 minutes
Started: 2025-01-15T03:42:00Z

--- Planning Agent begins ---

THOUGHT: This is a P1 incident on payment-service. Error rate > 5% is critical. I should start by searching for similar past incidents, then get service metadata, and check for a runbook.

ACTION: search_similar_incidents
INPUT: {"query": "payment-service high error rate 5xx errors spike", "k": 5}
OBSERVATION: Found 3 similar incidents:
  1. [2024-11-22] payment-service 8% error rate — Root cause: PostgreSQL connection pool exhausted after traffic spike. Fixed by increasing max_connections and adding connection pooling via PgBouncer. Similarity: 0.89
  2. [2024-09-10] payment-service elevated latency — Root cause: New deployment introduced N+1 query. Rolled back. Similarity: 0.82
  3. [2024-07-03] payment-service 503 errors — Root cause: Redis session store OOM, pod evicted. Fixed by increasing Redis memory limit. Similarity: 0.77

THOUGHT: Three similar past incidents. Two involve database issues, one involves Redis. I should prioritize the storage and kubernetes agents. Also need to check if there was a recent deployment.

ACTION: get_service_metadata
INPUT: {"service_name": "payment-service"}
OBSERVATION: {
  "owner_team": "payments-platform",
  "on_call": "pagerduty:payments-platform-pd",
  "kubernetes": {"namespace": "payments", "deployment": "payment-service", "replicas": 6},
  "databases": [{"type": "postgresql", "id": "pg-payments-prod", "host": "pg-payments.internal"}],
  "cache": [{"type": "redis", "id": "redis-sessions-prod"}],
  "dependencies": ["fraud-service", "ledger-service", "notification-service"],
  "slo": {"error_rate_threshold": 0.01, "latency_p99_ms": 500}
}

THOUGHT: Payment service has a PostgreSQL database and Redis cache. Six replicas in the 'payments' namespace. I now have enough context to check the runbook.

ACTION: get_runbook
INPUT: {"service_name": "payment-service", "symptom_keywords": ["high_error_rate", "5xx"]}
OBSERVATION: Found runbook: "payment-service-high-error-rate-runbook"
  Step 1: Check pod restart counts (kubectl get pods -n payments)
  Step 2: Check PostgreSQL connection pool utilization
  Step 3: Check for recent deployments in last 2 hours
  Step 4: Check Redis memory usage
  Last updated: 2024-08-15

THOUGHT: Runbook exists but is 5 months old — I'll use it as reference but run full investigation. Based on similar incidents and runbook, my top hypotheses are:
  H1: PostgreSQL connection pool exhausted (most similar to incident #1, similarity 0.89)
  H2: Recent bad deployment (similar to incident #2)
  H3: Redis OOM (similar to incident #3)
  H4: Downstream dependency failure causing cascading errors
  H5: Traffic spike exceeding pod capacity

Investigation time window: 2025-01-15T01:42:00Z to 2025-01-15T03:52:00Z (2h before + 10min buffer)

Agent dispatch order:
  Parallel group 1: kubernetes_agent, github_agent (no dependencies between them)
  Parallel group 2: storage_agent (needs k8s findings for pod names; wait for group 1)
  Sequential: network_agent if no root cause found after group 2
  Sequential: security_agent only if IAM/secret changes suspected

FINAL OUTPUT:
{
  "incident_id": "inc_01HX4KQRS7",
  "hypotheses": [
    {"id": "H1", "description": "PostgreSQL connection pool exhausted", "confidence": 0.45, "basis": "High similarity (0.89) to incident 2024-11-22"},
    {"id": "H2", "description": "Recent deployment introduced regression", "confidence": 0.30, "basis": "High similarity (0.82) to incident 2024-09-10"},
    {"id": "H3", "description": "Redis OOM causing session failures", "confidence": 0.15, "basis": "Moderate similarity (0.77) to incident 2024-07-03"},
    {"id": "H4", "description": "Downstream dependency failure cascade", "confidence": 0.07, "basis": "General distributed systems failure pattern"},
    {"id": "H5", "description": "Traffic spike exceeding pod capacity", "confidence": 0.03, "basis": "Runbook step 4 suggests checking"}
  ],
  "agent_dispatch": [
    {"group": 1, "agents": ["kubernetes_agent", "github_agent"], "parallel": true},
    {"group": 2, "agents": ["storage_agent"], "parallel": false, "depends_on_group": 1},
    {"group": 3, "agents": ["network_agent"], "parallel": false, "condition": "if_no_root_cause_after_group_2"}
  ],
  "time_window": {"start": "2025-01-15T01:42:00Z", "end": "2025-01-15T03:52:00Z"},
  "reasoning": "Top hypothesis is PostgreSQL connection pool based on high similarity to Nov 2024 incident. Will confirm with storage_agent after kubernetes_agent establishes pod state.",
  "runbook_reference": "payment-service-high-error-rate-runbook"
}
```

### 2.6 Output Schema

```python
class Hypothesis(BaseModel):
    id: str                    # e.g., "H1", "H2"
    description: str           # Human-readable hypothesis statement
    confidence: float          # 0.0 to 1.0
    basis: str                 # Explanation of why this hypothesis was formed

class AgentDispatchGroup(BaseModel):
    group: int                 # Execution order (1 = first)
    agents: List[str]          # Agent names to invoke in this group
    parallel: bool             # True = invoke all agents simultaneously
    depends_on_group: Optional[int]  # Wait for this group to complete first
    condition: Optional[str]   # Only invoke if this condition is met

class InvestigationPlan(BaseModel):
    incident_id: str
    hypotheses: List[Hypothesis]
    agent_dispatch: List[AgentDispatchGroup]
    time_window: Dict[str, str]   # {"start": ISO8601, "end": ISO8601}
    reasoning: str
    runbook_reference: Optional[str]
    similar_incident_ids: List[str]
```

### 2.7 Performance Targets

| Metric | Target |
|---|---|
| Execution time p50 | < 30 seconds |
| Execution time p99 | < 90 seconds |
| Plan quality score (human eval) | > 4.0 / 5.0 |
| Root cause in hypothesis list | > 95% of resolved incidents |

---

## 3. Kubernetes Agent

### 3.1 Purpose

Investigates the health and behavior of Kubernetes workloads for the affected service. Provides evidence about pod failures, resource exhaustion, configuration drift, and deployment events within the investigation time window.

### 3.2 Trigger Conditions

- Always invoked for any incident involving an application service.
- Invoked as part of Dispatch Group 1 (parallel with GitHub Agent).

### 3.3 Tools

#### `k8s_get_pod_status`
```json
{
  "name": "k8s_get_pod_status",
  "description": "List all pods for a service with their current status, restart counts, age, and last transition time. Essential first step for any Kubernetes investigation.",
  "parameters": {
    "namespace": {"type": "string", "description": "Kubernetes namespace."},
    "selector": {"type": "string", "description": "Label selector, e.g., 'app=payment-service'."},
    "include_terminated": {"type": "boolean", "description": "Include recently terminated pods. Default true.", "default": true}
  },
  "required": ["namespace", "selector"]
}
```

#### `k8s_get_pod_logs`
```json
{
  "name": "k8s_get_pod_logs",
  "description": "Fetch log lines from a specific pod and container. Automatically filters for ERROR, FATAL, WARN, exception, and panic lines unless a custom grep pattern is specified.",
  "parameters": {
    "namespace": {"type": "string"},
    "pod_name": {"type": "string"},
    "container": {"type": "string", "description": "Container name. Omit for single-container pods."},
    "since": {"type": "string", "description": "ISO 8601 timestamp. Fetch logs since this time."},
    "tail_lines": {"type": "integer", "description": "Return last N lines. Default 200, max 2000.", "default": 200},
    "grep_pattern": {"type": "string", "description": "Optional regex pattern to filter log lines."}
  },
  "required": ["namespace", "pod_name", "since"]
}
```

#### `k8s_describe_deployment`
```json
{
  "name": "k8s_describe_deployment",
  "description": "Get full deployment specification including resource requests/limits, environment variables, image tag, rollout strategy, and recent rollout events.",
  "parameters": {
    "namespace": {"type": "string"},
    "name": {"type": "string", "description": "Deployment name."}
  },
  "required": ["namespace", "name"]
}
```

#### `k8s_get_node_metrics`
```json
{
  "name": "k8s_get_node_metrics",
  "description": "Get current CPU, memory, and disk usage for a specific node or all nodes in the cluster.",
  "parameters": {
    "node_name": {"type": "string", "description": "Node name. Pass 'all' to get all nodes."}
  },
  "required": ["node_name"]
}
```

#### `k8s_get_events`
```json
{
  "name": "k8s_get_events",
  "description": "Retrieve Kubernetes events for a namespace filtered by time. Events capture OOMKills, pod evictions, failed scheduling, and other control plane activity.",
  "parameters": {
    "namespace": {"type": "string"},
    "since": {"type": "string", "description": "ISO 8601 timestamp."},
    "event_type": {"type": "string", "enum": ["Warning", "Normal", "all"], "default": "Warning"}
  },
  "required": ["namespace", "since"]
}
```

#### `k8s_get_hpa_status`
```json
{
  "name": "k8s_get_hpa_status",
  "description": "Get HorizontalPodAutoscaler status including current vs desired replicas, scaling events, and current metric values.",
  "parameters": {
    "namespace": {"type": "string"},
    "name": {"type": "string", "description": "HPA name, typically same as deployment name."}
  },
  "required": ["namespace", "name"]
}
```

### 3.4 System Prompt

```
You are the Kubernetes Agent for Atlas AI. Your job is to investigate the health of Kubernetes workloads for a specific service during an incident.

## Investigation Approach
Follow this systematic process:

1. ESTABLISH BASELINE: Call k8s_get_pod_status first. Look for:
   - Pods in CrashLoopBackOff, OOMKilled, Error, or Pending states
   - High restart counts (> 3 in the time window)
   - Missing replicas (fewer running pods than desired)

2. GET EVENTS: Call k8s_get_events for the namespace. Focus on Warning events.
   Look for: OOMKill, BackOff, Failed, Evicted, FailedScheduling

3. READ LOGS: For any pod with restarts or errors, call k8s_get_pod_logs.
   - For OOMKilled pods: look for memory growth patterns before the kill
   - For CrashLoopBackOff: get logs from the last crash
   - Always grep for: "OOMKilled", "panic", "fatal", "OutOfMemory", "connection refused", "timeout"

4. CHECK RESOURCES: Call k8s_describe_deployment to check:
   - Memory/CPU limits vs requests (large gap = risk of OOM)
   - Image tag (note the current version for correlation with GitHub agent)
   - Environment variable configuration

5. CHECK SCALING: Call k8s_get_hpa_status if traffic spikes are suspected.
   Note whether the HPA was at max replicas (indicating it couldn't scale further).

6. NODE HEALTH: Call k8s_get_node_metrics if pod scheduling issues appear.

## Evidence Reporting
For every finding, record:
- The exact timestamp of the event
- The pod name or resource involved
- The specific log line or event message (exact text, not paraphrased)
- Your interpretation

## Rules
- Never fabricate pod names, log lines, or event messages. Report only what the tools return.
- If a tool returns empty results, report that explicitly — absence of evidence is evidence.
- Mark each finding with a confidence level: HIGH (tool returned explicit evidence), MEDIUM (inferred from partial evidence), LOW (suspected but not confirmed).
- Do not suggest remediation steps — that is the RCA Agent's job.

## Output Format
Produce a KubernetesFinding object as your final output. Think out loud step by step as you investigate, then produce the final structured JSON.
```

### 3.5 Example Run Transcript

```
Context: Investigating payment-service, namespace: payments, time_window: 2025-01-15T01:42:00Z to 03:52:00Z

THOUGHT: Starting with pod status to get the overall picture.

ACTION: k8s_get_pod_status
INPUT: {"namespace": "payments", "selector": "app=payment-service", "include_terminated": true}
OBSERVATION: {
  "pods": [
    {"name": "payment-service-7d9f-xk2p9", "status": "Running", "restarts": 0, "age": "2d"},
    {"name": "payment-service-7d9f-mn4r1", "status": "Running", "restarts": 0, "age": "2d"},
    {"name": "payment-service-7d9f-vb8w2", "status": "OOMKilled", "restarts": 4, "age": "2d", "last_restart": "2025-01-15T03:38:00Z"},
    {"name": "payment-service-7d9f-qp5t3", "status": "CrashLoopBackOff", "restarts": 7, "age": "2d", "last_restart": "2025-01-15T03:45:00Z"},
    {"name": "payment-service-7d9f-jl6n4", "status": "Running", "restarts": 1, "age": "2d", "last_restart": "2025-01-15T03:30:00Z"},
    {"name": "payment-service-7d9f-kw7m5", "status": "Terminating", "restarts": 5, "age": "2d"}
  ],
  "desired_replicas": 6, "ready_replicas": 3
}

THOUGHT: 3 of 6 pods are unhealthy. Two OOMKilled/CrashLoopBackOff, one Terminating. This is significant. The cluster is running at 50% capacity which explains the high error rate. Let me get events and logs.

ACTION: k8s_get_events
INPUT: {"namespace": "payments", "since": "2025-01-15T01:42:00Z", "event_type": "Warning"}
OBSERVATION: [
  {"time": "2025-01-15T03:22:00Z", "type": "Warning", "reason": "OOMKilling", "object": "pod/payment-service-7d9f-vb8w2", "message": "Memory limit reached. Limit: 512Mi, Used: 513Mi. Killing."},
  {"time": "2025-01-15T03:28:00Z", "type": "Warning", "reason": "OOMKilling", "object": "pod/payment-service-7d9f-kw7m5", "message": "Memory limit reached. Limit: 512Mi, Used: 514Mi."},
  {"time": "2025-01-15T03:35:00Z", "type": "Warning", "reason": "OOMKilling", "object": "pod/payment-service-7d9f-qp5t3", "message": "Memory limit reached. Limit: 512Mi, Used: 512Mi."},
  {"time": "2025-01-15T03:42:00Z", "type": "Warning", "reason": "BackOff", "object": "pod/payment-service-7d9f-qp5t3", "message": "Back-off restarting failed container"}
]

THOUGHT: Clear OOMKill pattern. Memory limit is 512Mi and pods are hitting it. OOMKills started at 03:22, the incident fired at 03:42 (after enough pods failed to cause error spike). Let me get logs to understand WHY memory is growing.

ACTION: k8s_get_pod_logs
INPUT: {"namespace": "payments", "pod_name": "payment-service-7d9f-vb8w2", "since": "2025-01-15T02:42:00Z", "tail_lines": 500, "grep_pattern": "memory|heap|cache|ERROR|WARN|connection"}
OBSERVATION: [
  "2025-01-15T02:44:01Z WARN heap_size=245MB threshold=80%",
  "2025-01-15T02:58:33Z WARN heap_size=380MB threshold=80% — cache_entries=148291",
  "2025-01-15T03:10:12Z ERROR cache miss rate=0.02% — in-memory cache growing unbounded",
  "2025-01-15T03:18:44Z WARN heap_size=490MB threshold=95% — cache_entries=412008",
  "2025-01-15T03:21:55Z FATAL out of memory — heap_size=513MB limit=512MB"
]

THOUGHT: Found the cause. An in-memory cache is growing unbounded — 412,000 entries at 03:18. This is a memory leak via unbounded cache growth. Let me check the deployment spec to see if there's a cache size limit configured.

ACTION: k8s_describe_deployment
INPUT: {"namespace": "payments", "name": "payment-service"}
OBSERVATION: {
  "image": "payment-service:v2.14.1",
  "resources": {"requests": {"memory": "256Mi", "cpu": "500m"}, "limits": {"memory": "512Mi", "cpu": "2000m"}},
  "env": [
    {"name": "CACHE_MAX_ENTRIES", "value": "0"},
    {"name": "CACHE_TTL_SECONDS", "value": "3600"},
    {"name": "DB_POOL_SIZE", "value": "20"}
  ],
  "replicas": 6, "last_deployed": "2025-01-15T01:15:00Z"
}

THOUGHT: Found it. CACHE_MAX_ENTRIES=0 means NO limit on cache entries. The cache can grow indefinitely. Also note the deployment happened at 01:15 — just before the investigation window starts. The image is v2.14.1 — I should note this for the GitHub agent findings correlation. Let me also check HPA.

ACTION: k8s_get_hpa_status
INPUT: {"namespace": "payments", "name": "payment-service"}
OBSERVATION: {"min_replicas": 6, "max_replicas": 6, "current_replicas": 6, "desired_replicas": 6, "note": "HPA min equals max — no autoscaling configured."}

THOUGHT: HPA min=max=6, so there's no autoscaling possible. The investigation is complete.

FINAL OUTPUT:
{
  "service": "payment-service",
  "namespace": "payments",
  "summary": "Memory leak via unbounded in-memory cache growth. OOMKills caused pod count to drop from 6 to 3, triggering the error rate spike.",
  "findings": [
    {
      "type": "OOMKill",
      "confidence": "HIGH",
      "timestamp": "2025-01-15T03:22:00Z",
      "evidence": "3 pods OOMKilled between 03:22 and 03:42. Memory limit 512Mi consistently exceeded.",
      "affected_resources": ["payment-service-7d9f-vb8w2", "payment-service-7d9f-kw7m5", "payment-service-7d9f-qp5t3"]
    },
    {
      "type": "UnboundedCacheGrowth",
      "confidence": "HIGH",
      "timestamp": "2025-01-15T03:10:12Z",
      "evidence": "Log line: 'cache miss rate=0.02% — in-memory cache growing unbounded'. Cache grew to 412,008 entries before OOMKill.",
      "affected_resources": ["payment-service-7d9f-vb8w2"]
    },
    {
      "type": "MisconfiguredEnvironmentVariable",
      "confidence": "HIGH",
      "timestamp": "2025-01-15T01:15:00Z",
      "evidence": "CACHE_MAX_ENTRIES=0 in deployment spec. Zero value disables cache size limit.",
      "affected_resources": ["payment-service deployment"]
    },
    {
      "type": "RecentDeployment",
      "confidence": "HIGH",
      "timestamp": "2025-01-15T01:15:00Z",
      "evidence": "Deployment of image payment-service:v2.14.1 occurred 2h 27m before first OOMKill.",
      "affected_resources": ["payment-service:v2.14.1"]
    }
  ],
  "healthy_pods": 3,
  "total_pods": 6,
  "capacity_degradation_percent": 50
}
```

### 3.6 Output Schema

```python
class KubernetesFinding(BaseModel):
    service: str
    namespace: str
    summary: str
    findings: List[Dict[str, Any]]  # Each: type, confidence, timestamp, evidence, affected_resources
    healthy_pods: int
    total_pods: int
    capacity_degradation_percent: float
    image_version: Optional[str]
    resource_limits: Optional[Dict[str, str]]
    oom_kills_count: int = 0
    crash_loop_count: int = 0
```

### 3.7 Performance Targets

| Metric | Target |
|---|---|
| Execution time p50 | < 60 seconds |
| Execution time p99 | < 3 minutes |
| Root cause identification rate | > 80% for OOMKill/CrashLoop incidents |
| False positive finding rate | < 5% |

---

## 4. GitHub Agent

### 4.1 Purpose

Correlates the incident timeline with repository activity. Identifies deployments, configuration changes, and code modifications that may have introduced the failure.

### 4.2 Trigger Conditions

- Always invoked in Dispatch Group 1 (parallel with Kubernetes Agent).
- Given extra priority if: incident started within 60 minutes of a deployment, or if the Kubernetes Agent found a recent image change.

### 4.3 Tools

#### `github_list_recent_commits`
```json
{
  "name": "github_list_recent_commits",
  "description": "List recent commits for a repository within a time window. Returns author, message, changed files, and diff statistics.",
  "parameters": {
    "repo": {"type": "string", "description": "Repository in 'owner/repo' format."},
    "branch": {"type": "string", "description": "Branch name. Default 'main'.", "default": "main"},
    "since": {"type": "string", "description": "ISO 8601 timestamp."},
    "until": {"type": "string", "description": "ISO 8601 timestamp."},
    "max_results": {"type": "integer", "default": 20}
  },
  "required": ["repo", "since"]
}
```

#### `github_get_deployment_history`
```json
{
  "name": "github_get_deployment_history",
  "description": "Get deployment events from GitHub Environments for a specific environment and time window.",
  "parameters": {
    "repo": {"type": "string"},
    "environment": {"type": "string", "description": "e.g., 'production', 'staging'."},
    "since": {"type": "string", "description": "ISO 8601 timestamp."},
    "limit": {"type": "integer", "default": 10}
  },
  "required": ["repo", "environment", "since"]
}
```

#### `github_get_pr_diff`
```json
{
  "name": "github_get_pr_diff",
  "description": "Get the full diff for a merged pull request. Analyzes code changes for risk patterns such as cache configuration, database query changes, dependency upgrades.",
  "parameters": {
    "repo": {"type": "string"},
    "pr_number": {"type": "integer"},
    "max_diff_lines": {"type": "integer", "description": "Truncate diff at this many lines. Default 500.", "default": 500}
  },
  "required": ["repo", "pr_number"]
}
```

#### `github_get_failed_checks`
```json
{
  "name": "github_get_failed_checks",
  "description": "List all failed CI/CD checks for a commit SHA.",
  "parameters": {
    "repo": {"type": "string"},
    "sha": {"type": "string", "description": "Full commit SHA."}
  },
  "required": ["repo", "sha"]
}
```

#### `github_search_code`
```json
{
  "name": "github_search_code",
  "description": "Search for a code pattern in a repository. Useful for finding configuration values, environment variable usage, or API call patterns.",
  "parameters": {
    "repo": {"type": "string"},
    "query": {"type": "string", "description": "Search query using GitHub code search syntax."},
    "ref": {"type": "string", "description": "Git ref (branch, tag, or SHA) to search at."}
  },
  "required": ["repo", "query"]
}
```

### 4.4 System Prompt

```
You are the GitHub Agent for Atlas AI. Your job is to investigate repository activity that may be causally related to a production incident.

## Investigation Approach

1. GET DEPLOYMENTS: Start with github_get_deployment_history for the production environment.
   Note: Did any deployment occur within 2 hours of the incident start? This is the highest-priority signal.

2. GET RECENT COMMITS: Call github_list_recent_commits for the 4-hour window ending at incident start.
   Focus on: configuration file changes, dependency version bumps, environment variable changes, caching logic changes.

3. ANALYZE HIGH-RISK COMMITS: For any commit that touches infrastructure config, dependencies, or the service being investigated, call github_get_pr_diff to review the actual changes.

4. CHECK CI STATUS: For the most recent deployment commit, call github_get_failed_checks. Any failing test that was bypassed to deploy is highly significant.

5. CODE SEARCH (if specific patterns are needed): If Kubernetes findings mention a specific config value or code path, use github_search_code to locate it in the codebase.

## What to Look For
- Configuration changes that could affect resource limits (memory, cache sizes, connection pools)
- Dependency version bumps (new library versions may have memory leaks or behavior changes)
- Database query changes (new queries, removed indexes, ORM changes)
- Feature flag changes that enable new code paths
- Environment variable renaming or removal
- Any change to cache, queue, or session handling code

## Deployment Correlation Rule
If a deployment occurred within 120 minutes before incident start: mark as HIGH CONFIDENCE causal candidate.
If a deployment occurred between 2-6 hours before: mark as MEDIUM CONFIDENCE.
If no deployment in 6+ hours: mark code changes as LOW CONFIDENCE causal candidate.

## Output Format
Produce a GitHubFinding object. Quote specific diff lines when they are directly relevant — do not paraphrase code changes.
```

### 4.5 Output Schema

```python
class CommitSummary(BaseModel):
    sha: str
    author: str
    message: str
    timestamp: str
    risk_level: str  # "high", "medium", "low"
    risk_reason: str
    pr_number: Optional[int]

class GitHubFinding(BaseModel):
    service: str
    repo: str
    summary: str
    recent_deployments: List[Dict[str, Any]]
    causal_candidate_commits: List[CommitSummary]
    deployment_correlation: str   # "high", "medium", "low", "none"
    minutes_since_last_deploy: Optional[int]
    failed_ci_checks: List[str]
    relevant_diff_excerpts: List[str]
```

### 4.6 Performance Targets

| Metric | Target |
|---|---|
| Execution time p50 | < 45 seconds |
| Execution time p99 | < 2 minutes |
| Deployment correlation accuracy | > 90% (when deployment is causal) |

---

## 5. Storage Agent

### 5.1 Purpose

Investigates database and object storage health. Identifies slow queries, connection exhaustion, replication lag, and disk pressure that may be causing or contributing to application errors.

### 5.2 Trigger Conditions

- Invoked in Dispatch Group 2 (after Kubernetes Agent completes, to use pod/service metadata).
- Given extra priority if: Kubernetes findings show database connection errors, or if Planning Agent hypothesis H1 is database-related.

### 5.3 Tools

| Tool | Description |
|---|---|
| `db_get_slow_queries(db_id, since, threshold_ms)` | Queries from pg_stat_statements exceeding threshold |
| `db_get_connection_pool_stats(db_id)` | Active, idle, waiting, max connections |
| `db_get_replication_lag(db_id)` | Lag in bytes and seconds per replica |
| `db_get_table_bloat(db_id, schema)` | Table and index bloat statistics |
| `db_explain_query(db_id, query_hash)` | EXPLAIN ANALYZE for a slow query hash |
| `db_get_lock_waits(db_id, since)` | Lock wait events and blocking queries |
| `s3_get_bucket_metrics(bucket, since)` | S3/GCS request rates, error rates, latency |
| `db_get_vacuum_status(db_id)` | Last vacuum/analyze timestamps, dead tuple counts |

### 5.4 System Prompt

```
You are the Storage Agent for Atlas AI. Your job is to investigate database and object storage health for a service experiencing a production incident.

## Investigation Process
1. Start with connection pool stats — exhausted pools cause immediate application errors.
2. Check slow queries — queries suddenly getting slower indicate plan changes or missing indexes.
3. Check replication lag — high lag causes read replica queries to return stale data.
4. If lock waits are present, identify the blocking query.
5. Check table bloat if the database is old or vacuum jobs are failing.
6. For S3/GCS: check error rates and latency spikes.

## Key Thresholds
- Connection pool > 90% utilized: HIGH severity
- Slow query threshold crossing: any query taking >10x its baseline is HIGH severity
- Replication lag > 30 seconds: HIGH severity
- Table bloat > 50%: MEDIUM severity (likely not immediate cause)

## Output Format
Produce a StorageFinding object with all evidence cited from tool outputs.
```

### 5.5 Output Schema

```python
class StorageFinding(BaseModel):
    service: str
    databases_checked: List[str]
    summary: str
    connection_pool_status: Dict[str, Any]  # utilization%, active, idle, waiting
    slow_queries: List[Dict[str, Any]]      # query hash, duration_ms, calls, query text
    replication_lag_seconds: Optional[float]
    lock_wait_events: List[Dict[str, Any]]
    s3_findings: Optional[Dict[str, Any]]
    severity: str  # "critical", "high", "medium", "low", "healthy"
```

### 5.6 Performance Targets

| Metric | Target |
|---|---|
| Execution time p50 | < 90 seconds |
| Execution time p99 | < 4 minutes |

---

## 6. Network Agent

### 6.1 Purpose

Investigates network-layer failures: DNS resolution issues, load balancer health, CDN problems, and inter-service connectivity failures.

### 6.2 Trigger Conditions

- Invoked conditionally after initial agents if no root cause is found.
- Always invoked for incidents involving 502/503/504 HTTP errors.
- Always invoked for incidents with "connection refused" or "timeout" errors in logs.

### 6.3 Tools

| Tool | Description |
|---|---|
| `network_get_lb_metrics(lb_id, since)` | ALB/NLB: request count, 5xx rate, latency p50/p95/p99 |
| `network_check_dns(hostname)` | Current DNS resolution with TTL |
| `network_get_service_mesh_stats(service, since)` | Istio/Linkerd: success rate, latency, retries |
| `network_get_cdn_stats(domain, since)` | CDN: cache hit rate, origin error rate, latency |
| `network_check_connectivity(source_service, target_service)` | Reachability test (curl equivalent) |
| `network_get_tls_cert_status(hostname)` | TLS cert expiry and validity |

### 6.4 System Prompt

```
You are the Network Agent for Atlas AI. Investigate network-layer infrastructure for signs of failure contributing to the incident.

Start with the load balancer metrics (high 5xx at the LB = likely application issue; high 5xx with normal request count = possible backend failure). Check DNS if connectivity issues are suspected. Verify TLS cert validity — expired certs cause silent failures. If a service mesh is in use, check success rates and retry storms (high retry count suggests intermittent failures masked to the application).

Report every finding with the exact metric value, timestamp, and direction of change.
```

### 6.5 Output Schema

```python
class NetworkFinding(BaseModel):
    service: str
    summary: str
    lb_error_rate_percent: Optional[float]
    lb_latency_p99_ms: Optional[float]
    dns_healthy: Optional[bool]
    tls_cert_days_until_expiry: Optional[int]
    service_mesh_success_rate: Optional[float]
    cdn_origin_error_rate: Optional[float]
    connectivity_failures: List[str]
    severity: str
```

### 6.6 Performance Targets

| Metric | Target |
|---|---|
| Execution time p50 | < 60 seconds |
| Execution time p99 | < 3 minutes |

---

## 7. Security Agent

### 7.1 Purpose

Looks for security-related events that may have caused the incident or resulted from it: IAM changes, secret rotation, anomalous API access patterns, WAF events, and pod security violations.

### 7.2 Trigger Conditions

- Invoked conditionally if: Planning Agent raises a security hypothesis, or if Kubernetes/GitHub agents find unusual access patterns.
- Always invoked for incidents classified as `security` type.

### 7.3 Tools

| Tool | Description |
|---|---|
| `security_get_cloudtrail_events(role, since)` | AWS CloudTrail / GCP Audit Log events for a service role |
| `security_scan_access_logs(service, since)` | Anomalous request patterns (new IPs, unusual UA, high rate) |
| `security_get_secret_rotation_events(secret_id, since)` | Secret rotation history from Vault/AWS Secrets Manager |
| `security_check_pod_security(namespace, pod_name)` | PSA violations, privileged containers, host path mounts |
| `security_get_waf_events(since)` | WAF allow/block decisions |
| `security_scan_for_exposed_secrets(repo, sha)` | Git history scan for accidentally committed credentials |

### 7.4 System Prompt

```
You are the Security Agent for Atlas AI. Investigate security events that may be causally related to the incident.

Focus on: IAM permission changes (especially removal of required permissions), secret rotation events (if a secret was rotated and the application was not restarted), anomalous access patterns (DDoS, credential stuffing), and pod security context violations.

IMPORTANT: You are operating in read-only mode. You cannot change IAM policies, revoke tokens, or block IPs. Document findings only. Flag any finding that appears to be an active security incident as CRITICAL — this will trigger a separate security incident workflow.

Never include actual secret values in your output even if they appear in tool outputs. Replace any credential-looking strings with [REDACTED].
```

### 7.5 Output Schema

```python
class SecurityFinding(BaseModel):
    service: str
    summary: str
    iam_changes: List[Dict[str, Any]]
    secret_rotation_events: List[Dict[str, Any]]
    anomalous_access_events: List[Dict[str, Any]]
    pod_security_violations: List[Dict[str, Any]]
    active_security_incident_suspected: bool
    severity: str
```

### 7.6 Performance Targets

| Metric | Target |
|---|---|
| Execution time p50 | < 60 seconds |
| Execution time p99 | < 3 minutes |
| False positive security alert rate | < 1% |

---

## 8. RCA Agent

### 8.1 Purpose

The RCA Agent is the synthesis engine. It receives the complete investigation context from all prior agents and produces a single, authoritative Root Cause Analysis with a causal chain, confidence score, and ordered remediation proposals.

### 8.2 Trigger Conditions

- Invoked after all dispatched investigation agents have completed (or timed out after 10 minutes).
- Has access to the full investigation context, including all agent findings and the original investigation plan.

### 8.3 Tools

The RCA Agent has no external tools. It reasons exclusively over the accumulated investigation context. This is intentional: by the time the RCA Agent runs, all evidence has been gathered. Giving it tools could cause it to chase irrelevant details.

### 8.4 System Prompt

```
You are the RCA Agent for Atlas AI. You receive findings from multiple specialist agents and synthesize them into a definitive Root Cause Analysis.

## Your Task
Analyze all provided agent findings and produce a single, authoritative RCA that:
1. States the root cause clearly and specifically (not "database issues" but "PostgreSQL connection pool exhausted due to CACHE_MAX_ENTRIES=0 causing unbounded memory growth in payment-service v2.14.1")
2. Provides a timeline of events from first symptom to full impact
3. Identifies contributing factors (not root causes, but things that made the incident worse)
4. Proposes specific remediation actions ordered by urgency
5. Assigns a confidence score (0-100)

## Confidence Scoring Guidelines
- 90-100: Root cause confirmed by multiple independent evidence sources
- 70-89: Root cause supported by strong evidence from 2+ agents
- 50-69: Root cause is the most likely explanation but some uncertainty remains
- 30-49: Hypothesis only — evidence is circumstantial or incomplete
- 0-29: Very low confidence — insufficient data; recommend deeper investigation

## Causal Chain Requirements
Every causal chain must have this structure:
  [Trigger] → [Mechanism] → [Immediate Impact] → [User-Visible Symptom]

Example: "CACHE_MAX_ENTRIES=0 deployed (trigger) → unbounded cache grew to 412K entries (mechanism) → pod memory exceeded 512Mi limit, OOMKilled (immediate impact) → 3/6 replicas offline causing 503 errors (user-visible symptom)"

## Remediation Action Schema
Each remediation action must include:
- action_id: unique identifier
- priority: 1 (immediate), 2 (urgent), 3 (important), 4 (improvement)
- title: one-line description
- steps: ordered list of specific commands or actions
- risk_level: "low", "medium", "high"
- rollback_procedure: what to do if this action makes things worse
- estimated_time_minutes: how long this will take

## Rules
- If agent findings contradict each other, acknowledge the contradiction and explain which evidence you weighted more heavily and why.
- If confidence is below 50, state what additional investigation would be needed.
- Do not propose remediation actions with risk_level "high" unless they are clearly necessary. Always provide a safer lower-risk alternative if one exists.
- The RCA must be explainable to a non-technical stakeholder in the executive_summary field.
- Never recommend actions that require production database schema changes without including a full rollback plan.

## Agent Findings Context
{agent_findings_block}
```

### 8.5 Example Output

```json
{
  "incident_id": "inc_01HX4KQRS7",
  "root_cause": "Deployment of payment-service v2.14.1 introduced CACHE_MAX_ENTRIES=0 environment variable, disabling the in-memory cache size limit and causing unbounded memory growth until OOMKill.",
  "causal_chain": "CACHE_MAX_ENTRIES=0 set in v2.14.1 deployment (01:15 UTC) → in-memory cache grew to 412,008 entries over 2 hours → pod RSS memory reached 513Mi (limit: 512Mi) → Kubernetes OOMKilled 3/6 pods (03:22-03:42 UTC) → 50% capacity loss caused 5xx error rate to exceed 5% (03:42 UTC)",
  "confidence_score": 94,
  "contributing_factors": [
    "Memory limit of 512Mi is low relative to normal heap usage of 245Mi — only 267Mi headroom for cache",
    "No autoscaling configured (HPA min=max=6) — surviving pods could not compensate for lost capacity",
    "No canary deployment — change was applied to all 6 pods simultaneously"
  ],
  "timeline": [
    {"time": "2025-01-15T01:15:00Z", "event": "Deployment of payment-service:v2.14.1 to production"},
    {"time": "2025-01-15T02:44:00Z", "event": "Heap size warning threshold (80%) triggered"},
    {"time": "2025-01-15T03:10:00Z", "event": "Log: 'in-memory cache growing unbounded', 148,291 entries"},
    {"time": "2025-01-15T03:22:00Z", "event": "First OOMKill: payment-service-7d9f-vb8w2"},
    {"time": "2025-01-15T03:38:00Z", "event": "Second and third OOMKills"},
    {"time": "2025-01-15T03:42:00Z", "event": "PagerDuty alert fires — error rate 5.3%"}
  ],
  "remediation_actions": [
    {
      "action_id": "REM-001",
      "priority": 1,
      "title": "Set CACHE_MAX_ENTRIES=10000 and roll out deployment",
      "steps": [
        "kubectl set env deployment/payment-service CACHE_MAX_ENTRIES=10000 -n payments",
        "kubectl rollout status deployment/payment-service -n payments --timeout=5m",
        "Monitor error_rate metric — should drop within 2 minutes of rollout completion"
      ],
      "risk_level": "low",
      "rollback_procedure": "kubectl rollout undo deployment/payment-service -n payments",
      "estimated_time_minutes": 5
    },
    {
      "action_id": "REM-002",
      "priority": 2,
      "title": "Increase memory limit to 1Gi to provide safer headroom",
      "steps": [
        "Edit deployment resource limits: memory limit from 512Mi to 1Gi",
        "kubectl apply -f updated-deployment.yaml -n payments",
        "Verify all 6 pods restart and reach Running state"
      ],
      "risk_level": "low",
      "rollback_procedure": "kubectl rollout undo deployment/payment-service -n payments",
      "estimated_time_minutes": 10
    },
    {
      "action_id": "REM-003",
      "priority": 3,
      "title": "Add pre-deployment validation check for CACHE_MAX_ENTRIES",
      "steps": [
        "Add GitHub Actions check: fail if CACHE_MAX_ENTRIES is unset or 0",
        "Update deployment checklist to include cache configuration review"
      ],
      "risk_level": "low",
      "rollback_procedure": "N/A — prevention measure",
      "estimated_time_minutes": 60
    }
  ],
  "executive_summary": "A configuration error in the v2.14.1 deployment caused the payment service's memory cache to grow without limit, consuming all available memory and crashing half the service's servers. The fix is a one-line configuration change that takes 5 minutes to apply.",
  "requires_human_approval": true,
  "approval_urgency": "P1 — apply within 15 minutes to restore full capacity"
}
```

### 8.6 Output Schema

```python
class RemediationAction(BaseModel):
    action_id: str
    priority: int
    title: str
    steps: List[str]
    risk_level: str
    rollback_procedure: str
    estimated_time_minutes: int

class TimelineEvent(BaseModel):
    time: str
    event: str

class RCAReport(BaseModel):
    incident_id: str
    root_cause: str
    causal_chain: str
    confidence_score: int
    contributing_factors: List[str]
    timeline: List[TimelineEvent]
    remediation_actions: List[RemediationAction]
    executive_summary: str
    requires_human_approval: bool
    approval_urgency: str
```

### 8.7 Performance Targets

| Metric | Target |
|---|---|
| Execution time p50 | < 90 seconds |
| Execution time p99 | < 4 minutes |
| Average confidence score | > 80 |
| Human override rate (RCA found incorrect) | < 10% |
| Root cause accuracy (human validation) | > 90% |

---

## 9. Documentation Agent

### 9.1 Purpose

Converts the structured RCA into human-readable documents published to the team's collaboration tools (Confluence, Jira, Slack). Eliminates the manual toil of post-incident write-up.

### 9.2 Trigger Conditions

- Invoked after RCA Agent completes and human approval is received.
- Also invoked if an engineer explicitly requests documentation generation.

### 9.3 Tools

| Tool | Description |
|---|---|
| `confluence_create_page(space_key, title, parent_page_id, body_html)` | Creates a Confluence page with formatted incident report |
| `confluence_update_page(page_id, body_html, version)` | Updates an existing page |
| `jira_update_ticket(ticket_id, fields)` | Updates Jira issue with resolution, root cause label, time-to-resolve |
| `jira_create_followup_ticket(project, summary, description, parent_id)` | Creates follow-up action items for prevention measures |
| `slack_post_message(channel, blocks)` | Posts structured Slack message with incident summary |
| `pagerduty_resolve_incident(incident_id, resolution_note)` | Marks PagerDuty incident as resolved with note |

### 9.4 System Prompt

```
You are the Documentation Agent for Atlas AI. Your job is to create polished, professional incident documentation from a structured RCA report.

## Document Standards

### Confluence Page Structure
Every incident report page must follow this structure:
  1. Incident Overview (severity, dates, duration, impact summary)
  2. Timeline of Events (chronological, use table format)
  3. Root Cause Analysis (root cause statement, causal chain, confidence score)
  4. Impact Assessment (services affected, users affected, financial impact if known)
  5. Remediation Actions Taken (what was done, when, by whom)
  6. Contributing Factors
  7. Prevention Measures (follow-up action items with owners and due dates)
  8. Lessons Learned

### Jira Update
Update the incident ticket with:
  - Resolution: brief root cause statement
  - Labels: add label matching root cause category (e.g., "configuration-error", "memory-leak", "deployment-regression")
  - Time to Detect, Time to Resolve (calculated from timestamps)
  - Link to Confluence page

### Slack Summary
Write a Slack message with three sections:
  1. :red_circle: RESOLVED — one-line incident summary
  2. Root Cause: clear explanation
  3. Prevention: what is being done so this does not happen again

## Tone
- Professional but accessible. Avoid jargon where plain language works.
- Do not assign blame to individuals. Focus on systems and processes.
- Be honest about confidence levels — if the RCA is 75% confident, say so.

## Output
Produce a DocumentationResult with URLs and confirmation of all documents created.
```

### 9.5 Output Schema

```python
class DocumentationResult(BaseModel):
    confluence_page_url: Optional[str]
    jira_ticket_url: Optional[str]
    slack_message_ts: Optional[str]
    pagerduty_resolved: bool
    followup_tickets_created: List[str]
    documents_created: List[str]
```

### 9.6 Performance Targets

| Metric | Target |
|---|---|
| Execution time p50 | < 60 seconds |
| Documentation quality score (human eval) | > 4.0 / 5.0 |
| All follow-up tickets created within 2 hours of resolution | > 95% |

---

## 10. Cost Agent

### 10.1 Purpose

Quantifies the financial impact of the incident (cost of downtime) and identifies unusual cloud spend patterns that may be causally related to the incident.

### 10.2 Trigger Conditions

- Invoked in parallel with RCA Agent to enrich the RCA with cost data.
- Given primary dispatch if the incident alert is cost-related (e.g., AWS Cost Anomaly Detection alert).

### 10.3 Tools

| Tool | Description |
|---|---|
| `cost_get_service_spend(service, since, until)` | Per-service daily cloud spend breakdown |
| `cost_get_anomaly_events(account_id, since)` | AWS Cost Anomaly Detection / GCP Budget alert events |
| `cost_get_resource_utilization(resource_id, since)` | Actual vs billed resource utilization |
| `cost_estimate_incident_impact(incident_id, downtime_minutes, error_rate)` | Estimates revenue/SLA impact from downtime |
| `cost_get_rightsizing_recommendations(service)` | AWS Compute Optimizer / GCP recommendations |

### 10.4 System Prompt

```
You are the Cost Agent for Atlas AI. Your job is to quantify the financial dimension of the incident.

Calculate:
1. Cloud infrastructure cost during the incident period (was spending higher or lower than baseline?)
2. Estimated revenue impact of downtime (if SLA and revenue data are available)
3. Any cost anomalies in the 24 hours preceding the incident (unusual spend often signals runaway resources)

If the incident was caused by a runaway process (like an unbounded cache), calculate the extra infrastructure cost attributable to that process.

Format all costs in USD with appropriate precision ($1,234 for large amounts, $12.34 for small amounts). Include a 30-day baseline for comparison.

Produce a CostFinding object.
```

### 10.5 Output Schema

```python
class CostFinding(BaseModel):
    service: str
    incident_period_spend_usd: float
    baseline_period_spend_usd: float
    spend_delta_percent: float
    estimated_revenue_impact_usd: Optional[float]
    cost_anomaly_events: List[Dict[str, Any]]
    runaway_resource_cost_usd: Optional[float]
    rightsizing_opportunity_usd_monthly: Optional[float]
    summary: str
```

### 10.6 Performance Targets

| Metric | Target |
|---|---|
| Execution time p50 | < 45 seconds |
| Cost estimation accuracy | ± 20% of actual (validated monthly) |
