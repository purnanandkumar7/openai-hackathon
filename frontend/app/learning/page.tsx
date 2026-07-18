"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import {
  BrainCircuit,
  CheckCircle2,
  TrendingUp,
  Clock,
  ThumbsUp,
  ThumbsDown,
  Minus,
  HelpCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { MOCK_LEARNING_METRICS, MOCK_INCIDENTS, MOCK_RCA_REPORT } from "@/lib/mock-data";
import { formatRelativeTime, cn } from "@/lib/utils";
import { SeverityBadge } from "@/components/ui/SeverityBadge";

// ─── Custom tooltip for recharts ──────────────────────────────────────────────

interface TooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; name: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700/60 bg-slate-900 px-3 py-2 shadow-xl text-xs">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="font-semibold text-indigo-300">
          {p.name}: {typeof p.value === "number" && p.value <= 1
            ? `${Math.round(p.value * 100)}%`
            : p.value}
        </p>
      ))}
    </div>
  );
}

// ─── Outcome icon ─────────────────────────────────────────────────────────────

function OutcomeIcon({ outcome }: { outcome: string }) {
  switch (outcome) {
    case "correct":
      return <ThumbsUp className="w-4 h-4 text-emerald-400" />;
    case "partially_correct":
      return <Minus className="w-4 h-4 text-amber-400" />;
    case "incorrect":
      return <ThumbsDown className="w-4 h-4 text-red-400" />;
    default:
      return <HelpCircle className="w-4 h-4 text-slate-500" />;
  }
}

// ─── Resolution row ───────────────────────────────────────────────────────────

const MOCK_RESOLUTIONS = MOCK_INCIDENTS.filter((i) => i.rca_id).map((inc, i) => ({
  id: `res-${i + 1}`,
  incident: inc,
  outcome: i === 0 ? "correct" : i === 1 ? "correct" : i === 2 ? "partially_correct" : "correct",
  outcome_score: [0.94, 0.88, 0.71, 0.91][i % 4],
  approved_by: "Alice Chen",
  approved_at: inc.resolved_at ?? inc.updated_at,
  notes: i === 2 ? "Root cause was correct, but timeline needed adjustment." : undefined,
}));

function ResolutionRow({
  resolution,
}: {
  resolution: (typeof MOCK_RESOLUTIONS)[0];
}) {
  const [expanded, setExpanded] = useState(false);
  const inc = resolution.incident;
  const pct = Math.round(resolution.outcome_score * 100);

  return (
    <div className="border-b border-slate-800/40 last:border-0">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-800/20 transition-colors"
      >
        <OutcomeIcon outcome={resolution.outcome} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-300 line-clamp-1">{inc.title}</p>
          <p className="text-xs text-slate-600 mt-0.5">
            Approved by {resolution.approved_by} · {formatRelativeTime(resolution.approved_at)}
          </p>
        </div>
        <SeverityBadge severity={inc.severity} size="sm" />
        <div className="flex items-center gap-2 w-24 shrink-0">
          <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full",
                pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-amber-500" : "bg-red-500"
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="text-xs font-mono text-slate-500 w-8 text-right">{pct}%</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-slate-600 shrink-0" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-slate-600 shrink-0" />
        )}
      </button>
      {expanded && resolution.notes && (
        <div className="px-10 pb-3 animate-fade-in">
          <p className="text-xs text-slate-500 bg-slate-800/30 rounded-lg px-3 py-2">
            {resolution.notes}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LearningPage() {
  const metrics = MOCK_LEARNING_METRICS;
  const total = Object.values(metrics.outcome_distribution).reduce((a, b) => a + b, 0);
  const correctPct = Math.round((metrics.outcome_distribution.correct / total) * 100);

  const outcomeData = [
    { name: "Correct", value: metrics.outcome_distribution.correct, color: "#10b981" },
    { name: "Partial", value: metrics.outcome_distribution.partially_correct, color: "#f59e0b" },
    { name: "Incorrect", value: metrics.outcome_distribution.incorrect, color: "#ef4444" },
    { name: "Unknown", value: metrics.outcome_distribution.unknown, color: "#64748b" },
  ];

  const agentPerfData = metrics.agent_performance.map((a) => ({
    name: a.agent_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    confidence: Math.round(a.avg_confidence * 100),
    failures: Math.round(a.failure_rate * 100),
  }));

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BrainCircuit className="w-6 h-6 text-indigo-400" />
            Learning Loop
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Continuous improvement metrics — RCA accuracy over time
          </p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold text-white">{correctPct}%</p>
          <p className="text-xs text-slate-500">Overall accuracy</p>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Total Incidents</span>
            <CheckCircle2 className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-2xl font-bold text-white">{metrics.total_incidents}</p>
          <p className="text-xs text-slate-600 mt-0.5">{metrics.resolved_incidents} resolved</p>
        </div>
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Avg MTTR</span>
            <Clock className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-white">{metrics.avg_resolution_time_minutes}m</p>
          <p className="text-xs text-emerald-400 mt-0.5">↓ 12m vs last month</p>
        </div>
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Avg Confidence</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white">
            {Math.round(metrics.avg_confidence_score * 100)}%
          </p>
          <p className="text-xs text-emerald-400 mt-0.5">↑ 7% vs last month</p>
        </div>
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Correct RCAs</span>
            <ThumbsUp className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white">{metrics.outcome_distribution.correct}</p>
          <p className="text-xs text-slate-600 mt-0.5">of {total} evaluated</p>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Accuracy trend line chart */}
        <div className="lg:col-span-2 rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">
            RCA Accuracy Over Time
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={metrics.accuracy_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.12)" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#64748b", fontSize: 11 }}
                tickFormatter={(v) =>
                  new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                }
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 11 }}
                tickFormatter={(v) => `${Math.round(v * 100)}%`}
                domain={[0.6, 1.0]}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="accuracy"
                stroke="#6366f1"
                strokeWidth={2.5}
                dot={{ r: 4, fill: "#6366f1", stroke: "#1e1b4b", strokeWidth: 2 }}
                activeDot={{ r: 6, fill: "#818cf8" }}
                name="Accuracy"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Outcome distribution */}
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">
            Outcome Distribution
          </h2>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={outcomeData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.08)" horizontal={false} />
              <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis dataKey="name" type="category" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} width={70} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} name="Count">
                {outcomeData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-1.5">
            {outcomeData.map((d) => (
              <div key={d.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ background: d.color }} />
                  <span className="text-slate-500">{d.name}</span>
                </div>
                <span className="text-slate-400 font-medium">
                  {d.value} ({Math.round((d.value / total) * 100)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Agent performance */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">
          Agent Performance
        </h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={agentPerfData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.12)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "#64748b", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              interval={0}
              angle={-30}
              textAnchor="end"
              height={50}
            />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="confidence" name="Avg Confidence %" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Approved resolutions */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-800/40">
          <h2 className="text-sm font-semibold text-slate-300">
            Approved Resolutions
          </h2>
          <span className="text-xs text-slate-600">
            {MOCK_RESOLUTIONS.length} evaluations
          </span>
        </div>
        <div>
          {MOCK_RESOLUTIONS.map((res) => (
            <ResolutionRow key={res.id} resolution={res} />
          ))}
        </div>
      </div>
    </div>
  );
}
