"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Plus,
  Search,
  Filter,
  SortAsc,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { IncidentCard } from "@/components/incidents/IncidentCard";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { MOCK_INCIDENTS } from "@/lib/mock-data";
import type { Severity, IncidentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const SEVERITIES: Severity[] = ["P1", "P2", "P3", "P4"];
const STATUSES: IncidentStatus[] = ["open", "investigating", "resolved", "closed"];
const PAGE_SIZE = 6;

const statusLabels: Record<IncidentStatus, string> = {
  open: "Open",
  investigating: "Investigating",
  resolved: "Resolved",
  closed: "Closed",
};

export default function IncidentsPage() {
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<Severity[]>([]);
  const [statusFilter, setStatusFilter] = useState<IncidentStatus[]>([]);
  const [sortBy, setSortBy] = useState<"created_at" | "severity">("created_at");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    let list = [...MOCK_INCIDENTS];

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (i) =>
          i.title.toLowerCase().includes(q) ||
          i.description.toLowerCase().includes(q) ||
          i.affected_services.some((s) => s.includes(q))
      );
    }

    if (severityFilter.length > 0) {
      list = list.filter((i) => severityFilter.includes(i.severity));
    }

    if (statusFilter.length > 0) {
      list = list.filter((i) => statusFilter.includes(i.status));
    }

    list.sort((a, b) => {
      if (sortBy === "severity") {
        const order = { P1: 0, P2: 1, P3: 2, P4: 3 };
        return order[a.severity] - order[b.severity];
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

    return list;
  }, [search, severityFilter, statusFilter, sortBy]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const toggleSeverity = (s: Severity) => {
    setSeverityFilter((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
    setPage(1);
  };

  const toggleStatus = (s: IncidentStatus) => {
    setStatusFilter((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
    setPage(1);
  };

  const clearFilters = () => {
    setSeverityFilter([]);
    setStatusFilter([]);
    setSearch("");
    setPage(1);
  };

  const hasFilters =
    severityFilter.length > 0 || statusFilter.length > 0 || search.trim().length > 0;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Incidents</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {filtered.length} incident{filtered.length !== 1 ? "s" : ""}
            {hasFilters ? " matching filters" : " total"}
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

      {/* Filter bar */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-4 space-y-3">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search incidents by title, description, or service…"
            className="w-full pl-9 pr-4 py-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-all"
          />
        </div>

        {/* Filter row */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Severity filters */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-600" />
            <span className="text-xs text-slate-600">Severity:</span>
            <div className="flex gap-1">
              {SEVERITIES.map((s) => (
                <button
                  key={s}
                  onClick={() => toggleSeverity(s)}
                  className={cn(
                    "transition-all",
                    severityFilter.includes(s)
                      ? "opacity-100 scale-105"
                      : "opacity-50 hover:opacity-80"
                  )}
                >
                  <SeverityBadge severity={s} size="sm" />
                </button>
              ))}
            </div>
          </div>

          <div className="w-px h-4 bg-slate-700/50" />

          {/* Status filters */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-600">Status:</span>
            {STATUSES.map((s) => (
              <button
                key={s}
                onClick={() => toggleStatus(s)}
                className={cn(
                  "text-xs px-2.5 py-1 rounded-full border transition-all",
                  statusFilter.includes(s)
                    ? "border-indigo-500/40 bg-indigo-500/15 text-indigo-300"
                    : "border-slate-700/50 text-slate-500 hover:text-slate-300 hover:border-slate-600"
                )}
              >
                {statusLabels[s]}
              </button>
            ))}
          </div>

          <div className="w-px h-4 bg-slate-700/50 hidden sm:block" />

          {/* Sort */}
          <div className="flex items-center gap-2">
            <SortAsc className="w-3.5 h-3.5 text-slate-600" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              className="text-xs bg-transparent text-slate-500 focus:outline-none cursor-pointer hover:text-slate-300 transition-colors"
            >
              <option value="created_at">Newest first</option>
              <option value="severity">By severity</option>
            </select>
          </div>

          {/* Clear filters */}
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 ml-auto transition-colors"
            >
              <X className="w-3 h-3" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Results grid */}
      {paginated.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-20 text-slate-600">
          <Search className="w-10 h-10 opacity-30" />
          <p className="text-sm">No incidents match your filters.</p>
          <button
            onClick={clearFilters}
            className="text-xs text-indigo-400 hover:text-indigo-300"
          >
            Clear all filters
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {paginated.map((inc) => (
            <IncidentCard key={inc.id} incident={inc} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-600">
            Showing {(page - 1) * PAGE_SIZE + 1}–
            {Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Prev
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={cn(
                  "w-8 h-8 rounded-lg text-xs font-medium transition-all",
                  p === page
                    ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/25"
                    : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
                )}
              >
                {p}
              </button>
            ))}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              Next
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
