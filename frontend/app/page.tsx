import type { Metadata } from "next";
import Link from "next/link";
import {
  AlertTriangle,
  TrendingDown,
  Activity,
  Clock,
  Plus,
  ChevronRight,
  Flame,
  Wifi,
  Server,
  CheckCircle2,
} from "lucide-react";
import { IncidentCard } from "@/components/incidents/IncidentCard";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import {
  MOCK_INCIDENTS,
  MOCK_DASHBOARD_STATS,
} from "@/lib/mock-data";
import { formatRelativeTime, cn } from "@/lib/utils";
import type { Severity } from "@/lib/types";

export const metadata: Metadata = { title: "Dashboard" };

// ─── Stat Card ────────────────────────────────────────────────────────────────

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.FC<{ className?: string }>;
  iconColor: string;
  iconBg: string;
  trend?: { value: string; positive: boolean };
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconColor,
  iconBg,
  trend,
}: StatCardProps) {
  return (
    <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
            {title}
          </p>
          <p className="text-3xl font-bold text-white">{value}</p>
          {subtitle && (
            <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
          )}
          {trend && (
            <p
              className={cn(
                "text-xs mt-1 font-medium",
                trend.positive ? "text-emerald-400" : "text-red-400"
              )}
            >
              {trend.positive ? "↑" : "↓"} {trend.value}
            </p>
          )}
        </div>
        <div
          className={cn(
            "flex items-center justify-center w-11 h-11 rounded-xl",
            iconBg
          )}
        >
          <Icon className={cn("w-5 h-5", iconColor)} />
        </div>
      </div>
    </div>
  );
}

// ─── System Health ────────────────────────────────────────────────────────────

const services = [
  { name: "payment-service",       health: "degraded",  latency: "284ms",  uptime: "98.2%" },
  { name: "auth-service",          health: "degraded",  latency: "412ms",  uptime: "97.8%" },
  { name: "order-service",         health: "healthy",   latency: "42ms",   uptime: "99.9%" },
  { name: "checkout-ui",           health: "healthy",   latency: "31ms",   uptime: "99.7%" },
  { name: "recommendation-engine", health: "critical",  latency: "N/A",    uptime: "89.1%" },
  { name: "notification-service",  health: "healthy",   latency: "18ms",   uptime: "99.9%" },
];

function ServiceHealthRow({
  name,
  health,
  latency,
  uptime,
}: (typeof services)[0]) {
  const dot =
    health === "healthy"
      ? "bg-emerald-400"
      : health === "degraded"
      ? "bg-amber-400"
      : "bg-red-400";
  const label =
    health === "healthy"
      ? "text-emerald-400"
      : health === "degraded"
      ? "text-amber-400"
      : "text-red-400";

  return (
    <div className="flex items-center justify-between py-2.5 border-b border-slate-800/40 last:border-0">
      <div className="flex items-center gap-2.5">
        <div className={cn("w-2 h-2 rounded-full", dot)} />
        <span className="text-sm text-slate-300 font-mono">{name}</span>
      </div>
      <div className="flex items-center gap-6">
        <span className="text-xs font-mono text-slate-600 w-16 text-right">
          {latency}
        </span>
        <span className="text-xs font-mono text-slate-600 w-12 text-right">
          {uptime}
        </span>
        <span className={cn("text-xs font-medium w-16 text-right", label)}>
          {health}
        </span>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const stats = MOCK_DASHBOARD_STATS;
  const activeIncidents = MOCK_INCIDENTS.filter(
    (i) => i.status === "open" || i.status === "investigating"
  );
  const recentIncidents = MOCK_INCIDENTS.slice(0, 6);

  const severityOrder: Severity[] = ["P1", "P2", "P3", "P4"];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">

      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time incident intelligence overview
          </p>
        </div>
        <Link
          href="/incidents/new"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-semibold transition-colors shadow-lg shadow-indigo-500/20"
        >
          <Plus className="w-4 h-4" />
          New Incident
        </Link>
      </div>

      {/* System health banner */}
      {stats.system_health !== "healthy" && (
        <div
          className={cn(
            "flex items-center gap-3 px-4 py-3 rounded-xl border text-sm",
            stats.system_health === "critical"
              ? "border-red-500/30 bg-red-500/10 text-red-300"
              : "border-amber-500/30 bg-amber-500/10 text-amber-300"
          )}
        >
          <Flame className="w-4 h-4 shrink-0" />
          <span className="font-semibold">
            System status:{" "}
            <span className="capitalize">{stats.system_health}</span>
          </span>
          <span className="text-slate-500">—</span>
          <span className="text-xs">
            {stats.total_open} active incident
            {stats.total_open !== 1 ? "s" : ""} ·{" "}
            {stats.active_investigations} investigation
            {stats.active_investigations !== 1 ? "s" : ""} in progress
          </span>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Open Incidents"
          value={stats.total_open}
          subtitle={`${stats.active_investigations} investigating`}
          icon={AlertTriangle}
          iconColor="text-red-400"
          iconBg="bg-red-500/10"
        />
        <StatCard
          title="Resolved Today"
          value={stats.resolved_today}
          subtitle="last 24 hours"
          icon={CheckCircle2}
          iconColor="text-emerald-400"
          iconBg="bg-emerald-500/10"
          trend={{ value: "+2 vs yesterday", positive: true }}
        />
        <StatCard
          title="Avg MTTR"
          value={`${stats.avg_mttr_minutes}m`}
          subtitle="mean time to resolve"
          icon={Clock}
          iconColor="text-indigo-400"
          iconBg="bg-indigo-500/10"
          trend={{ value: "12m faster this week", positive: true }}
        />
        <StatCard
          title="Active Agents"
          value={stats.active_investigations * 3}
          subtitle={`across ${stats.active_investigations} investigations`}
          icon={Activity}
          iconColor="text-violet-400"
          iconBg="bg-violet-500/10"
        />
      </div>

      {/* Severity breakdown */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">
          Open Incidents by Severity
        </h2>
        <div className="grid grid-cols-4 gap-3">
          {severityOrder.map((sev) => {
            const count = stats.by_severity[sev] ?? 0;
            const maxCount = Math.max(...Object.values(stats.by_severity));
            const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
            return (
              <div key={sev} className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <SeverityBadge severity={sev} size="sm" />
                  <span className="text-lg font-bold text-white">{count}</span>
                </div>
                <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      sev === "P1"
                        ? "bg-red-500"
                        : sev === "P2"
                        ? "bg-orange-500"
                        : sev === "P3"
                        ? "bg-yellow-500"
                        : "bg-blue-500"
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid lg:grid-cols-2 gap-6">

        {/* Active investigations */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Wifi className="w-4 h-4 text-indigo-400" />
              Active Investigations
            </h2>
            <Link
              href="/incidents?status=investigating"
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5 transition-colors"
            >
              View all
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          {activeIncidents.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-800 py-10 text-center text-slate-600 text-sm">
              No active investigations
            </div>
          ) : (
            <div className="space-y-3">
              {activeIncidents.map((inc) => (
                <IncidentCard key={inc.id} incident={inc} compact />
              ))}
            </div>
          )}
        </div>

        {/* System Health */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Server className="w-4 h-4 text-slate-400" />
              Service Health
            </h2>
            <div className="flex gap-3 text-[10px] text-slate-600">
              <span>Latency</span>
              <span>Uptime</span>
              <span className="w-14 text-right">Status</span>
            </div>
          </div>
          <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 px-4 py-1">
            {services.map((svc) => (
              <ServiceHealthRow key={svc.name} {...svc} />
            ))}
          </div>
        </div>
      </div>

      {/* Recent Incidents Table */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-slate-400" />
            Recent Incidents
          </h2>
          <Link
            href="/incidents"
            className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5 transition-colors"
          >
            View all
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800/60">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Incident
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden sm:table-cell">
                  Severity
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden md:table-cell">
                  Services
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden lg:table-cell">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {recentIncidents.map((inc) => (
                <tr
                  key={inc.id}
                  className="hover:bg-slate-800/30 transition-colors group"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/incidents/${inc.id}`}
                      className="block"
                    >
                      <p className="text-sm font-medium text-slate-200 group-hover:text-white transition-colors line-clamp-1">
                        {inc.title}
                      </p>
                      <p className="text-[10px] font-mono text-slate-600 mt-0.5">
                        #{inc.id.slice(-8).toUpperCase()}
                      </p>
                    </Link>
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <SeverityBadge severity={inc.severity} size="sm" />
                  </td>
                  <td className="px-4 py-3">
                    <StatusIndicator status={inc.status} size="sm" />
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <div className="flex gap-1 flex-wrap">
                      {inc.affected_services.slice(0, 2).map((s) => (
                        <span
                          key={s}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700/30"
                        >
                          {s}
                        </span>
                      ))}
                      {inc.affected_services.length > 2 && (
                        <span className="text-[10px] text-slate-600">
                          +{inc.affected_services.length - 2}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell text-xs text-slate-600 whitespace-nowrap">
                    {formatRelativeTime(inc.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
