import { type Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SeverityBadgeProps {
  severity: Severity;
  className?: string;
  size?: "sm" | "md" | "lg";
}

const severityConfig: Record<
  Severity,
  { label: string; className: string; dotColor: string }
> = {
  P1: {
    label: "P1",
    className:
      "bg-red-500/15 text-red-400 border border-red-500/30",
    dotColor: "bg-red-400",
  },
  P2: {
    label: "P2",
    className:
      "bg-orange-500/15 text-orange-400 border border-orange-500/30",
    dotColor: "bg-orange-400",
  },
  P3: {
    label: "P3",
    className:
      "bg-yellow-500/15 text-yellow-400 border border-yellow-500/30",
    dotColor: "bg-yellow-400",
  },
  P4: {
    label: "P4",
    className:
      "bg-blue-500/15 text-blue-400 border border-blue-500/30",
    dotColor: "bg-blue-400",
  },
};

const sizeClasses = {
  sm: "text-[10px] px-1.5 py-0.5 gap-1",
  md: "text-xs px-2 py-1 gap-1.5",
  lg: "text-sm px-3 py-1.5 gap-2",
};

const dotSizeClasses = {
  sm: "w-1.5 h-1.5",
  md: "w-2 h-2",
  lg: "w-2.5 h-2.5",
};

export function SeverityBadge({
  severity,
  className,
  size = "md",
}: SeverityBadgeProps) {
  const config = severityConfig[severity];

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-semibold tracking-wide",
        config.className,
        sizeClasses[size],
        className
      )}
    >
      <span
        className={cn(
          "rounded-full shrink-0",
          config.dotColor,
          dotSizeClasses[size]
        )}
      />
      {config.label}
    </span>
  );
}

export function SeverityLabel({ severity }: { severity: Severity }) {
  const labels: Record<Severity, string> = {
    P1: "Critical",
    P2: "High",
    P3: "Medium",
    P4: "Low",
  };
  return <>{labels[severity]}</>;
}
