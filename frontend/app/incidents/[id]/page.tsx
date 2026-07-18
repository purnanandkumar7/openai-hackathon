"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Play,
  FileText,
  ExternalLink,
  Clock,
  Server,
  AlertTriangle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { AgentProgressFeed } from "@/components/incidents/AgentProgressFeed";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { MOCK_INCIDENTS } from "@/lib/mock-data";
import { formatDateTime, formatRelativeTime, cn } from "@/lib/utils";

export default function IncidentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const incident = MOCK_INCIDENTS.find((i) => i.id === id) ?? MOCK_INCIDENTS[0];

  const [investigationStarted, setInvestigationStarted] = useState(
    !!incident.investigation_id
  );
  const [rcaReady, setRcaReady] = useState(!!incident.rca_id);
  const [isStarting, setIsStarting] = useState(false);
  const [rcaId, setRcaId] = useState(incident.rca_id);

  const handleStartInvestigation = async () => {
    setIsStarting(true);
    await new Promise((r) => setTimeout(r, 800));
    setInvestigationStarted(true);
    setIsStarting(false);
  };

  const handleInvestigationComplete = (completedRcaId?: string) => {
    setRcaReady(true);
    setRcaId(completedRcaId ?? "rca-mock-001");
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Back nav */}
      <Link
        href="/incidents"
        className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Incidents
      </Link>

      {/* Incident header card */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex items-center gap-2.5 flex-wrap">
            <SeverityBadge severity={incident.severity} />
            <StatusIndicator status={incident.status} />
            <span className="text-xs font-mono text-slate-600">
              #{incident.id.slice(-10).toUpperCase()}
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {rcaReady && rcaId && (
              <Link
                href={`/incidents/${incident.id}/rca`}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/15 text-emerald-300 border border-emerald-500/25 text-sm font-medium hover:bg-emerald-500/25 transition-colors"
              >
                <FileText className="w-3.5 h-3.5" />
                View RCA
              </Link>
            )}
            {!investigationStarted && (
              <button
                onClick={handleStartInvestigation}
                disabled={isStarting}
                className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-semibold transition-colors shadow-lg shadow-indigo-500/20 disabled:opacity-60"
              >
                {isStarting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5" />
                )}
                {isStarting ? "Starting…" : "Investigate"}
              </button>
            )}
          </div>
        </div>

        <h1 className="text-xl font-bold text-white mb-2">{incident.title}</h1>
        <p className="text-sm text-slate-400 leading-relaxed">{incident.description}</p>

        {/* Meta grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4 pt-4 border-t border-slate-800/40">
          <div>
            <p className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">
              Created
            </p>
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Clock className="w-3 h-3 text-slate-600" />
              {formatRelativeTime(incident.created_at)}
            </div>
          </div>
          <div>
            <p className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">
              Last Updated
            </p>
            <p className="text-xs text-slate-400">{formatDateTime(incident.updated_at)}</p>
          </div>
          <div>
            <p className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">
              Affected Services
            </p>
            <div className="flex flex-wrap gap-1">
              {incident.affected_services.map((s) => (
                <span
                  key={s}
                  className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/30"
                >
                  <Server className="w-2.5 h-2.5 text-slate-600" />
                  {s}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-[10px] text-slate-600 uppercase tracking-wider mb-1">
              Severity
            </p>
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <AlertTriangle className="w-3 h-3 text-slate-600" />
              {incident.severity === "P1"
                ? "Critical"
                : incident.severity === "P2"
                ? "High"
                : incident.severity === "P3"
                ? "Medium"
                : "Low"}
            </div>
          </div>
        </div>
      </div>

      {/* Investigation area */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-bold text-white">Agent Investigation</h2>
          {investigationStarted && !rcaReady && (
            <span className="flex items-center gap-1.5 text-xs text-indigo-400">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
              Investigation in progress
            </span>
          )}
          {rcaReady && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Investigation complete
            </span>
          )}
        </div>

        {!investigationStarted ? (
          <div className="rounded-xl border border-dashed border-slate-700/50 py-16 flex flex-col items-center gap-4 text-center">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
              <Play className="w-7 h-7 text-indigo-400" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-300">
                No investigation started yet
              </p>
              <p className="text-xs text-slate-600 mt-1">
                Click &ldquo;Investigate&rdquo; to deploy all 8 AI agents on this incident
              </p>
            </div>
            <button
              onClick={handleStartInvestigation}
              disabled={isStarting}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-semibold transition-colors shadow-lg shadow-indigo-500/20 disabled:opacity-60"
            >
              {isStarting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {isStarting ? "Starting investigation…" : "Start Investigation"}
            </button>
          </div>
        ) : (
          <div className="rounded-xl border border-slate-800/60 bg-slate-900/20 p-5">
            <AgentProgressFeed
              investigationId={incident.investigation_id ?? incident.id}
              useMock={!rcaReady}
              onComplete={handleInvestigationComplete}
            />
          </div>
        )}
      </div>

      {/* RCA CTA */}
      {rcaReady && rcaId && (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 flex items-center justify-between gap-4 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center">
              <FileText className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-sm font-semibold text-emerald-300">
                Root Cause Analysis Ready
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                AI-generated RCA report with root cause, timeline, and fix recommendations
              </p>
            </div>
          </div>
          <Link
            href={`/incidents/${incident.id}/rca`}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/25 text-sm font-semibold hover:bg-emerald-500/30 transition-colors shrink-0"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Open RCA Report
          </Link>
        </div>
      )}
    </div>
  );
}
