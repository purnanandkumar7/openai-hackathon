"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  Bell,
  Search,
  ChevronRight,
  Settings,
  LogOut,
  User,
  Moon,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Breadcrumb builder ───────────────────────────────────────────────────────

function buildBreadcrumbs(pathname: string) {
  const segments = pathname.split("/").filter(Boolean);
  const crumbs = [{ label: "Home", href: "/" }];

  const labelMap: Record<string, string> = {
    incidents: "Incidents",
    agents: "Agents",
    learning: "Learning",
    settings: "Settings",
    new: "New Incident",
    rca: "RCA Report",
  };

  let path = "";
  for (const seg of segments) {
    path += `/${seg}`;
    const label =
      labelMap[seg] ??
      (seg.length === 36 || seg.match(/^[a-z0-9-]{8,}$/)
        ? `#${seg.slice(0, 8)}`
        : seg.charAt(0).toUpperCase() + seg.slice(1));
    crumbs.push({ label, href: path });
  }
  return crumbs;
}

// ─── Notification mock ────────────────────────────────────────────────────────

const MOCK_NOTIFICATIONS = [
  {
    id: "1",
    title: "P1 Incident Created",
    message: "payment-service: high error rate detected",
    time: "2m ago",
    read: false,
  },
  {
    id: "2",
    title: "Investigation Complete",
    message: "RCA available for INC-2041",
    time: "8m ago",
    read: false,
  },
  {
    id: "3",
    title: "Agent Degraded",
    message: "log_analyzer reporting elevated failure rate",
    time: "1h ago",
    read: true,
  },
];

// ─── Component ────────────────────────────────────────────────────────────────

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const pathname = usePathname();
  const crumbs = buildBreadcrumbs(pathname);
  const unreadCount = MOCK_NOTIFICATIONS.filter((n) => !n.read).length;

  return (
    <header
      className={cn(
        "flex items-center justify-between h-14 px-6 border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-30",
        className
      )}
    >
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1.5 text-sm">
        {crumbs.map((crumb, i) => (
          <span key={crumb.href} className="flex items-center gap-1.5">
            {i > 0 && (
              <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
            )}
            {i === crumbs.length - 1 ? (
              <span className="font-medium text-slate-200">{crumb.label}</span>
            ) : (
              <Link
                href={crumb.href}
                className="text-slate-500 hover:text-slate-300 transition-colors"
              >
                {crumb.label}
              </Link>
            )}
          </span>
        ))}
      </nav>

      {/* Right side actions */}
      <div className="flex items-center gap-2">
        {/* Search button */}
        <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50 text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-all text-xs">
          <Search className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Search</span>
          <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-700/50 text-slate-500 border border-slate-600/30">
            ⌘K
          </kbd>
        </button>

        {/* Notifications */}
        <div className="relative group">
          <button className="relative flex items-center justify-center w-8 h-8 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all">
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-indigo-500 border border-slate-950" />
            )}
          </button>

          {/* Dropdown */}
          <div className="absolute right-0 top-full mt-1 w-80 rounded-xl bg-slate-900 border border-slate-700/60 shadow-2xl shadow-black/50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-50">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/40">
              <span className="text-sm font-semibold text-slate-200">Notifications</span>
              {unreadCount > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/20">
                  {unreadCount} new
                </span>
              )}
            </div>
            <div className="divide-y divide-slate-800/50">
              {MOCK_NOTIFICATIONS.map((n) => (
                <div
                  key={n.id}
                  className={cn(
                    "px-4 py-3 hover:bg-slate-800/40 cursor-pointer transition-colors",
                    !n.read && "bg-indigo-500/5"
                  )}
                >
                  <div className="flex items-start gap-2">
                    {!n.read && (
                      <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                    )}
                    <div className={cn(!n.read ? "" : "ml-3.5")}>
                      <p className="text-xs font-semibold text-slate-200">{n.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{n.message}</p>
                      <p className="text-[10px] text-slate-600 mt-1">{n.time}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="px-4 py-2.5 border-t border-slate-700/40">
              <button className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
                View all notifications
              </button>
            </div>
          </div>
        </div>

        {/* Dark mode indicator */}
        <button className="flex items-center justify-center w-8 h-8 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all">
          <Moon className="w-4 h-4" />
        </button>

        {/* User avatar + menu */}
        <div className="relative group ml-1">
          <button className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-800 transition-all">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 flex items-center justify-center text-[11px] font-bold text-white">
              A
            </div>
          </button>

          {/* User dropdown */}
          <div className="absolute right-0 top-full mt-1 w-48 rounded-xl bg-slate-900 border border-slate-700/60 shadow-2xl shadow-black/50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-50">
            <div className="px-3 py-3 border-b border-slate-700/40">
              <p className="text-sm font-semibold text-slate-200">Admin User</p>
              <p className="text-xs text-slate-500">admin@atlas.ai</p>
            </div>
            <div className="p-1.5 space-y-0.5">
              <button className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors">
                <User className="w-3.5 h-3.5" />
                Profile
              </button>
              <button className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors">
                <Settings className="w-3.5 h-3.5" />
                Settings
              </button>
              <button className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors">
                <LogOut className="w-3.5 h-3.5" />
                Sign out
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
