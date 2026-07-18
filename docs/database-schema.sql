-- Atlas AI Database Schema
-- PostgreSQL 16 with pgvector extension
-- Version: 1.0.0
-- Last Updated: 2025-01-01

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Custom types
CREATE TYPE incident_severity AS ENUM ('P1', 'P2', 'P3', 'P4');
CREATE TYPE incident_status AS ENUM ('created', 'investigating', 'rca_complete', 'awaiting_approval', 'remediating', 'resolved', 'archived');
CREATE TYPE agent_type AS ENUM ('planning', 'kubernetes', 'github', 'storage', 'network', 'security', 'rca', 'documentation', 'cost');
CREATE TYPE agent_run_status AS ENUM ('running', 'completed', 'failed', 'timeout');
CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high');

-- ============================================================================
-- INCIDENTS TABLE
-- ============================================================================
CREATE TABLE incidents (
    id TEXT PRIMARY KEY DEFAULT 'inc_' || encode(gen_random_bytes(12), 'hex'),
    title TEXT NOT NULL,
    severity incident_severity NOT NULL,
    status incident_status NOT NULL DEFAULT 'created',
    service_name TEXT NOT NULL,
    alert_name TEXT,
    description TEXT,
    external_id TEXT UNIQUE,  -- PagerDuty/Jira ID for deduplication
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    
    -- Investigation tracking
    investigation_id TEXT,
    rca_id TEXT,
    
    -- Metrics
    mttr_seconds INTEGER,  -- Mean Time To Resolve
    mttd_seconds INTEGER,  -- Mean Time To Detect
    
    -- Constraints
    CONSTRAINT valid_severity CHECK (severity IN ('P1', 'P2', 'P3', 'P4')),
    CONSTRAINT valid_resolved_at CHECK (resolved_at IS NULL OR resolved_at >= created_at)
);

-- Indexes
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_service_name ON incidents(service_name);
CREATE INDEX idx_incidents_created_at ON incidents(created_at DESC);
CREATE INDEX idx_incidents_external_id ON incidents(external_id) WHERE external_id IS NOT NULL;
CREATE INDEX idx_incidents_metadata ON incidents USING GIN(metadata);

-- GIN index for JSONB queries
CREATE INDEX idx_incidents_metadata_service ON incidents((metadata->>'pagerduty_service_id'));

-- ============================================================================
-- AGENT_RUNS TABLE
-- ============================================================================
CREATE TABLE agent_runs (
    id TEXT PRIMARY KEY DEFAULT 'run_' || encode(gen_random_bytes(12), 'hex'),
    incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    agent_type agent_type NOT NULL,
    status agent_run_status NOT NULL DEFAULT 'running',
    
    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds NUMERIC(10,3),
    
    -- Execution data
    input_context JSONB,  -- Input parameters passed to the agent
    tool_calls JSONB DEFAULT '[]'::jsonb,  -- Array of tool call records
    findings JSONB,  -- Structured output from the agent
    error_message TEXT,
    
    -- Performance metrics
    llm_calls_count INTEGER DEFAULT 0,
    llm_tokens_total INTEGER DEFAULT 0,
    llm_cost_usd NUMERIC(10,4) DEFAULT 0,
    
    -- Constraints
    CONSTRAINT valid_duration CHECK (completed_at IS NULL OR duration_seconds >= 0)
);

-- Indexes
CREATE INDEX idx_agent_runs_incident_id ON agent_runs(incident_id);
CREATE INDEX idx_agent_runs_agent_type ON agent_runs(agent_type);
CREATE INDEX idx_agent_runs_status ON agent_runs(status);
CREATE INDEX idx_agent_runs_started_at ON agent_runs(started_at DESC);
CREATE INDEX idx_agent_runs_findings ON agent_runs USING GIN(findings);
CREATE INDEX idx_agent_runs_tool_calls ON agent_runs USING GIN(tool_calls);

-- ============================================================================
-- RCA_REPORTS TABLE
-- ============================================================================
CREATE TABLE rca_reports (
    id TEXT PRIMARY KEY DEFAULT 'rca_' || encode(gen_random_bytes(12), 'hex'),
    incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    
    -- RCA content
    root_cause TEXT NOT NULL,
    causal_chain TEXT NOT NULL,
    confidence_score INTEGER NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 100),
    contributing_factors JSONB DEFAULT '[]'::jsonb,
    timeline JSONB NOT NULL,  -- Array of {time, event} objects
    executive_summary TEXT NOT NULL,
    
    -- Remediation
    remediation_actions JSONB NOT NULL,  -- Array of RemediationAction objects
    requires_human_approval BOOLEAN DEFAULT TRUE,
    approval_urgency TEXT,
    
    -- Approval tracking
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    
    -- Meta
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_rca_reports_incident_id ON rca_reports(incident_id);
CREATE INDEX idx_rca_reports_confidence_score ON rca_reports(confidence_score);
CREATE INDEX idx_rca_reports_created_at ON rca_reports(created_at DESC);
CREATE INDEX idx_rca_reports_remediation_actions ON rca_reports USING GIN(remediation_actions);

-- ============================================================================
-- LEARNING_CASES TABLE (for vector similarity search)
-- ============================================================================
CREATE TABLE learning_cases (
    id TEXT PRIMARY KEY DEFAULT 'case_' || encode(gen_random_bytes(12), 'hex'),
    incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    
    -- Content for retrieval
    title TEXT NOT NULL,
    service_name TEXT NOT NULL,
    symptoms TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    resolution_summary TEXT NOT NULL,
    
    -- Vector embedding (OpenAI text-embedding-3-small = 1536 dimensions)
    embedding vector(1536),
    
    -- Metadata
    severity incident_severity NOT NULL,
    resolution_time_seconds INTEGER,
    human_validated BOOLEAN DEFAULT FALSE,
    quality_score NUMERIC(3,2) DEFAULT 1.0 CHECK (quality_score >= 0 AND quality_score <= 5.0),
    
    -- Soft delete for low-quality cases
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_learning_cases_service_name ON learning_cases(service_name);
CREATE INDEX idx_learning_cases_severity ON learning_cases(severity);
CREATE INDEX idx_learning_cases_is_active ON learning_cases(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_learning_cases_quality_score ON learning_cases(quality_score DESC);

-- IVFFlat index for vector similarity search (approximate nearest neighbor)
-- Lists = sqrt(total_rows) is a good starting point; adjust based on data size
CREATE INDEX idx_learning_cases_embedding ON learning_cases 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- ============================================================================
-- NOTIFICATIONS TABLE
-- ============================================================================
CREATE TABLE notifications (
    id TEXT PRIMARY KEY DEFAULT 'notif_' || encode(gen_random_bytes(12), 'hex'),
    incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    
    -- Notification content
    notification_type TEXT NOT NULL,  -- 'rca_ready', 'approval_needed', 'remediation_complete', etc.
    channel TEXT NOT NULL,  -- 'slack', 'email', 'pagerduty', 'webhook'
    recipient TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    
    -- Delivery status
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'sent', 'failed'
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    
    -- External tracking
    external_message_id TEXT,  -- Slack message TS, email message ID, etc.
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_notifications_incident_id ON notifications(incident_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- ============================================================================
-- AUDIT_LOG TABLE (immutable append-only)
-- ============================================================================
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY DEFAULT 'audit_' || encode(gen_random_bytes(12), 'hex'),
    incident_id TEXT REFERENCES incidents(id) ON DELETE CASCADE,
    
    -- Event details
    event_type TEXT NOT NULL,  -- 'investigation_started', 'rca_approved', 'remediation_executed', etc.
    actor TEXT NOT NULL,  -- User ID or 'system'
    action TEXT NOT NULL,  -- Human-readable description
    
    -- Context
    resource_type TEXT,  -- 'incident', 'agent_run', 'rca_report', 'remediation_action'
    resource_id TEXT,
    changes JSONB,  -- Before/after state for mutations
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Security
    ip_address INET,
    user_agent TEXT,
    
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_log_incident_id ON audit_log(incident_id);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_log_actor ON audit_log(actor);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);

-- Row-level security: application can INSERT but never UPDATE or DELETE
-- (Requires setting up RLS policies based on your auth model)

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_incidents_updated_at
    BEFORE UPDATE ON incidents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rca_reports_updated_at
    BEFORE UPDATE ON rca_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_learning_cases_updated_at
    BEFORE UPDATE ON learning_cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-calculate agent run duration on completion
CREATE OR REPLACE FUNCTION calculate_agent_run_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL AND OLD.completed_at IS NULL THEN
        NEW.duration_seconds := EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_duration_on_complete
    BEFORE UPDATE ON agent_runs
    FOR EACH ROW
    EXECUTE FUNCTION calculate_agent_run_duration();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Incident summary view with joined data
CREATE VIEW incident_summary AS
SELECT 
    i.id,
    i.title,
    i.severity,
    i.status,
    i.service_name,
    i.created_at,
    i.resolved_at,
    i.mttr_seconds,
    i.mttd_seconds,
    COUNT(DISTINCT ar.id) AS agent_runs_count,
    COUNT(DISTINCT ar.id) FILTER (WHERE ar.status = 'completed') AS completed_agent_runs,
    COUNT(DISTINCT ar.id) FILTER (WHERE ar.status = 'failed') AS failed_agent_runs,
    rca.id AS rca_id,
    rca.confidence_score AS rca_confidence,
    rca.root_cause AS rca_root_cause,
    rca.approved_at AS rca_approved_at
FROM incidents i
LEFT JOIN agent_runs ar ON i.id = ar.incident_id
LEFT JOIN rca_reports rca ON i.id = rca.incident_id
GROUP BY i.id, rca.id;

-- Agent performance statistics view
CREATE VIEW agent_performance_stats AS
SELECT 
    agent_type,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed_runs,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
    COUNT(*) FILTER (WHERE status = 'timeout') AS timeout_runs,
    ROUND(AVG(duration_seconds)::numeric, 2) AS avg_duration_seconds,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_seconds)::numeric, 2) AS p50_duration_seconds,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_seconds)::numeric, 2) AS p95_duration_seconds,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_seconds)::numeric, 2) AS p99_duration_seconds,
    SUM(llm_calls_count) AS total_llm_calls,
    SUM(llm_tokens_total) AS total_llm_tokens,
    ROUND(SUM(llm_cost_usd)::numeric, 2) AS total_cost_usd,
    ROUND((COUNT(*) FILTER (WHERE status = 'completed')::numeric / NULLIF(COUNT(*), 0) * 100), 2) AS success_rate_percent
FROM agent_runs
GROUP BY agent_type;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to search for similar incidents using vector similarity
CREATE OR REPLACE FUNCTION search_similar_incidents(
    query_embedding vector(1536),
    match_threshold NUMERIC DEFAULT 0.75,
    match_count INTEGER DEFAULT 5
)
RETURNS TABLE (
    case_id TEXT,
    incident_id TEXT,
    title TEXT,
    service_name TEXT,
    root_cause TEXT,
    resolution_summary TEXT,
    similarity NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        lc.id AS case_id,
        lc.incident_id,
        lc.title,
        lc.service_name,
        lc.root_cause,
        lc.resolution_summary,
        1 - (lc.embedding <=> query_embedding) AS similarity
    FROM learning_cases lc
    WHERE 
        lc.is_active = TRUE
        AND 1 - (lc.embedding <=> query_embedding) >= match_threshold
    ORDER BY lc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- DEMO SEED DATA
-- ============================================================================

-- Incident 1: OOMKill incident (resolved)
INSERT INTO incidents (id, title, severity, status, service_name, alert_name, description, external_id, created_at, resolved_at, mttr_seconds, mttd_seconds, metadata)
VALUES 
('inc_001_demo_oomkill', 'payment-service high error rate', 'P1', 'resolved', 'payment-service', 'error_rate_high', 
 '5xx error rate exceeded 5% threshold for 3 minutes', 'PD-DEMO-001', 
 '2025-01-15 03:42:00+00', '2025-01-15 04:05:00+00', 1380, 180,
 '{"pagerduty_incident_url": "https://company.pagerduty.com/incidents/DEMO001", "alert_source": "prometheus"}'::jsonb);

-- Incident 2: Database slow query (resolved)
INSERT INTO incidents (id, title, severity, status, service_name, alert_name, description, external_id, created_at, resolved_at, mttr_seconds, mttd_seconds)
VALUES 
('inc_002_demo_slowquery', 'checkout-service high latency', 'P1', 'resolved', 'checkout-service', 'latency_p99_high',
 'p99 latency exceeded 5000ms for 5 minutes', 'PD-DEMO-002',
 '2025-01-14 14:25:00+00', '2025-01-14 15:10:00+00', 2700, 300);

-- Incident 3: DNS resolution failure (resolved)
INSERT INTO incidents (id, title, severity, status, service_name, alert_name, description, external_id, created_at, resolved_at, mttr_seconds)
VALUES 
('inc_003_demo_dns', 'api-gateway 503 errors', 'P1', 'resolved', 'api-gateway', 'error_rate_high',
 '30% of requests returning 503 Service Unavailable', 'PD-DEMO-003',
 '2025-01-13 08:15:00+00', '2025-01-13 08:45:00+00', 1800);

-- Incident 4: Cost anomaly (investigating)
INSERT INTO incidents (id, title, severity, status, service_name, alert_name, description, created_at)
VALUES 
('inc_004_demo_cost', 'ml-training-service cost spike', 'P2', 'investigating', 'ml-training-service', 'cost_anomaly',
 'AWS Cost Anomaly Detection: 300% increase in EC2 spend',
 '2025-01-15 10:30:00+00');

-- Incident 5: Security alert (awaiting_approval)
INSERT INTO incidents (id, title, severity, status, service_name, alert_name, description, created_at)
VALUES 
('inc_005_demo_security', 'auth-service unusual access patterns', 'P2', 'awaiting_approval', 'auth-service', 'anomalous_access',
 'Detected 10,000 failed login attempts from single IP in 5 minutes',
 '2025-01-15 09:00:00+00');

-- Agent runs for Incident 1 (OOMKill - complete investigation)
INSERT INTO agent_runs (id, incident_id, agent_type, status, started_at, completed_at, duration_seconds, llm_calls_count, llm_tokens_total, llm_cost_usd, findings)
VALUES 
('run_001_planning', 'inc_001_demo_oomkill', 'planning', 'completed', 
 '2025-01-15 03:42:30+00', '2025-01-15 03:43:15+00', 45, 3, 2800, 0.042,
 '{"hypotheses": [
    {"id": "H1", "description": "PostgreSQL connection pool exhausted", "confidence": 0.45, "basis": "High similarity to incident 2024-11-22"},
    {"id": "H2", "description": "Recent deployment introduced regression", "confidence": 0.30, "basis": "Common pattern"}
  ],
  "agent_dispatch": [
    {"group": 1, "agents": ["kubernetes_agent", "github_agent"], "parallel": true},
    {"group": 2, "agents": ["storage_agent"], "parallel": false}
  ]}'::jsonb);

INSERT INTO agent_runs (id, incident_id, agent_type, status, started_at, completed_at, duration_seconds, llm_calls_count, llm_tokens_total, llm_cost_usd, findings)
VALUES 
('run_001_k8s', 'inc_001_demo_oomkill', 'kubernetes', 'completed',
 '2025-01-15 03:43:20+00', '2025-01-15 03:44:50+00', 90, 8, 12000, 0.180,
 '{"service": "payment-service", "namespace": "payments", 
   "summary": "Memory leak via unbounded in-memory cache growth. OOMKills caused pod count to drop from 6 to 3.",
   "findings": [
     {"type": "OOMKill", "confidence": "HIGH", "timestamp": "2025-01-15T03:22:00Z", 
      "evidence": "3 pods OOMKilled between 03:22 and 03:42. Memory limit 512Mi consistently exceeded.",
      "affected_resources": ["payment-service-7d9f-vb8w2", "payment-service-7d9f-qp5t3"]},
     {"type": "UnboundedCacheGrowth", "confidence": "HIGH", "timestamp": "2025-01-15T03:10:12Z",
      "evidence": "Log: in-memory cache growing unbounded. Cache grew to 412,008 entries before OOMKill."}
   ],
   "healthy_pods": 3, "total_pods": 6, "capacity_degradation_percent": 50,
   "image_version": "v2.14.1", "oom_kills_count": 3}'::jsonb);

INSERT INTO agent_runs (id, incident_id, agent_type, status, started_at, completed_at, duration_seconds, llm_calls_count, llm_tokens_total, llm_cost_usd, findings)
VALUES 
('run_001_github', 'inc_001_demo_oomkill', 'github', 'completed',
 '2025-01-15 03:43:20+00', '2025-01-15 03:44:30+00', 70, 6, 9500, 0.143,
 '{"service": "payment-service", "repo": "company/payment-service",
   "summary": "Deployment 2h 27m before incident changed CACHE_MAX_ENTRIES to 0",
   "recent_deployments": [
     {"sha": "abc123def456", "timestamp": "2025-01-15T01:15:00Z", "environment": "production", "minutes_before_incident": 147}
   ],
   "causal_candidate_commits": [
     {"sha": "abc123def456", "author": "alice@company.com", "message": "Update cache configuration",
      "timestamp": "2025-01-15T01:10:00Z", "risk_level": "high", 
      "risk_reason": "Modified cache settings: CACHE_MAX_ENTRIES set to 0", "pr_number": 4521}
   ],
   "deployment_correlation": "high", "minutes_since_last_deploy": 147,
   "relevant_diff_excerpts": ["- CACHE_MAX_ENTRIES=10000\\n+ CACHE_MAX_ENTRIES=0"]}'::jsonb);

INSERT INTO agent_runs (id, incident_id, agent_type, status, started_at, completed_at, duration_seconds, llm_calls_count, llm_tokens_total, llm_cost_usd, findings)
VALUES 
('run_001_storage', 'inc_001_demo_oomkill', 'storage', 'completed',
 '2025-01-15 03:44:55+00', '2025-01-15 03:46:20+00', 85, 5, 7200, 0.108,
 '{"service": "payment-service", "databases_checked": ["pg-payments-prod"],
   "summary": "Database healthy. Connection pool at 45% utilization. No slow queries detected.",
   "connection_pool_status": {"utilization_percent": 45, "active": 90, "idle": 110, "max": 200},
   "slow_queries": [], "severity": "healthy"}'::jsonb);

INSERT INTO agent_runs (id, incident_id, agent_type, status, started_at, completed_at, duration_seconds, llm_calls_count, llm_tokens_total, llm_cost_usd, findings)
VALUES 
('run_001_rca', 'inc_001_demo_oomkill', 'rca', 'completed',
 '2025-01-15 03:46:30+00', '2025-01-15 03:48:00+00', 90, 4, 15000, 0.225,
 '{"incident_id": "inc_001_demo_oomkill",
   "root_cause": "Deployment of payment-service v2.14.1 introduced CACHE_MAX_ENTRIES=0 environment variable, disabling the in-memory cache size limit and causing unbounded memory growth until OOMKill.",
   "confidence_score": 94}'::jsonb);

-- RCA Report for Incident 1
INSERT INTO rca_reports (id, incident_id, root_cause, causal_chain, confidence_score, contributing_factors, timeline, remediation_actions, executive_summary, approved_by, approved_at)
VALUES 
('rca_001_demo', 'inc_001_demo_oomkill',
 'Deployment of payment-service v2.14.1 introduced CACHE_MAX_ENTRIES=0 environment variable, disabling the in-memory cache size limit and causing unbounded memory growth until OOMKill.',
 'CACHE_MAX_ENTRIES=0 set in v2.14.1 deployment (01:15 UTC) → in-memory cache grew to 412,008 entries over 2 hours → pod RSS memory reached 513Mi (limit: 512Mi) → Kubernetes OOMKilled 3/6 pods (03:22-03:42 UTC) → 50% capacity loss caused 5xx error rate to exceed 5% (03:42 UTC)',
 94,
 '["Memory limit of 512Mi is low relative to normal heap usage — only 267Mi headroom for cache", 
   "No autoscaling configured (HPA min=max=6) — surviving pods could not compensate for lost capacity",
   "No canary deployment — change was applied to all 6 pods simultaneously"]'::jsonb,
 '[
   {"time": "2025-01-15T01:15:00Z", "event": "Deployment of payment-service:v2.14.1 to production"},
   {"time": "2025-01-15T02:44:00Z", "event": "Heap size warning threshold (80%) triggered"},
   {"time": "2025-01-15T03:10:00Z", "event": "Log: in-memory cache growing unbounded, 148,291 entries"},
   {"time": "2025-01-15T03:22:00Z", "event": "First OOMKill: payment-service-7d9f-vb8w2"},
   {"time": "2025-01-15T03:38:00Z", "event": "Second and third OOMKills"},
   {"time": "2025-01-15T03:42:00Z", "event": "PagerDuty alert fires — error rate 5.3%"}
 ]'::jsonb,
 '[
   {
     "action_id": "REM-001", "priority": 1, 
     "title": "Set CACHE_MAX_ENTRIES=10000 and roll out deployment",
     "steps": [
       "kubectl set env deployment/payment-service CACHE_MAX_ENTRIES=10000 -n payments",
       "kubectl rollout status deployment/payment-service -n payments --timeout=5m"
     ],
     "risk_level": "low",
     "rollback_procedure": "kubectl rollout undo deployment/payment-service -n payments",
     "estimated_time_minutes": 5
   },
   {
     "action_id": "REM-002", "priority": 2,
     "title": "Increase memory limit to 1Gi to provide safer headroom",
     "steps": [
       "Edit deployment resource limits: memory limit from 512Mi to 1Gi",
       "kubectl apply -f updated-deployment.yaml -n payments"
     ],
     "risk_level": "low",
     "rollback_procedure": "kubectl rollout undo deployment/payment-service -n payments",
     "estimated_time_minutes": 10
   }
 ]'::jsonb,
 'A configuration error in the v2.14.1 deployment caused the payment service memory cache to grow without limit, consuming all available memory and crashing half the service servers. The fix is a one-line configuration change that takes 5 minutes to apply.',
 'user_alice',
 '2025-01-15 03:50:00+00');

-- Learning case for Incident 1
INSERT INTO learning_cases (id, incident_id, title, service_name, symptoms, root_cause, resolution_summary, severity, resolution_time_seconds, human_validated, quality_score, embedding)
VALUES 
('case_001_demo', 'inc_001_demo_oomkill',
 'payment-service high error rate - OOMKill due to unbounded cache',
 'payment-service',
 'High 5xx error rate (5.3%), multiple pod restarts, OOMKilled pods, capacity degradation to 50%',
 'CACHE_MAX_ENTRIES=0 environment variable disabled cache size limit causing unbounded memory growth',
 'Set CACHE_MAX_ENTRIES=10000 and increased memory limit from 512Mi to 1Gi',
 'P1', 1380, TRUE, 5.0,
 -- In production, this would be a real embedding vector. For demo, using a zero vector.
 array_fill(0, ARRAY[1536])::vector);

-- Audit log entries for Incident 1
INSERT INTO audit_log (incident_id, event_type, actor, action, resource_type, resource_id, metadata)
VALUES 
('inc_001_demo_oomkill', 'incident_created', 'system', 'Incident created from PagerDuty webhook', 'incident', 'inc_001_demo_oomkill', 
 '{"source": "pagerduty", "external_id": "PD-DEMO-001"}'::jsonb),
('inc_001_demo_oomkill', 'investigation_started', 'system', 'Autonomous investigation triggered', 'incident', 'inc_001_demo_oomkill', '{}'::jsonb),
('inc_001_demo_oomkill', 'agent_completed', 'system', 'Planning agent completed', 'agent_run', 'run_001_planning', '{}'::jsonb),
('inc_001_demo_oomkill', 'agent_completed', 'system', 'Kubernetes agent completed', 'agent_run', 'run_001_k8s', '{}'::jsonb),
('inc_001_demo_oomkill', 'agent_completed', 'system', 'GitHub agent completed', 'agent_run', 'run_001_github', '{}'::jsonb),
('inc_001_demo_oomkill', 'rca_generated', 'system', 'RCA report generated with confidence 94%', 'rca_report', 'rca_001_demo', 
 '{"confidence_score": 94}'::jsonb),
('inc_001_demo_oomkill', 'rca_approved', 'user_alice', 'User approved remediation actions REM-001, REM-002', 'rca_report', 'rca_001_demo',
 '{"approved_actions": ["REM-001", "REM-002"]}'::jsonb),
('inc_001_demo_oomkill', 'remediation_executed', 'system', 'Executed REM-001: Set CACHE_MAX_ENTRIES=10000', 'remediation_action', 'REM-001',
 '{"result": "success", "duration_seconds": 72}'::jsonb),
('inc_001_demo_oomkill', 'incident_resolved', 'system', 'Incident marked as resolved', 'incident', 'inc_001_demo_oomkill',
 '{"mttr_seconds": 1380, "mttd_seconds": 180}'::jsonb);

-- Notifications for Incident 1
INSERT INTO notifications (incident_id, notification_type, channel, recipient, subject, body, status, sent_at, external_message_id)
VALUES 
('inc_001_demo_oomkill', 'rca_ready', 'slack', '#incidents-prod', 'RCA Ready: payment-service high error rate',
 '🚨 **RCA Ready for Approval**\n\n**Root Cause:** CACHE_MAX_ENTRIES=0 causing unbounded memory growth\n**Confidence:** 94%\n\nApprove remediation to fix.',
 'sent', '2025-01-15 03:48:30+00', '1705290510.123456'),
('inc_001_demo_oomkill', 'incident_resolved', 'slack', '#incidents-prod', 'RESOLVED: payment-service high error rate',
 '✅ **Incident Resolved**\n\nMTTR: 23 minutes\n[View full RCA](https://atlas-ai.company.com/incidents/inc_001_demo_oomkill)',
 'sent', '2025-01-15 04:05:30+00', '1705291530.789012');

-- Additional incidents (brief, without full agent runs)
INSERT INTO agent_runs (incident_id, agent_type, status, started_at, completed_at, duration_seconds, llm_calls_count, llm_tokens_total, llm_cost_usd)
VALUES 
('inc_002_demo_slowquery', 'planning', 'completed', '2025-01-14 14:25:30+00', '2025-01-14 14:26:15+00', 45, 3, 2500, 0.038),
('inc_002_demo_slowquery', 'kubernetes', 'completed', '2025-01-14 14:26:20+00', '2025-01-14 14:27:10+00', 50, 5, 6000, 0.090),
('inc_002_demo_slowquery', 'github', 'completed', '2025-01-14 14:26:20+00', '2025-01-14 14:27:30+00', 70, 6, 8500, 0.128),
('inc_002_demo_slowquery', 'storage', 'completed', '2025-01-14 14:27:35+00', '2025-01-14 14:29:00+00', 85, 7, 10000, 0.150);

INSERT INTO agent_runs (incident_id, agent_type, status, started_at, completed_at, duration_seconds, llm_calls_count, llm_tokens_total, llm_cost_usd)
VALUES 
('inc_003_demo_dns', 'planning', 'completed', '2025-01-13 08:15:30+00', '2025-01-13 08:16:10+00', 40, 2, 2200, 0.033),
('inc_003_demo_dns', 'kubernetes', 'completed', '2025-01-13 08:16:15+00', '2025-01-13 08:17:30+00', 75, 6, 8000, 0.120),
('inc_003_demo_dns', 'network', 'completed', '2025-01-13 08:17:35+00', '2025-01-13 08:19:00+00', 85, 8, 11000, 0.165);

-- ============================================================================
-- UTILITY QUERIES (for reference)
-- ============================================================================

-- Query: Get all incidents with their RCA status
-- SELECT i.id, i.title, i.severity, i.status, 
--        rca.confidence_score, rca.root_cause
-- FROM incidents i
-- LEFT JOIN rca_reports rca ON i.id = rca.incident_id
-- ORDER BY i.created_at DESC;

-- Query: Get agent performance summary
-- SELECT * FROM agent_performance_stats;

-- Query: Search for similar incidents (requires embedding vector)
-- SELECT * FROM search_similar_incidents(
--   (SELECT embedding FROM learning_cases WHERE id = 'case_001_demo'),
--   0.75,
--   5
-- );

-- Query: Get all tool calls for a specific agent run
-- SELECT id, agent_type, 
--        jsonb_array_length(tool_calls) as tool_call_count,
--        tool_calls
-- FROM agent_runs
-- WHERE id = 'run_001_k8s';

-- Query: Incident timeline with all events
-- SELECT 
--   al.timestamp,
--   al.event_type,
--   al.action,
--   al.actor
-- FROM audit_log al
-- WHERE al.incident_id = 'inc_001_demo_oomkill'
-- ORDER BY al.timestamp;

-- ============================================================================
-- GRANTS (adjust based on your user setup)
-- ============================================================================

-- Example: Grant read-only access to an audit viewer role
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO audit_viewer_role;
-- REVOKE INSERT, UPDATE, DELETE ON audit_log FROM app_user_role;

-- Example: Grant application user full access except audit log mutations
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user_role;
-- REVOKE UPDATE, DELETE ON audit_log FROM app_user_role;
