"use client";

import { useState, useEffect } from "react";
import {
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Loader2,
  Radio,
  Clock,
  Lightbulb,
  SkipForward,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatRelativeTime, formatDuration } from "@/lib/utils";
import { useAgentProgress, createMockWSEmitter } from "@/lib/websocket";
import type { AgentType, AgentRun, WSEvent } from "@/lib/types";

// ─── Agent display metadata ────────────────────────────────────────────────────

const agentMeta: Record<
  AgentType,
  { label: string; color: string; description: string }
> = {
  orchestrator: {
    label: "Orchestrator",
    color: "text-violet-400",
    description: "Coordinating investigation workflow",
  },
  log_analyzer: {
    label: "Log Analyzer",
    color: "text-blue-400",
    description: "Scanning application and system logs",
  },
  metric_analyzer: {
    label: "Metric Analyzer",
    color: "text-cyan-400",
    description: "Analyzing performance metrics and anomalies",
  },
  trace_analyzer: {
    label: "Trace Analyzer",
    color: "text-indigo-400",
    description: "Examining distributed traces",
  },
  dependency_mapper: {
    label: "Dependency Mapper",
    color: "text-teal-400",
    description: "Mapping service dependencies and call graph",
  },
  hypothesis_generator: {
    label: "Hypothesis Generator",
    color: "text-amber-400",
    description: "Generating root cause hypotheses",
  },
  evidence_collector: {
    label: "Evidence Collector",
    color: "text-orange-400",
    description: "Collecting supporting evidence",
  },
  rca_synthesizer: {
    label: "RCA Synthesizer",
    color: "text-rose-400",
    description: "Synthesizing root cause analysis",
  },
  fix_recommender: {
    label: "Fix Recommender",
    color: "text-emerald-400",
    description: "Generating fix recommendations",
  },
};

// ─── Agent Row ────────────────────────────────────────────────────────────────

interface AgentRowProps {
  run: AgentRun;
  isNew?: boolean;
}

function AgentRow({ run, isNew = false }: AgentRowProps) {
  const [expanded, setExpanded] = useState(false);
  const meta = agentMeta[run.agent_type] ?? {
    label: run.agent_type,
    color: "text-slate-400",
    description: "",
  };

  const StatusIcon = () => {
    switch (run.status) {
      case "running":
        return <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />;
      case "completed":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-400" />;
      case "skipped":
        return <SkipForward className="w-4 h-4 text-slate-500" />;
      default:
        return <Clock className="w-4 h-4 text-slate-600" />;
    }
  };

  return (
    <div
      className={cn(
        "rounded-lg border transition-all duration-300",
        isNew && "animate-fade-in",
        run.status === "running"
          ? "border-indigo-500/30 bg-indigo-500/5"
          : run.status === "completed"
          ? "border-emerald-500/20 bg-emerald-500/5"
          : run.status === "failed"
          ? "border-red-500/20 bg-red-500/5"
          : "border-slate-700/40 bg-slate-900/30"
      )}
    >
      {/* Header row */}
      <button
        onClick={() => run.findings.length > 0 && setExpanded(!expanded)}
        className={cn(
          "w-full flex items-center gap-3 px-4 py-3 text-left",
          run.findings.length > 0 ? "cursor-pointer" : "cursor-default"
        )}
      >
        <StatusIcon />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={cn("text-sm font-semibold", meta.color)}>
              {meta.label}
            </span>
            {run.status === "running" && (
              <span className="text-[10px] font-mono text-slate-500 animate-pulse">
                running…
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{meta.description}</p>
        </div>

        {/* Duration */}
        {run.duration_ms && (
          <span className="text-[10px] font-mono text-slate-600 shrink-0">
            {formatDuration(run.duration_ms)}
          </span>
        )}

        {/* Findings count */}
        {run.findings.length > 0 && (
          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/20 shrink-0">
            <Lightbulb className="w-3 h-3" />
            {run.findings.length}
          </span>
        )}

        {run.findings.length > 0 && (
          expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-slate-600 shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
          )
        )}
      </button>

      {/* Progress bar for running agents */}
      {run.status === "running" && (
        <div className="mx-4 mb-3">
          <div className="h-0.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full transition-all duration-500"
              style={{ width: `${run.progress ?? 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Error message */}
      {run.status === "failed" && run.error && (
        <div className="mx-4 mb-3 flex items-center gap-2 text-xs text-red-400 bg-red-500/10 rounded-lg px-3 py-2">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          {run.error}
        </div>
      )}

      {/* Expanded findings */}
      {expanded && run.findings.length > 0 && (
        <div className="px-4 pb-3 space-y-2">
          <div className="h-px bg-slate-700/30" />
          {run.findings.map((finding) => (
            <div
              key={finding.id}
              className="rounded-lg bg-slate-900/60 border border-slate-700/30 px-3 py-2.5"
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <span className="text-xs font-semibold text-slate-300">
                  {finding.title}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 shrink-0">
                  {Math.round(finding.confidence * 100)}% conf
                </span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                {finding.description}
              </p>
              {finding.evidence && finding.evidence.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {finding.evidence.map((e, i) => (
                    <li
                      key={i}
                      className="text-[10px] font-mono text-slate-600 flex items-center gap-1.5"
                    >
                      <span className="w-1 h-1 rounded-full bg-slate-600 shrink-0" />
                      {e}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface AgentProgressFeedProps {
  investigationId: string;
  /** If true, uses the built-in mock emitter for demo purposes */
  useMock?: boolean;
  onComplete?: (rcaId?: string) => void;
}

export function AgentProgressFeed({
  investigationId,
  useMock = false,
  onComplete,
}: AgentProgressFeedProps) {
  const {
    agentRuns,
    connectionState,
    isCompleted,
    isFailed,
    rcaId,
  } = useAgentProgress({
    investigationId: useMock ? null : investigationId,
    enabled: !useMock,
  });

  // Mock state management
  const [mockAgentRuns, setMockAgentRuns] = useState<Record<string, AgentRun>>({});
  const [mockIsCompleted, setMockIsCompleted] = useState(false);
  const [mockRcaId, setMockRcaId] = useState<string>();
  const [mockConnectionState, setMockConnectionState] =
    useState<"connecting" | "connected" | "disconnected" | "error">("connecting");

  useEffect(() => {
    if (!useMock) return;

    setMockConnectionState("connecting");
    const timeout = setTimeout(() => {
      setMockConnectionState("connected");

      const stop = createMockWSEmitter(investigationId, (event: WSEvent) => {
        setMockAgentRuns((prev) => {
          const next = { ...prev };

          if (event.type === "agent_started" && event.data.agent_type && event.data.agent_run_id) {
            next[event.data.agent_run_id] = {
              id: event.data.agent_run_id,
              investigation_id: investigationId,
              agent_type: event.data.agent_type as AgentType,
              status: "running",
              started_at: event.timestamp,
              findings: [],
              progress: 0,
            };
          } else if (event.type === "agent_progress" && event.data.agent_run_id && next[event.data.agent_run_id]) {
            next[event.data.agent_run_id] = {
              ...next[event.data.agent_run_id],
              progress: event.data.progress ?? 0,
            };
          } else if (event.type === "agent_finding" && event.data.agent_run_id && event.data.finding && next[event.data.agent_run_id]) {
            const run = next[event.data.agent_run_id];
            next[event.data.agent_run_id] = {
              ...run,
              findings: [...run.findings, event.data.finding],
            };
          } else if (event.type === "agent_completed" && event.data.agent_run_id && next[event.data.agent_run_id]) {
            next[event.data.agent_run_id] = {
              ...next[event.data.agent_run_id],
              status: "completed",
              completed_at: event.timestamp,
              progress: 100,
              duration_ms: Math.floor(Math.random() * 3000) + 500,
            };
          } else if (event.type === "agent_failed" && event.data.agent_run_id && next[event.data.agent_run_id]) {
            next[event.data.agent_run_id] = {
              ...next[event.data.agent_run_id],
              status: "failed",
              error: event.data.error,
            };
          }

          return next;
        });

        if (event.type === "investigation_completed") {
          setMockIsCompleted(true);
          setMockRcaId(event.data.rca_id);
        }
      });

      return stop;
    }, 800);

    return () => clearTimeout(timeout);
  }, [useMock, investigationId]);

  useEffect(() => {
    if ((isCompleted || mockIsCompleted) && onComplete) {
      onComplete(rcaId ?? mockRcaId);
    }
  }, [isCompleted, mockIsCompleted, rcaId, mockRcaId, onComplete]);

  const activeRuns = Object.values(useMock ? mockAgentRuns : agentRuns);
  const activeConnState = useMock ? mockConnectionState : connectionState;
  const completed = useMock ? mockIsCompleted : isCompleted;
  const failed = isFailed;

  const completedCount = activeRuns.filter((r) => r.status === "completed").length;
  const totalCount = activeRuns.length;

  return (
    <div className="space-y-3">
      {/* Status bar */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          {activeConnState === "connecting" && (
            <>
              <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
              <span className="text-xs text-slate-500">Connecting to investigation feed…</span>
            </>
          )}
          {activeConnState === "connected" && !completed && !failed && (
            <>
              <Radio className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
              <span className="text-xs text-indigo-300 font-medium">Live — agents working</span>
            </>
          )}
          {activeConnState === "disconnected" && !completed && (
            <>
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-xs text-amber-400">Connection lost — reconnecting…</span>
            </>
          )}
          {completed && (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-xs text-emerald-400 font-medium">Investigation complete</span>
            </>
          )}
          {failed && (
            <>
              <XCircle className="w-3.5 h-3.5 text-red-400" />
              <span className="text-xs text-red-400 font-medium">Investigation failed</span>
            </>
          )}
        </div>

        {totalCount > 0 && (
          <span className="text-xs font-mono text-slate-500">
            {completedCount}/{totalCount} agents
          </span>
        )}
      </div>

      {/* Agent rows */}
      {activeRuns.length === 0 && activeConnState === "connecting" && (
        <div className="flex flex-col items-center gap-3 py-12 text-slate-600">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-500/50" />
          <p className="text-sm">Waiting for agents to start…</p>
        </div>
      )}

      <div className="space-y-2">
        {activeRuns.map((run) => (
          <AgentRow key={run.id} run={run} isNew />
        ))}
      </div>

      {/* Completion summary */}
      {completed && (
        <div className="mt-2 animate-fade-in rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-emerald-400">
              All agents completed successfully
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              {completedCount} agents ran · RCA report is ready
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
