import type {
  Incident,
  CreateIncidentPayload,
  Investigation,
  RCAReport,
  Resolution,
  LearningMetrics,
  PaginatedResponse,
  DashboardStats,
  AgentInfo,
} from "./types";

// ─── Base config ─────────────────────────────────────────────────────────────

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    let message = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      message = body.detail ?? body.message ?? message;
    } catch {
      // ignore parse errors
    }
    throw new Error(message);
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as unknown as T;
  }

  return res.json() as Promise<T>;
}

// ─── Incidents ────────────────────────────────────────────────────────────────

export const incidentsApi = {
  list(params?: {
    page?: number;
    page_size?: number;
    severity?: string;
    status?: string;
    search?: string;
  }): Promise<PaginatedResponse<Incident>> {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    if (params?.severity) qs.set("severity", params.severity);
    if (params?.status) qs.set("status", params.status);
    if (params?.search) qs.set("search", params.search);
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return request<PaginatedResponse<Incident>>(`/api/incidents${query}`);
  },

  get(id: string): Promise<Incident> {
    return request<Incident>(`/api/incidents/${id}`);
  },

  create(payload: CreateIncidentPayload): Promise<Incident> {
    return request<Incident>("/api/incidents", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  update(id: string, payload: Partial<CreateIncidentPayload>): Promise<Incident> {
    return request<Incident>(`/api/incidents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  delete(id: string): Promise<void> {
    return request<void>(`/api/incidents/${id}`, { method: "DELETE" });
  },

  triggerInvestigation(id: string): Promise<Investigation> {
    return request<Investigation>(`/api/incidents/${id}/investigate`, {
      method: "POST",
    });
  },
};

// ─── Investigations ───────────────────────────────────────────────────────────

export const investigationsApi = {
  get(investigationId: string): Promise<Investigation> {
    return request<Investigation>(`/api/investigations/${investigationId}`);
  },

  getByIncident(incidentId: string): Promise<Investigation | null> {
    return request<Investigation | null>(
      `/api/incidents/${incidentId}/investigation`
    );
  },
};

// ─── RCA ──────────────────────────────────────────────────────────────────────

export const rcaApi = {
  get(rcaId: string): Promise<RCAReport> {
    return request<RCAReport>(`/api/rca/${rcaId}`);
  },

  getByIncident(incidentId: string): Promise<RCAReport | null> {
    return request<RCAReport | null>(`/api/incidents/${incidentId}/rca`);
  },
};

// ─── Resolutions / Learning ───────────────────────────────────────────────────

export const resolutionsApi = {
  list(params?: {
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Resolution>> {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return request<PaginatedResponse<Resolution>>(`/api/resolutions${query}`);
  },

  approve(
    id: string,
    payload: { outcome: string; notes?: string; feedback?: string }
  ): Promise<Resolution> {
    return request<Resolution>(`/api/resolutions/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getMetrics(): Promise<LearningMetrics> {
    return request<LearningMetrics>("/api/learning/metrics");
  },
};

// ─── Agents ───────────────────────────────────────────────────────────────────

export const agentsApi = {
  list(): Promise<AgentInfo[]> {
    return request<AgentInfo[]>("/api/agents");
  },
};

// ─── Dashboard ────────────────────────────────────────────────────────────────

export const dashboardApi = {
  getStats(): Promise<DashboardStats> {
    return request<DashboardStats>("/api/dashboard/stats");
  },
};
