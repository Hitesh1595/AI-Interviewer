// REST client. Uses relative URLs so the Vite dev proxy (or FastAPI serving the
// built app in production) forwards to the backend on the same origin.

export interface CreateSessionResponse {
  id: string;
  state: string;
  config: Record<string, unknown>;
  context: {
    tech_stack: string[];
    projects: { name: string; description: string; tech: string[]; url: string }[];
    available_sources: string[];
    candidate_name: string | null;
  };
}

export interface Evaluation {
  dimension_scores: Record<string, number>;
  overall_score: number;
  strengths: string[];
  weaknesses: string[];
  summary: string;
  recommendation: string;
  move_forward: boolean;
}

// --- Admin auth token (stored in localStorage) ---
const TOKEN_KEY = "ai_admin_token";
export const getAdminToken = () => localStorage.getItem(TOKEN_KEY);
export const setAdminToken = (t: string) => localStorage.setItem(TOKEN_KEY, t);
export const clearAdminToken = () => localStorage.removeItem(TOKEN_KEY);
export const isAdmin = () => !!getAdminToken();

function adminHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const t = getAdminToken();
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra;
}

async function jsonOrThrow(res: Response) {
  if (!res.ok) {
    if (res.status === 401) clearAdminToken();
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function adminLogin(password: string): Promise<void> {
  const res = await fetch("/api/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const data = await jsonOrThrow(res);
  setAdminToken(data.token);
}

export interface InterviewConfigInput {
  role_title: string;
  candidate_name?: string | null;
  seniority: string;
  interviewer_level: string;
  duration_minutes: number;
  focus_areas: string[];
}

export async function createSession(form: FormData): Promise<CreateSessionResponse> {
  return jsonOrThrow(await fetch("/api/sessions", { method: "POST", body: form }));
}

// --- Invite (admin) / intake (candidate) flow ---

export async function createInvite(
  config: InterviewConfigInput
): Promise<{ id: string; link_path: string; config: InterviewConfigInput }> {
  return jsonOrThrow(
    await fetch("/api/invites", {
      method: "POST",
      headers: adminHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(config),
    })
  );
}

export async function getInvite(id: string): Promise<{ id: string; config: InterviewConfigInput }> {
  return jsonOrThrow(await fetch(`/api/invites/${id}`));
}

export interface InviteSummary {
  id: string;
  created_ts: number;
  config: InterviewConfigInput;
  link_path: string;
  session_count: number;
}

export interface SessionSummary {
  id: string;
  invite_id: string | null;
  created_ts: number;
  state: string;
  candidate_name: string | null;
  role_title: string | null;
  seniority: string | null;
  overall_score: number | null;
  move_forward: boolean | null;
  recommendation: string | null;
  feedback_rating: number | null;
}

export interface SessionListResponse {
  items: SessionSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface SessionQuery {
  invite_id?: string;
  state?: string;
  decision?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export async function listInvites(): Promise<InviteSummary[]> {
  return jsonOrThrow(await fetch("/api/invites", { headers: adminHeaders() }));
}

export async function listSessions(params: SessionQuery = {}): Promise<SessionListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  });
  return jsonOrThrow(await fetch(`/api/sessions?${qs.toString()}`, { headers: adminHeaders() }));
}

export async function deleteSession(id: string): Promise<void> {
  await jsonOrThrow(await fetch(`/api/sessions/${id}`, { method: "DELETE", headers: adminHeaders() }));
}

export async function deleteInvite(id: string): Promise<void> {
  await jsonOrThrow(await fetch(`/api/invites/${id}`, { method: "DELETE", headers: adminHeaders() }));
}

export async function startFromInvite(
  id: string,
  form: FormData
): Promise<CreateSessionResponse> {
  return jsonOrThrow(await fetch(`/api/invites/${id}/start`, { method: "POST", body: form }));
}

export async function finishSession(id: string): Promise<Evaluation> {
  return jsonOrThrow(await fetch(`/api/sessions/${id}/finish`, { method: "POST" }));
}

export async function getResult(id: string) {
  return jsonOrThrow(await fetch(`/api/sessions/${id}/result`, { headers: adminHeaders() }));
}

export async function submitFeedback(
  id: string,
  body: { rating: number; comment: string; would_recommend: boolean | null }
) {
  return jsonOrThrow(
    await fetch(`/api/sessions/${id}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  );
}
