import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { RCAReportView } from "@/components/incidents/RCAReport";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { MOCK_INCIDENTS, MOCK_RCA_REPORT } from "@/lib/mock-data";
import type { Metadata } from "next";

interface PageProps {
  params: { id: string };
}

export function generateMetadata({ params }: PageProps): Metadata {
  const incident = MOCK_INCIDENTS.find((i) => i.id === params.id);
  return {
    title: incident ? `RCA: ${incident.title}` : "RCA Report",
  };
}

export default function RCAPage({ params }: PageProps) {
  const incident = MOCK_INCIDENTS.find((i) => i.id === params.id);

  // Fallback to first incident if not found (for demo)
  const inc = incident ?? MOCK_INCIDENTS[0];

  // In production this would be fetched from the API using inc.rca_id
  const report = { ...MOCK_RCA_REPORT, incident_id: inc.id };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-4">
      {/* Back nav */}
      <div className="flex items-center justify-between">
        <Link
          href={`/incidents/${inc.id}`}
          className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Incident
        </Link>
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <SeverityBadge severity={inc.severity} size="sm" />
          <span className="font-mono">#{inc.id.slice(-8).toUpperCase()}</span>
        </div>
      </div>

      <RCAReportView report={report} />
    </div>
  );
}
