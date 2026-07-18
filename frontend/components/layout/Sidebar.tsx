"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertTriangle,
  Bot,
  BrainCircuit,
  Settings,
  Zap,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navLinks = [
  {
    href: "/",
    label: "Dashboard",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    href: "/incidents",
    label: "Incidents",
    icon: AlertTriangle,
    badge: null,
  },
  {
    href: "/agents",
    label: "Agents",
    icon: Bot,
  },
  {
    href: "/learning",
    label: "Learning",
    icon: BrainCircuit,
  },
  {
    href: "/settings",
    label: "Settings",
    icon: Settings,
  },
];

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();

  const isActive = (href: string, exact?: boolean) => {
    if (exact) return pathname === href;
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <aside
      className={cn(
        "flex flex-col w-64 min-h-screen bg-slate-950 border-r border-slate-800/60",
        className
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-800/60">
        <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/25">
          <Zap className="w-5 h-5 text-white" />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-bold text-white tracking-tight">
            Atlas AI
          </span>
          <span className="text-[10px] text-slate-500 font-medium tracking-wider uppercase">
            Incident Intelligence
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <p className="px-3 py-2 text-[10px] font-semibold text-slate-600 tracking-widest uppercase">
          Navigation
        </p>
        {navLinks.map((link) => {
          const active = isActive(link.href, link.exact);
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                active
                  ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              )}
            >
              <Icon
                className={cn(
                  "w-4 h-4 shrink-0 transition-colors",
                  active ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300"
                )}
              />
              <span className="flex-1">{link.label}</span>
              {active && (
                <ChevronRight className="w-3 h-3 text-indigo-500 opacity-60" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-slate-800/60">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-slate-900/50">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 flex items-center justify-center text-[11px] font-bold text-white shrink-0">
            A
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-xs font-semibold text-slate-300 truncate">
              Admin User
            </span>
            <span className="text-[10px] text-slate-600 truncate">
              admin@atlas.ai
            </span>
          </div>
        </div>

        <p className="mt-3 px-1 text-[10px] text-slate-700 text-center">
          Atlas AI v0.1.0 · MIT License
        </p>
      </div>
    </aside>
  );
}
