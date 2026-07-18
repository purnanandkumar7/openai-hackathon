// TypeScript interfaces for Atlas AI

// ─── Enums ───────────────────────────────────────────────────────────────────

export type Severity = "P1" | "P2" | "P3" | "P4";
export type IncidentStatus = "open" | "investigating" | "resolved" | "closed";
export type AgentStatus = "idle" | "running" | "completed" | "failed" | "skipped";
export type AgentType =
  | "orchestrator"
  | "log_analyzer"
  | "metric_analyzer"
  | "trace_analyzer"
  | "dependency_mapper"
  | "hypothesis_generator"
  | "evidence_collector"
  | "rca_synthesizer"
  | "fix_recommender";

// ─── Core Models ─────────────────────────────────────────────────────────────

export interface Service {
  id: string;
  name: string;
  team?: string;
  tier?: number;
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  status: IncidentStatus;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  affected_services: string[];
  assigned_agents?: string[];
  investigation_id?: string;
  rca_id?: string;
  metadata?: Record<string, unknown>;
}

export interface CreateIncidentPayload {
  title: string;
  description: string;
  severity: Severity;
  affected_services: string[];
  metadata?: Record<string, unknown>;
}

// ─── Agent Models ─────────────────────────────────────────────────────────────

export interface AgentFinding {
  id: string;
  agent_type: AgentType;
  title: string;
  description: string;
  confidence: number; // 0-1
  evidence?: string[];
  metadata?: Record<string, unknown>;
  timestamp: string;
}

export interface AgentRun {
  id: string;
  investigation_id: string;
  agent_type: AgentType;
  status: AgentStatus;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  findings: AgentFinding[];
  error?: string;
  progress?: number; // 0-100
}

export interface Investigation {
  id: string;
  incident_id: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string;
  completed_at?: string;
  agent_runs: AgentRun[];
  rca_id?: string;
}

// ─── RCA Report ──────────────────────────────────────────────────────────────

export interface TimelineEvent {
  id: string;
  timestamp: string;
  type: "anomaly" | "deployment" | "alert" | "config_change" | "recovery" | "incident";
  title: string;
  description: string;
  service?: string;
  severity?: "low" | "medium" | "high" | "critical";
  metadata?: Record<string, unknown>;
}

export interface ContributingFactor {
  id: string;
  title: string;
  description: string;
  category: "technical" | "process" | "human" | "external";
  weight: number; // 0-1
  evidence: string[];
}

export interface FixRecommendation {
  id: string;
  title: string;
  description: string;
  type: "immediate" | "short_term" | "long_term";
  priority: "critical" | "high" | "medium" | "low";
  effort: "low" | "medium" | "high";
  impact: "low" | "medium" | "high";
  steps: string[];
  owner?: string;
  estimated_effort?: string;
}

export interface LessonLearned {
  id: string;
  category: "detection" | "response" | "prevention" | "process";
  title: string;
  description: string;
  action_items: string[];
}

export interface RCAReport {
  id: string;
  incident_id: string;
  investigation_id: string;
  generated_at: string;
  confidence_score: number; // 0-1
  root_cause: {
    title: string;
    description: string;
    service: string;
    component?: string;
    category: string;
  };
  contributing_factors: ContributingFactor[];
  timeline: TimelineEvent[];
  fix_recommendations: FixRecommendation[];
  lessons_learned: LessonLearned[];
  affected_services: string[];
  impact_summary: string;
  executive_summary: string;
}

// ─── Learning Loop ────────────────────────────────────────────────────────────

export type ResolutionOutcome = "correct" | "partially_correct" | "incorrect" | "unknown";

export interface Resolution {
  id: string;
  incident_id: string;
  rca_id: string;
  outcome: ResolutionOutcome;
  outcome_score: number; // 0-1
  approved_by?: string;
  approved_at?: string;
  notes?: string;
  created_at: string;
  feedback?: string;
}

export interface LearningMetrics {
  total_incidents: number;
  resolved_incidents: number;
  avg_resolution_time_minutes: number;
  avg_confidence_score: number;
  outcome_distribution: Record<ResolutionOutcome, number>;
  accuracy_trend: Array<{
    date: string;
    accuracy: number;
    incident_count: number;
  }>;
  agent_performance: Array<{
    agent_type: AgentType;
    avg_confidence: number;
    run_count: number;
    failure_rate: number;
  }>;
}

// ─── WebSocket Events ─────────────────────────────────────────────────────────

export type WSEventType =
  | "investigation_started"
  | "agent_started"
  | "agent_progress"
  | "agent_finding"
  | "agent_completed"
  | "agent_failed"
  | "investigation_completed"
  | "investigation_failed";

export interface WSEvent {
  type: WSEventType;
  investigation_id: string;
  timestamp: string;
  data: {
    agent_type?: AgentType;
    agent_run_id?: string;
    progress?: number;
    finding?: AgentFinding;
    error?: string;
    message?: string;
    agent_run?: AgentRun;
    rca_id?: string;
  };
}

// ─── API Responses ────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface APIError {
  detail: string;
  code?: string;
  field?: string;
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export interface DashboardStats {
  total_open: number;
  by_severity: Record<Severity, number>;
  active_investigations: number;
  resolved_today: number;
  avg_mttr_minutes: number;
  system_health: "healthy" | "degraded" | "critical";
}

// ─── Agent Info ───────────────────────────────────────────────────────────────

export interface AgentInfo {
  type: AgentType;
  display_name: string;
  description: string;
  icon: string;
  last_run?: string;
  total_runs: number;
  success_rate: number;
  avg_duration_ms: number;
  status: "idle" | "running" | "degraded";
  findings_count: number;
}
