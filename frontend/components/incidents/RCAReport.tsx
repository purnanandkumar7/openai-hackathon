"use client";

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
  ChevronDown,
  ChevronRight,
  Zap,
  BookOpen,
  Wrench,
  GitBranch,
  TrendingUp,
  Shield,
  ArrowRight,
} from "lucide-react";
import { type RCAReport, type FixRecommendation, type ContributingFactor } from "@/lib/types";
import { formatDateTime, cn } from "@/lib/utils";

// ─── Sub-components ───────────────────────────────────────────────────────────

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80
      ? "from-emerald-500 to-emerald-400"
      : pct >= 60
      ? "from-amber-500 to-amber-400"
      : "from-red-500 to-red-400";

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={cn("h-full bg-gradient-to-r rounded-full transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-slate-400 w-8 text-right">{pct}%</span>
    </div>
  );
}

function EffortBadge({ effort }: { effort: string }) {
  const map: Record<string, string> = {
    low: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
    medium: "bg-amber-500/15 text-amber-400 border-amber-500/20",
    high: "bg-red-500/15 text-red-400 border-red-500/20",
  };
  return (
    <span className={cn("text-[10px] px-2 py-0.5 rounded border font-medium", map[effort] ?? "bg-slate-800 text-slate-400 border-slate-700")}>
      {effort.charAt(0).toUpperCase() + effort.slice(1)} effort
    </span>
  );
}

function ImpactBadge({ impact }: { impact: string }) {
  const map: Record<string, string> = {
    high: "bg-violet-500/15 text-violet-400 border-violet-500/20",
    medium: "bg-blue-500/15 text-blue-400 border-blue-500/20",
    low: "bg-slate-500/15 text-slate-400 border-slate-500/20",
  };
  return (
    <span className={cn("text-[10px] px-2 py-0.5 rounded border font-medium", map[impact] ?? "bg-slate-800 text-slate-400 border-slate-700")}>
      {impact.charAt(0).toUpperCase() + impact.slice(1)} impact
    </span>
  );
}

function FixCard({ fix }: { fix: FixRecommendation }) {
  const [expanded, setExpanded] = useState(false);
  const typeIcon =
    fix.type === "immediate" ? (
      <Zap className="w-3.5 h-3.5 text-red-400" />
    ) : fix.type === "short_term" ? (
      <Clock className="w-3.5 h-3.5 text-amber-400" />
    ) : (
      <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
    );

  const typeLabel =
    fix.type === "immediate"
      ? "Immediate"
      : fix.type === "short_term"
      ? "Short-term"
      : "Long-term";

  const priorityColor =
    fix.priority === "critical"
      ? "text-red-400"
      : fix.priority === "high"
      ? "text-orange-400"
      : fix.priority === "medium"
      ? "text-yellow-400"
      : "text-slate-400";

  return (
    <div className="rounded-xl border border-slate-700/40 bg-slate-900/40 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 px-4 py-3.5 text-left hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-slate-800 shrink-0 mt-0.5">
          {typeIcon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-semibold text-slate-200">{fix.title}</span>
            <span className={cn("text-[10px] font-medium shrink-0", priorityColor)}>
              {fix.priority.toUpperCase()}
            </span>
          </div>
          <p className="text-xs text-slate-500 line-clamp-2">{fix.description}</p>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700/30">
              {typeLabel}
            </span>
            <EffortBadge effort={fix.effort} />
            <ImpactBadge impact={fix.impact} />
            {fix.estimated_effort && (
              <span className="text-[10px] text-slate-600">~{fix.estimated_effort}</span>
            )}
          </div>
        </div>
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-slate-600 shrink-0 mt-1" />
        ) : (
          <ChevronRight className="w-4 h-4 text-slate-600 shrink-0 mt-1" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 animate-fade-in">
          <div className="h-px bg-slate-800 mb-3" />
          <p className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
            Implementation Steps
          </p>
          <ol className="space-y-1.5">
            {fix.steps.map((step, i) => (
              <li key={i} className="flex items-start gap-2.5 text-xs text-slate-400">
                <span className="flex items-center justify-center w-4 h-4 rounded-full bg-slate-800 text-slate-500 text-[10px] font-mono shrink-0 mt-0.5">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
          {fix.owner && (
            <p className="mt-3 text-xs text-slate-600">
              Owner: <span className="text-slate-400">{fix.owner}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main RCA Report component ────────────────────────────────────────────────

interface RCAReportProps {
  report: RCAReport;
}

export function RCAReportView({ report }: RCAReportProps) {
  const [activeSection, setActiveSection] = useState<string>("summary");

  const sections = [
    { id: "summary", label: "Summary" },
    { id: "timeline", label: "Timeline" },
    { id: "root-cause", label: "Root Cause" },
    { id: "factors", label: "Contributing Factors" },
    { id: "fixes", label: "Fix Recommendations" },
    { id: "lessons", label: "Lessons Learned" },
  ];

  const scrollToSection = (id: string) => {
    setActiveSection(id);
    document.getElementById(`rca-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleExportPDF = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Report header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono text-slate-600">
              RCA-{report.id.slice(-8).toUpperCase()}
            </span>
            <span className="text-[10px] text-slate-600">·</span>
            <span className="text-[10px] text-slate-600">
              Generated {formatDateTime(report.generated_at)}
            </span>
          </div>
          <h1 className="text-xl font-bold text-white">Root Cause Analysis Report</h1>
          <p className="text-sm text-slate-400 mt-1">{report.root_cause.title}</p>
        </div>
        <button
          onClick={handleExportPDF}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 hover:bg-indigo-500/25 transition-colors text-sm font-medium shrink-0 print:hidden"
        >
          <Download className="w-4 h-4" />
          Export PDF
        </button>
      </div>

      {/* Confidence score + nav */}
      <div className="rounded-xl border border-slate-700/40 bg-slate-900/40 p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Confidence Score
          </span>
          <span className="text-xs text-slate-500">
            Based on {report.affected_services.length} services analyzed
          </span>
        </div>
        <ConfidenceBar value={report.confidence_score} />
      </div>

      {/* Section nav */}
      <div className="flex gap-1 overflow-x-auto pb-1 print:hidden">
        {sections.map((s) => (
          <button
            key={s.id}
            onClick={() => scrollToSection(s.id)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all",
              activeSection === s.id
                ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/25"
                : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* ── Executive Summary ── */}
      <section id="rca-summary" className="scroll-mt-20">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="w-4 h-4 text-indigo-400" />
          <h2 className="text-base font-bold text-white">Executive Summary</h2>
        </div>
        <div className="rounded-xl border border-slate-700/40 bg-slate-900/40 p-4">
          <p className="text-sm text-slate-300 leading-relaxed">{report.executive_summary}</p>
          <div className="mt-4 pt-4 border-t border-slate-800/60">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Impact Summary
            </p>
            <p className="text-xs text-slate-400 leading-relaxed">{report.impact_summary}</p>
          </div>
          <div className="mt-4 pt-4 border-t border-slate-800/60">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Affected Services
            </p>
            <div className="flex flex-wrap gap-1.5">
              {report.affected_services.map((svc) => (
                <span
                  key={svc}
                  className="text-xs px-2.5 py-1 rounded-lg bg-slate-800/60 text-slate-400 border border-slate-700/30"
                >
                  {svc}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Timeline ── */}
      <section id="rca-timeline" className="scroll-mt-20">
        <div className="flex items-center gap-2 mb-3">
          <Clock className="w-4 h-4 text-amber-400" />
          <h2 className="text-base font-bold text-white">Incident Timeline</h2>
        </div>
        <div className="relative pl-5">
          {/* Vertical line */}
          <div className="absolute left-2 top-2 bottom-2 w-0.5 bg-gradient-to-b from-slate-700 via-slate-700/50 to-transparent" />

          <div className="space-y-3">
            {report.timeline.map((event, i) => {
              const dot =
                event.severity === "critical"
                  ? "bg-red-400 ring-red-500/25"
                  : event.severity === "high"
                  ? "bg-orange-400 ring-orange-500/25"
                  : event.type === "incident"
                  ? "bg-rose-400 ring-rose-500/25"
                  : event.type === "recovery"
                  ? "bg-emerald-400 ring-emerald-500/25"
                  : event.type === "deployment"
                  ? "bg-blue-400 ring-blue-500/25"
                  : "bg-slate-500 ring-slate-500/25";

              return (
                <div key={event.id} className="flex items-start gap-3 animate-fade-in">
                  <div
                    className={cn(
                      "w-3.5 h-3.5 rounded-full ring-4 ring-offset-0 ring-offset-slate-950 shrink-0 mt-0.5 -ml-1.5",
                      dot
                    )}
                  />
                  <div className="flex-1 rounded-xl border border-slate-700/30 bg-slate-900/30 px-3.5 py-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-xs font-semibold text-slate-200">
                          {event.title}
                        </span>
                        {event.service && (
                          <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-500">
                            {event.service}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] font-mono text-slate-600 shrink-0">
                        {new Date(event.timestamp).toLocaleTimeString("en-US", {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">{event.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Root Cause ── */}
      <section id="rca-root-cause" className="scroll-mt-20">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <h2 className="text-base font-bold text-white">Root Cause</h2>
        </div>
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5">
          <div className="flex items-start gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-red-500/15 border border-red-500/20 shrink-0">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-bold text-red-300 mb-1">
                {report.root_cause.title}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                {report.root_cause.description}
              </p>
              <div className="flex flex-wrap gap-2 mt-3">
                <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-800/60 text-slate-300 border border-slate-700/30">
                  <span className="text-slate-500">Service: </span>
                  {report.root_cause.service}
                </span>
                {report.root_cause.component && (
                  <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-800/60 text-slate-300 border border-slate-700/30">
                    <span className="text-slate-500">Component: </span>
                    {report.root_cause.component}
                  </span>
                )}
                <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-800/60 text-slate-300 border border-slate-700/30">
                  <span className="text-slate-500">Category: </span>
                  {report.root_cause.category}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Contributing Factors ── */}
      <section id="rca-factors" className="scroll-mt-20">
        <div className="flex items-center gap-2 mb-3">
          <GitBranch className="w-4 h-4 text-violet-400" />
          <h2 className="text-base font-bold text-white">Contributing Factors</h2>
        </div>
        <div className="space-y-2">
          {report.contributing_factors.map((factor: ContributingFactor) => (
            <div
              key={factor.id}
              className="rounded-xl border border-slate-700/40 bg-slate-900/40 p-4"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <h4 className="text-sm font-semibold text-slate-200">{factor.title}</h4>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700/30 mt-1 inline-block">
                    {factor.category}
                  </span>
                </div>
                <div className="w-28 shrink-0">
                  <p className="text-[10px] text-slate-600 mb-1">Contribution weight</p>
                  <ConfidenceBar value={factor.weight} />
                </div>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed mb-2">
                {factor.description}
              </p>
              {factor.evidence.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {factor.evidence.map((e, i) => (
                    <span
                      key={i}
                      className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-slate-600 border border-slate-700/20"
                    >
                      {e}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── Fix Recommendations ── */}
      <section id="rca-fixes" className="scroll-mt-20">
        <div className="flex items-center gap-2 mb-3">
          <Wrench className="w-4 h-4 text-emerald-400" />
          <h2 className="text-base font-bold text-white">Fix Recommendations</h2>
        </div>

        {/* Group by type */}
        {(["immediate", "short_term", "long_term"] as const).map((type) => {
          const fixes = report.fix_recommendations.filter((f) => f.type === type);
          if (fixes.length === 0) return null;
          const typeLabel =
            type === "immediate" ? "Immediate Actions" : type === "short_term" ? "Short-term" : "Long-term";
          const labelColor =
            type === "immediate" ? "text-red-400" : type === "short_term" ? "text-amber-400" : "text-blue-400";
          return (
            <div key={type} className="mb-4">
              <p className={cn("text-xs font-semibold uppercase tracking-wider mb-2", labelColor)}>
                {typeLabel}
              </p>
              <div className="space-y-2">
                {fixes.map((fix) => <FixCard key={fix.id} fix={fix} />)}
              </div>
            </div>
          );
        })}
      </section>

      {/* ── Lessons Learned ── */}
      <section id="rca-lessons" className="scroll-mt-20">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="w-4 h-4 text-teal-400" />
          <h2 className="text-base font-bold text-white">Lessons Learned</h2>
        </div>
        <div className="space-y-3">
          {report.lessons_learned.map((lesson) => {
            const catColor: Record<string, string> = {
              detection: "text-blue-400 bg-blue-500/10 border-blue-500/20",
              response: "text-amber-400 bg-amber-500/10 border-amber-500/20",
              prevention: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
              process: "text-violet-400 bg-violet-500/10 border-violet-500/20",
            };
            return (
              <div
                key={lesson.id}
                className="rounded-xl border border-slate-700/40 bg-slate-900/40 p-4"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={cn(
                      "text-[10px] font-medium px-2 py-0.5 rounded border uppercase tracking-wide",
                      catColor[lesson.category] ?? "text-slate-400 bg-slate-800 border-slate-700"
                    )}
                  >
                    {lesson.category}
                  </span>
                  <h4 className="text-sm font-semibold text-slate-200">{lesson.title}</h4>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed mb-3">
                  {lesson.description}
                </p>
                <div className="space-y-1.5">
                  {lesson.action_items.map((item, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-slate-400">
                      <ArrowRight className="w-3 h-3 text-teal-500 shrink-0 mt-0.5" />
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Completion indicator */}
      <div className="flex items-center justify-center gap-2 py-6 border-t border-slate-800/40 print:hidden">
        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        <span className="text-xs text-slate-600">End of RCA Report · {formatDateTime(report.generated_at)}</span>
      </div>
    </div>
  );
}
