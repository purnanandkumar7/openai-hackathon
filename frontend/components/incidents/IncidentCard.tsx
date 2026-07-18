import Link from "next/link";
import { Clock, Server, Users } from "lucide-react";
import { type Incident } from "@/lib/types";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { formatRelativeTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

// ─── Agent type → display label ───────────────────────────────────────────────

const agentLabels: Record<string, string> = {
  orchestrator: "Orch",
  log_analyzer: "Logs",
  metric_analyzer: "Metrics",
  trace_analyzer: "Traces",
  dependency_mapper: "Deps",
  hypothesis_generator: "Hyp",
  evidence_collector: "Evid",
  rca_synthesizer: "RCA",
  fix_recommender: "Fix",
};

interface IncidentCardProps {
  incident: Incident;
  className?: string;
  compact?: boolean;
}

export function IncidentCard({
  incident,
  className,
  compact = false,
}: IncidentCardProps) {
  return (
    <Link href={`/incidents/${incident.id}`} className="block group">
      <div
        className={cn(
          "rounded-xl border border-slate-800/60 bg-slate-900/40 p-4 transition-all duration-200",
          "hover:border-indigo-500/30 hover:bg-slate-900/80 hover:shadow-lg hover:shadow-black/20",
          "group-hover:translate-y-[-1px]",
          className
        )}
      >
        {/* Top row */}
        <div className="flex items-start justify-between gap-3 mb-2.5">
          <div className="flex items-center gap-2 min-w-0">
            <SeverityBadge severity={incident.severity} size="sm" />
            <span className="text-[10px] font-mono text-slate-600 shrink-0">
              #{incident.id.slice(-6).toUpperCase()}
            </span>
          </div>
          <StatusIndicator status={incident.status} size="sm" />
        </div>

        {/* Title */}
        <h3 className="text-sm font-semibold text-slate-200 leading-snug mb-1.5 group-hover:text-white transition-colors line-clamp-2">
          {incident.title}
        </h3>

        {!compact && (
          <p className="text-xs text-slate-500 leading-relaxed line-clamp-2 mb-3">
            {incident.description}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between mt-2">
          {/* Affected services */}
          <div className="flex items-center gap-1.5 min-w-0">
            <Server className="w-3 h-3 text-slate-600 shrink-0" />
            <div className="flex gap-1 flex-wrap">
              {incident.affected_services.slice(0, 2).map((svc) => (
                <span
                  key={svc}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/60 text-slate-500 border border-slate-700/30"
                >
                  {svc}
                </span>
              ))}
              {incident.affected_services.length > 2 && (
                <span className="text-[10px] text-slate-600">
                  +{incident.affected_services.length - 2}
                </span>
              )}
            </div>
          </div>

          {/* Time */}
          <div className="flex items-center gap-1 text-[10px] text-slate-600 shrink-0 ml-2">
            <Clock className="w-3 h-3" />
            {formatRelativeTime(incident.created_at)}
          </div>
        </div>

        {/* Assigned agents */}
        {incident.assigned_agents && incident.assigned_agents.length > 0 && !compact && (
          <div className="flex items-center gap-1.5 mt-2.5 pt-2.5 border-t border-slate-800/40">
            <Users className="w-3 h-3 text-slate-600" />
            <div className="flex gap-1">
              {incident.assigned_agents.map((a) => (
                <span
                  key={a}
                  className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/15"
                >
                  {agentLabels[a] ?? a}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </Link>
  );
}
