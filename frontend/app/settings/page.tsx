import type { Metadata } from "next";
import {
  Settings,
  Bell,
  Shield,
  Webhook,
  Sliders,
  ExternalLink,
  Save,
} from "lucide-react";

export const metadata: Metadata = { title: "Settings" };

function SettingRow({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-4 border-b border-slate-800/40 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-300">{label}</p>
        {description && (
          <p className="text-xs text-slate-600 mt-0.5">{description}</p>
        )}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function Toggle({ defaultOn = false }: { defaultOn?: boolean }) {
  return (
    <div
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${
        defaultOn ? "bg-indigo-500" : "bg-slate-700"
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
          defaultOn ? "translate-x-4" : "translate-x-1"
        }`}
      />
    </div>
  );
}

export default function SettingsPage() {
  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Settings className="w-6 h-6 text-slate-400" />
          Settings
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Configure Atlas AI for your environment
        </p>
      </div>

      {/* API Configuration */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Webhook className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-300">API Configuration</h2>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              API Base URL
            </label>
            <input
              type="text"
              defaultValue="http://localhost:8000"
              className="w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              WebSocket URL
            </label>
            <input
              type="text"
              defaultValue="ws://localhost:8000"
              className="w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              API Key (optional)
            </label>
            <input
              type="password"
              placeholder="sk-atlas-…"
              className="w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 transition-all"
            />
          </div>
        </div>
      </div>

      {/* Investigation Settings */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Sliders className="w-4 h-4 text-violet-400" />
          <h2 className="text-sm font-semibold text-slate-300">Investigation Settings</h2>
        </div>
        <SettingRow
          label="Auto-investigate P1 incidents"
          description="Automatically start investigation when a P1 incident is created"
        >
          <Toggle defaultOn={true} />
        </SettingRow>
        <SettingRow
          label="Auto-investigate P2 incidents"
          description="Automatically start investigation for P2 severity incidents"
        >
          <Toggle defaultOn={false} />
        </SettingRow>
        <SettingRow
          label="Run all agents in parallel"
          description="When enabled, independent agents run concurrently for faster analysis"
        >
          <Toggle defaultOn={true} />
        </SettingRow>
        <SettingRow
          label="Confidence threshold"
          description="Minimum confidence score required to surface a finding (0–100)"
        >
          <input
            type="number"
            defaultValue={65}
            min={0}
            max={100}
            className="w-20 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-300 text-center focus:outline-none focus:border-indigo-500/50 transition-all"
          />
        </SettingRow>
      </div>

      {/* Notifications */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Bell className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-slate-300">Notifications</h2>
        </div>
        <SettingRow label="P1 incident alerts" description="Immediate notification on P1 creation">
          <Toggle defaultOn={true} />
        </SettingRow>
        <SettingRow label="Investigation complete" description="Notify when RCA report is ready">
          <Toggle defaultOn={true} />
        </SettingRow>
        <SettingRow label="Agent failure alerts" description="Alert when an agent encounters an error">
          <Toggle defaultOn={false} />
        </SettingRow>
        <SettingRow label="Slack webhook URL" description="Post notifications to a Slack channel">
          <input
            type="text"
            placeholder="https://hooks.slack.com/…"
            className="w-64 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 transition-all"
          />
        </SettingRow>
      </div>

      {/* Security */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-slate-300">Security</h2>
        </div>
        <SettingRow label="Require approval for fix execution" description="Fixes must be manually approved before any automated action">
          <Toggle defaultOn={true} />
        </SettingRow>
        <SettingRow label="Audit logging" description="Log all agent actions and API calls">
          <Toggle defaultOn={true} />
        </SettingRow>
      </div>

      {/* About */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-3">About Atlas AI</h2>
        <div className="space-y-2 text-xs text-slate-600">
          <p>Version: <span className="text-slate-400">0.1.0</span></p>
          <p>Build: <span className="text-slate-400 font-mono">main-a1b2c3d</span></p>
          <div className="flex items-center gap-4 mt-3">
            <a href="https://github.com/atlas-ai" className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors">
              GitHub <ExternalLink className="w-3 h-3" />
            </a>
            <a href="#" className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors">
              Docs <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>

      {/* Save button */}
      <div className="flex justify-end">
        <button className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-semibold transition-colors shadow-lg shadow-indigo-500/20">
          <Save className="w-4 h-4" />
          Save Settings
        </button>
      </div>
    </div>
  );
}
