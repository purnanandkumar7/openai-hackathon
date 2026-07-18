import {
  Bot,
  FileText,
  BarChart2,
  GitBranch,
  Network,
  Lightbulb,
  Search,
  FileCheck,
  Wrench,
  CheckCircle2,
  XCircle,
  Clock,
  Activity,
  Loader2,
} from "lucide-react";
import { type AgentInfo, type AgentType } from "@/lib/types";
import { formatRelativeTime, formatDuration, cn } from "@/lib/utils";

// ─── Agent type icons & colors ────────────────────────────────────────────────

const agentIconMap: Record<AgentType, React.FC<{ className?: string }>> = {
  orchestrator: Bot,
  log_analyzer: FileText,
  metric_analyzer: BarChart2,
  trace_analyzer: GitBranch,
  dependency_mapper: Network,
  hypothesis_generator: Lightbulb,
  evidence_collector: Search,
  rca_synthesizer: FileCheck,
  fix_recommender: Wrench,
};

const agentColorMap: Record<AgentType, { bg: string; text: string; border: string }> = {
  orchestrator:         { bg: "bg-violet-500/10",  text: "text-violet-400",  border: "border-violet-500/20" },
  log_analyzer:         { bg: "bg-blue-500/10",    text: "text-blue-400",    border: "border-blue-500/20"   },
  metric_analyzer:      { bg: "bg-cyan-500/10",    text: "text-cyan-400",    border: "border-cyan-500/20"   },
  trace_analyzer:       { bg: "bg-indigo-500/10",  text: "text-indigo-400",  border: "border-indigo-500/20" },
  dependency_mapper:    { bg: "bg-teal-500/10",    text: "text-teal-400",    border: "border-teal-500/20"   },
  hypothesis_generator: { bg: "bg-amber-500/10",   text: "text-amber-400",   border: "border-amber-500/20"  },
  evidence_collector:   { bg: "bg-orange-500/10",  text: "text-orange-400",  border: "border-orange-500/20" },
  rca_synthesizer:      { bg: "bg-rose-500/10",    text: "text-rose-400",    border: "border-rose-500/20"   },
  fix_recommender:      { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20"},
};

// ─── Status dot ───────────────────────────────────────────────────────────────

function StatusDot({ status }: { status: AgentInfo["status"] }) {
  if (status === "running") {
    return (
      <div className="flex items-center gap-1.5">
        <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
        <span className="text-xs text-indigo-400">Running</span>
      </div>
    );
  }
  if (status === "degraded") {
    return (
      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-amber-400" />
        <span className="text-xs text-amber-400">Degraded</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-2 h-2 rounded-full bg-emerald-400" />
      <span className="text-xs text-emerald-400">Idle</span>
    </div>
  );
}

// ─── Metric mini block ────────────────────────────────────────────────────────

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] text-slate-600 uppercase tracking-wide">{label}</span>
      <span className="text-xs font-semibold text-slate-300">{value}</span>
    </div>
  );
}

// ─── Agent Card ───────────────────────────────────────────────────────────────

interface AgentCardProps {
  agent: AgentInfo;
  className?: string;
}

export function AgentCard({ agent, className }: AgentCardProps) {
  const Icon = agentIconMap[agent.type] ?? Bot;
  const colors = agentColorMap[agent.type] ?? {
    bg: "bg-slate-800",
    text: "text-slate-400",
    border: "border-slate-700",
  };

  const successRatePct = Math.round(agent.success_rate * 100);
  const successColor =
    successRatePct >= 95
      ? "text-emerald-400"
      : successRatePct >= 80
      ? "text-amber-400"
      : "text-red-400";

  return (
    <div
      className={cn(
        "rounded-xl border border-slate-800/60 bg-slate-900/40 p-4 transition-all duration-200 hover:border-slate-700/60 hover:bg-slate-900/70",
        agent.status === "running" && "border-indigo-500/25 bg-indigo-500/5",
        agent.status === "degraded" && "border-amber-500/20 bg-amber-500/5",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex items-center justify-center w-9 h-9 rounded-xl border",
              colors.bg,
              colors.border
            )}
          >
            <Icon className={cn("w-4.5 h-4.5", colors.text)} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-200">
              {agent.display_name}
            </h3>
            <p className="text-[10px] font-mono text-slate-600">{agent.type}</p>
          </div>
        </div>
        <StatusDot status={agent.status} />
      </div>

      {/* Description */}
      <p className="text-xs text-slate-500 leading-relaxed mb-4">
        {agent.description}
      </p>

      {/* Metrics row */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <Metric label="Runs" value={agent.total_runs.toLocaleString()} />
        <Metric
          label="Avg time"
          value={formatDuration(agent.avg_duration_ms)}
        />
        <Metric label="Findings" value={agent.findings_count.toLocaleString()} />
      </div>

      {/* Success rate bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-slate-600 uppercase tracking-wide">
            Success rate
          </span>
          <span className={cn("text-xs font-semibold", successColor)}>
            {successRatePct}%
          </span>
        </div>
        <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all",
              successRatePct >= 95
                ? "bg-emerald-500"
                : successRatePct >= 80
                ? "bg-amber-500"
                : "bg-red-500"
            )}
            style={{ width: `${successRatePct}%` }}
          />
        </div>
      </div>

      {/* Last run */}
      {agent.last_run && (
        <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-slate-800/40">
          <Activity className="w-3 h-3 text-slate-600" />
          <span className="text-[10px] text-slate-600">
            Last run {formatRelativeTime(agent.last_run)}
          </span>
        </div>
      )}
    </div>
  );
}
