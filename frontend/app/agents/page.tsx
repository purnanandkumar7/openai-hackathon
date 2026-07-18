import type { Metadata } from "next";
import { Bot, Activity, Zap, TrendingUp } from "lucide-react";
import { AgentCard } from "@/components/agents/AgentCard";
import { MOCK_AGENTS } from "@/lib/mock-data";

export const metadata: Metadata = { title: "Agents" };

export default function AgentsPage() {
  const running = MOCK_AGENTS.filter((a) => a.status === "running").length;
  const degraded = MOCK_AGENTS.filter((a) => a.status === "degraded").length;
  const totalRuns = MOCK_AGENTS.reduce((acc, a) => acc + a.total_runs, 0);
  const avgSuccess =
    MOCK_AGENTS.reduce((acc, a) => acc + a.success_rate, 0) / MOCK_AGENTS.length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Agents</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          {MOCK_AGENTS.length} specialized AI agents · {running} currently running
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Total Agents</span>
            <Bot className="w-4 h-4 text-violet-400" />
          </div>
          <p className="text-2xl font-bold text-white">{MOCK_AGENTS.length}</p>
        </div>
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Currently Running</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-2xl font-bold text-white">{running}</p>
          {degraded > 0 && (
            <p className="text-xs text-amber-400 mt-0.5">{degraded} degraded</p>
          )}
        </div>
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Total Runs</span>
            <Zap className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-white">{totalRuns.toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Avg Success Rate</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white">
            {Math.round(avgSuccess * 100)}%
          </p>
        </div>
      </div>

      {/* Running agents highlight */}
      {running > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
            Currently Active
          </h2>
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {MOCK_AGENTS.filter((a) => a.status === "running").map((agent) => (
              <AgentCard key={agent.type} agent={agent} />
            ))}
          </div>
        </div>
      )}

      {/* Degraded agents */}
      {degraded > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            Degraded
          </h2>
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {MOCK_AGENTS.filter((a) => a.status === "degraded").map((agent) => (
              <AgentCard key={agent.type} agent={agent} />
            ))}
          </div>
        </div>
      )}

      {/* All agents */}
      <div>
        <h2 className="text-sm font-semibold text-slate-400 mb-3">All Agents</h2>
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {MOCK_AGENTS.filter((a) => a.status === "idle").map((agent) => (
            <AgentCard key={agent.type} agent={agent} />
          ))}
        </div>
      </div>
    </div>
  );
}
