import { type IncidentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

interface StatusIndicatorProps {
  status: IncidentStatus;
  className?: string;
  showLabel?: boolean;
  size?: "sm" | "md";
}

const statusConfig: Record<
  IncidentStatus,
  { label: string; dotColor: string; badgeClass: string; pulseColor: string }
> = {
  open: {
    label: "Open",
    dotColor: "bg-red-400",
    badgeClass: "bg-red-500/15 text-red-400 border border-red-500/25",
    pulseColor: "bg-red-400",
  },
  investigating: {
    label: "Investigating",
    dotColor: "bg-amber-400",
    badgeClass: "bg-amber-500/15 text-amber-400 border border-amber-500/25",
    pulseColor: "bg-amber-400",
  },
  resolved: {
    label: "Resolved",
    dotColor: "bg-emerald-400",
    badgeClass: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25",
    pulseColor: "bg-emerald-400",
  },
  closed: {
    label: "Closed",
    dotColor: "bg-slate-400",
    badgeClass: "bg-slate-500/15 text-slate-400 border border-slate-500/25",
    pulseColor: "bg-slate-400",
  },
};

const activeStatuses: IncidentStatus[] = ["open", "investigating"];

export function StatusIndicator({
  status,
  className,
  showLabel = true,
  size = "md",
}: StatusIndicatorProps) {
  const config = statusConfig[status];
  const isActive = activeStatuses.includes(status);

  const dotSize = size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2";
  const textSize = size === "sm" ? "text-[10px]" : "text-xs";
  const padding = size === "sm" ? "px-1.5 py-0.5 gap-1" : "px-2.5 py-1 gap-1.5";

  if (!showLabel) {
    return (
      <span className={cn("relative flex items-center", className)}>
        {isActive && (
          <span
            className={cn(
              "absolute inline-flex rounded-full opacity-75 animate-ping",
              config.pulseColor,
              dotSize
            )}
          />
        )}
        <span className={cn("relative inline-flex rounded-full", config.dotColor, dotSize)} />
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        config.badgeClass,
        padding,
        textSize,
        className
      )}
    >
      <span className="relative flex items-center">
        {isActive && (
          <span
            className={cn(
              "absolute inline-flex rounded-full opacity-75 animate-ping",
              config.pulseColor,
              dotSize
            )}
          />
        )}
        <span className={cn("relative inline-flex rounded-full", config.dotColor, dotSize)} />
      </span>
      {config.label}
    </span>
  );
}
