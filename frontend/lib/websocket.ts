import { useEffect, useRef, useCallback, useState } from "react";
import type { WSEvent, WSEventType, AgentRun, AgentFinding, AgentType } from "./types";

// ─── Connection state ─────────────────────────────────────────────────────────

export type WSConnectionState = "connecting" | "connected" | "disconnected" | "error";

// ─── Hook ─────────────────────────────────────────────────────────────────────

interface UseAgentProgressOptions {
  investigationId: string | null;
  enabled?: boolean;
  onEvent?: (event: WSEvent) => void;
}

export interface AgentProgressState {
  agentRuns: Record<string, AgentRun>;
  events: WSEvent[];
  connectionState: WSConnectionState;
  isCompleted: boolean;
  isFailed: boolean;
  rcaId?: string;
}

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export function useAgentProgress({
  investigationId,
  enabled = true,
  onEvent,
}: UseAgentProgressOptions): AgentProgressState {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT = 5;

  const [state, setState] = useState<AgentProgressState>({
    agentRuns: {},
    events: [],
    connectionState: "disconnected",
    isCompleted: false,
    isFailed: false,
  });

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      let wsEvent: WSEvent;
      try {
        wsEvent = JSON.parse(event.data as string) as WSEvent;
      } catch {
        console.error("[WS] Failed to parse message", event.data);
        return;
      }

      onEvent?.(wsEvent);

      setState((prev) => {
        const newEvents = [...prev.events, wsEvent];
        const newAgentRuns = { ...prev.agentRuns };
        let isCompleted = prev.isCompleted;
        let isFailed = prev.isFailed;
        let rcaId = prev.rcaId;

        switch (wsEvent.type) {
          case "agent_started": {
            const { agent_type, agent_run_id } = wsEvent.data;
            if (agent_type && agent_run_id) {
              newAgentRuns[agent_run_id] = {
                id: agent_run_id,
                investigation_id: wsEvent.investigation_id,
                agent_type: agent_type as AgentType,
                status: "running",
                started_at: wsEvent.timestamp,
                findings: [],
                progress: 0,
              };
            }
            break;
          }

          case "agent_progress": {
            const { agent_run_id, progress } = wsEvent.data;
            if (agent_run_id && newAgentRuns[agent_run_id]) {
              newAgentRuns[agent_run_id] = {
                ...newAgentRuns[agent_run_id],
                progress: progress ?? newAgentRuns[agent_run_id].progress,
              };
            }
            break;
          }

          case "agent_finding": {
            const { agent_run_id, finding } = wsEvent.data;
            if (agent_run_id && finding && newAgentRuns[agent_run_id]) {
              const run = newAgentRuns[agent_run_id];
              newAgentRuns[agent_run_id] = {
                ...run,
                findings: [...run.findings, finding as AgentFinding],
              };
            }
            break;
          }

          case "agent_completed": {
            const { agent_run_id, agent_run } = wsEvent.data;
            const runId = agent_run_id ?? agent_run?.id;
            if (runId && newAgentRuns[runId]) {
              newAgentRuns[runId] = {
                ...newAgentRuns[runId],
                ...(agent_run ?? {}),
                status: "completed",
                completed_at: wsEvent.timestamp,
                progress: 100,
              };
            }
            break;
          }

          case "agent_failed": {
            const { agent_run_id, error } = wsEvent.data;
            if (agent_run_id && newAgentRuns[agent_run_id]) {
              newAgentRuns[agent_run_id] = {
                ...newAgentRuns[agent_run_id],
                status: "failed",
                error,
                completed_at: wsEvent.timestamp,
              };
            }
            break;
          }

          case "investigation_completed": {
            isCompleted = true;
            rcaId = wsEvent.data.rca_id;
            break;
          }

          case "investigation_failed": {
            isFailed = true;
            break;
          }
        }

        return {
          agentRuns: newAgentRuns,
          events: newEvents,
          connectionState: prev.connectionState,
          isCompleted,
          isFailed,
          rcaId,
        };
      });
    },
    [onEvent]
  );

  const connect = useCallback(() => {
    if (!investigationId || !enabled) return;

    setState((prev) => ({ ...prev, connectionState: "connecting" }));

    const wsUrl = `${WS_BASE}/ws/investigations/${investigationId}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      setState((prev) => ({ ...prev, connectionState: "connected" }));
    };

    ws.onmessage = handleMessage;

    ws.onerror = () => {
      setState((prev) => ({ ...prev, connectionState: "error" }));
    };

    ws.onclose = (ev) => {
      setState((prev) => ({
        ...prev,
        connectionState: "disconnected",
      }));

      // Reconnect unless we closed cleanly or exhausted retries
      if (
        ev.code !== 1000 &&
        reconnectAttemptsRef.current < MAX_RECONNECT &&
        enabled
      ) {
        const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 30000);
        reconnectAttemptsRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, delay);
      }
    };
  }, [investigationId, enabled, handleMessage]);

  useEffect(() => {
    if (!investigationId || !enabled) return;
    connect();

    return () => {
      reconnectTimerRef.current && clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close(1000, "component unmounted");
    };
  }, [investigationId, enabled, connect]);

  return state;
}

// ─── Utility: mock WS event emitter for demo ─────────────────────────────────

export function createMockWSEmitter(
  investigationId: string,
  onEvent: (e: WSEvent) => void
): () => void {
  const agentSequence: AgentType[] = [
    "log_analyzer",
    "metric_analyzer",
    "trace_analyzer",
    "dependency_mapper",
    "hypothesis_generator",
    "evidence_collector",
    "rca_synthesizer",
    "fix_recommender",
  ];

  const emit = (type: WSEventType, data: WSEvent["data"]) => {
    onEvent({
      type,
      investigation_id: investigationId,
      timestamp: new Date().toISOString(),
      data,
    });
  };

  let cancelled = false;
  let agentIndex = 0;

  const tick = () => {
    if (cancelled || agentIndex >= agentSequence.length) {
      if (!cancelled) emit("investigation_completed", { rca_id: "rca-mock-001" });
      return;
    }

    const agent = agentSequence[agentIndex];
    const runId = `run-${agent}-${Date.now()}`;
    emit("agent_started", { agent_type: agent, agent_run_id: runId });

    let progress = 0;
    const progressInterval = setInterval(() => {
      if (cancelled) { clearInterval(progressInterval); return; }
      progress = Math.min(progress + 20, 80);
      emit("agent_progress", { agent_run_id: runId, progress });
    }, 300);

    setTimeout(() => {
      clearInterval(progressInterval);
      if (cancelled) return;
      emit("agent_finding", {
        agent_run_id: runId,
        finding: {
          id: `finding-${runId}`,
          agent_type: agent,
          title: `Finding from ${agent.replace(/_/g, " ")}`,
          description: "Anomalous pattern detected in service response times.",
          confidence: 0.85,
          evidence: ["spike at 14:32 UTC", "p99 latency > 2000ms"],
          timestamp: new Date().toISOString(),
        },
      });
      emit("agent_completed", { agent_run_id: runId, progress: 100 });
      agentIndex += 1;
      setTimeout(tick, 600);
    }, 1800);
  };

  setTimeout(tick, 500);

  return () => { cancelled = true; };
}
