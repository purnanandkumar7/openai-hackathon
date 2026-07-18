"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Plus,
  X,
  Loader2,
  AlertTriangle,
  Server,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/types";

const SEVERITY_OPTIONS: { value: Severity; label: string; desc: string; color: string }[] = [
  { value: "P1", label: "P1 — Critical", desc: "Complete service outage or data loss", color: "border-red-500/40 bg-red-500/10 text-red-300" },
  { value: "P2", label: "P2 — High",     desc: "Significant degradation, revenue impact", color: "border-orange-500/40 bg-orange-500/10 text-orange-300" },
  { value: "P3", label: "P3 — Medium",   desc: "Partial degradation, workaround available", color: "border-yellow-500/40 bg-yellow-500/10 text-yellow-300" },
  { value: "P4", label: "P4 — Low",      desc: "Minor issue, no user impact", color: "border-blue-500/40 bg-blue-500/10 text-blue-300" },
];

const KNOWN_SERVICES = [
  "payment-service",
  "auth-service",
  "order-service",
  "checkout-ui",
  "recommendation-engine",
  "notification-service",
  "product-service",
  "api-gateway",
  "cdn",
  "asset-server",
  "elasticsearch",
  "kafka",
  "graphql-gateway",
];

export default function NewIncidentPage() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState<Severity>("P2");
  const [services, setServices] = useState<string[]>([]);
  const [serviceInput, setServiceInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const addService = (svc: string) => {
    const trimmed = svc.trim();
    if (!trimmed) return;
    if (!services.includes(trimmed)) {
      setServices((prev) => [...prev, trimmed]);
    }
    setServiceInput("");
  };

  const removeService = (svc: string) => {
    setServices((prev) => prev.filter((s) => s !== svc));
  };

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!title.trim()) errs.title = "Title is required";
    if (title.trim().length < 10) errs.title = "Title must be at least 10 characters";
    if (!description.trim()) errs.description = "Description is required";
    if (services.length === 0) errs.services = "At least one affected service is required";
    return errs;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }

    setIsSubmitting(true);
    setErrors({});

    try {
      // In production: await incidentsApi.create({ title, description, severity, affected_services: services });
      await new Promise((r) => setTimeout(r, 1200));
      // Redirect to the incidents list with the new incident
      router.push("/incidents");
    } catch (err) {
      setErrors({ submit: "Failed to create incident. Please try again." });
    } finally {
      setIsSubmitting(false);
    }
  };

  const suggestions = KNOWN_SERVICES.filter(
    (s) =>
      serviceInput.trim() &&
      s.includes(serviceInput.toLowerCase()) &&
      !services.includes(s)
  ).slice(0, 5);

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      {/* Back nav */}
      <Link
        href="/incidents"
        className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Incidents
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">New Incident</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Create an incident to begin AI-powered investigation
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Global error */}
        {errors.submit && (
          <div className="flex items-center gap-2 px-4 py-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {errors.submit}
          </div>
        )}

        {/* Title */}
        <div>
          <label className="block text-sm font-semibold text-slate-300 mb-1.5">
            <span className="flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-slate-500" />
              Incident Title
            </span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. payment-service high error rate — HTTP 503s spiking"
            className={cn(
              "w-full px-4 py-3 rounded-xl bg-slate-900/60 border text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-1 transition-all",
              errors.title
                ? "border-red-500/50 focus:border-red-500/60 focus:ring-red-500/20"
                : "border-slate-700/50 focus:border-indigo-500/50 focus:ring-indigo-500/20"
            )}
          />
          {errors.title && (
            <p className="text-xs text-red-400 mt-1">{errors.title}</p>
          )}
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-semibold text-slate-300 mb-1.5">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            placeholder="Describe the symptoms, impact, and any initial observations…"
            className={cn(
              "w-full px-4 py-3 rounded-xl bg-slate-900/60 border text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-1 transition-all resize-none",
              errors.description
                ? "border-red-500/50 focus:border-red-500/60 focus:ring-red-500/20"
                : "border-slate-700/50 focus:border-indigo-500/50 focus:ring-indigo-500/20"
            )}
          />
          {errors.description && (
            <p className="text-xs text-red-400 mt-1">{errors.description}</p>
          )}
        </div>

        {/* Severity */}
        <div>
          <label className="block text-sm font-semibold text-slate-300 mb-2">
            Severity
          </label>
          <div className="grid grid-cols-2 gap-2">
            {SEVERITY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setSeverity(opt.value)}
                className={cn(
                  "flex flex-col gap-0.5 px-4 py-3 rounded-xl border text-left transition-all",
                  severity === opt.value
                    ? opt.color + " ring-1 ring-offset-0"
                    : "border-slate-700/50 bg-slate-900/30 hover:border-slate-600"
                )}
              >
                <span className="text-sm font-semibold">{opt.label}</span>
                <span className="text-xs opacity-70">{opt.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Affected services */}
        <div>
          <label className="block text-sm font-semibold text-slate-300 mb-1.5">
            <span className="flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-slate-500" />
              Affected Services
            </span>
          </label>

          {/* Selected services */}
          {services.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {services.map((svc) => (
                <span
                  key={svc}
                  className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/25"
                >
                  {svc}
                  <button
                    type="button"
                    onClick={() => removeService(svc)}
                    className="text-indigo-400 hover:text-red-400 transition-colors ml-0.5"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Input + autocomplete */}
          <div className="relative">
            <input
              type="text"
              value={serviceInput}
              onChange={(e) => setServiceInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addService(serviceInput);
                }
                if (e.key === "," || e.key === " ") {
                  e.preventDefault();
                  addService(serviceInput);
                }
              }}
              placeholder="Type a service name and press Enter…"
              className={cn(
                "w-full px-4 py-3 rounded-xl bg-slate-900/60 border text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-1 transition-all",
                errors.services
                  ? "border-red-500/50 focus:border-red-500/60 focus:ring-red-500/20"
                  : "border-slate-700/50 focus:border-indigo-500/50 focus:ring-indigo-500/20"
              )}
            />

            {suggestions.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 rounded-xl bg-slate-900 border border-slate-700/60 shadow-xl z-20 overflow-hidden">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => addService(s)}
                    className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors text-left"
                  >
                    <Plus className="w-3.5 h-3.5 text-slate-600" />
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>

          {errors.services && (
            <p className="text-xs text-red-400 mt-1">{errors.services}</p>
          )}
          <p className="text-xs text-slate-600 mt-1.5">
            Press Enter or comma to add a service. You can add custom service names.
          </p>
        </div>

        {/* Submit */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-semibold transition-colors shadow-lg shadow-indigo-500/20 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating…
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                Create Incident
              </>
            )}
          </button>
          <Link
            href="/incidents"
            className="px-4 py-2.5 rounded-xl text-sm text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 transition-colors"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
