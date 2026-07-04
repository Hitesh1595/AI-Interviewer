import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  clearAdminToken,
  isAdmin,
  deleteInvite,
  deleteSession,
  listInvites,
  listSessions,
  type InviteSummary,
  type SessionSummary,
} from "../api/client";

const PAGE_SIZE = 10;
const STATES = ["greeting", "questioning", "wrap_up", "complete"];

function fmtDate(ts: number) {
  return new Date(ts * 1000).toLocaleString();
}

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const [invites, setInvites] = useState<InviteSummary[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Filters + pagination
  const [q, setQ] = useState("");
  const [state, setState] = useState("");
  const [decision, setDecision] = useState("");
  const [inviteFilter, setInviteFilter] = useState("");
  const [page, setPage] = useState(0);

  const loadInvites = useCallback(async () => {
    try {
      setInvites(await listInvites());
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listSessions({
        q: q || undefined,
        state: state || undefined,
        decision: decision || undefined,
        invite_id: inviteFilter || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });
      setSessions(res.items);
      setTotal(res.total);
    } catch (e: any) {
      setError(e.message);
      if (!isAdmin()) navigate("/admin/login");
    } finally {
      setLoading(false);
    }
  }, [q, state, decision, inviteFilter, page, navigate]);

  useEffect(() => {
    loadInvites();
  }, [loadInvites]);

  // Debounce filter changes; reset to page 0 when filters change.
  useEffect(() => {
    const t = setTimeout(loadSessions, 250);
    return () => clearTimeout(t);
  }, [loadSessions]);

  function resetPageAnd(setter: (v: string) => void) {
    return (v: string) => {
      setPage(0);
      setter(v);
    };
  }

  function copyLink(inv: InviteSummary) {
    navigator.clipboard.writeText(`${window.location.origin}${inv.link_path}`);
    setCopiedId(inv.id);
    setTimeout(() => setCopiedId(null), 1500);
  }

  async function onDeleteInvite(inv: InviteSummary) {
    if (!confirm(`Delete invite for "${inv.config.role_title}" and its ${inv.session_count} session(s)? This cannot be undone.`)) return;
    try {
      await deleteInvite(inv.id);
      if (inviteFilter === inv.id) setInviteFilter("");
      await Promise.all([loadInvites(), loadSessions()]);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function onDeleteSession(s: SessionSummary) {
    if (!confirm(`Delete this interview${s.candidate_name ? ` with ${s.candidate_name}` : ""}? This cannot be undone.`)) return;
    try {
      await deleteSession(s.id);
      await Promise.all([loadInvites(), loadSessions()]);
    } catch (e: any) {
      setError(e.message);
    }
  }

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const selectCls = "rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none";

  return (
    <div className="min-h-full bg-slate-100 py-10 px-4">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">📊 Admin Dashboard</h1>
          <div className="flex items-center gap-3">
            <button onClick={() => { loadInvites(); loadSessions(); }} className="text-sm text-slate-500 hover:underline">↻ Refresh</button>
            <button onClick={() => { clearAdminToken(); navigate("/admin/login"); }} className="text-sm text-slate-500 hover:underline">Sign out</button>
            <Link to="/" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">＋ New interview</Link>
          </div>
        </div>

        {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">{error}</div>}

        {/* Invites */}
        <div className="mb-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-3 font-semibold text-slate-800">Invites</h2>
          {invites.length === 0 ? (
            <div className="text-sm text-slate-400">No invites yet. <Link to="/" className="text-indigo-600 hover:underline">Create one →</Link></div>
          ) : (
            <div className="space-y-2">
              {invites.map((inv) => (
                <div key={inv.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2">
                  <div className="min-w-0">
                    <div className="truncate font-medium text-slate-800">
                      {inv.config.candidate_name ? `${inv.config.candidate_name} — ` : ""}{inv.config.role_title}
                    </div>
                    <div className="text-xs text-slate-500">
                      {inv.config.seniority} · {inv.session_count} session(s) · {fmtDate(inv.created_ts)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => setInviteFilter(inviteFilter === inv.id ? "" : inv.id)}
                      className={`rounded-md px-2.5 py-1 text-xs font-medium ${inviteFilter === inv.id ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
                      {inviteFilter === inv.id ? "Filtering ✓" : "Filter"}
                    </button>
                    <button onClick={() => copyLink(inv)} className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200">
                      {copiedId === inv.id ? "Copied!" : "Copy link"}
                    </button>
                    <button onClick={() => onDeleteInvite(inv)} className="rounded-md bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-100">
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sessions + filters */}
        <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <h2 className="mr-auto font-semibold text-slate-800">Interviews</h2>
            <input value={q} onChange={(e) => resetPageAnd(setQ)(e.target.value)} placeholder="Search candidate…" className={selectCls + " w-44"} />
            <select value={state} onChange={(e) => resetPageAnd(setState)(e.target.value)} className={selectCls}>
              <option value="">All statuses</option>
              {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={decision} onChange={(e) => resetPageAnd(setDecision)(e.target.value)} className={selectCls}>
              <option value="">All decisions</option>
              <option value="forward">Move forward</option>
              <option value="no">No</option>
              <option value="pending">Pending</option>
            </select>
            {inviteFilter && (
              <button onClick={() => setInviteFilter("")} className="rounded-md bg-slate-100 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-200">
                Clear invite filter ✕
              </button>
            )}
          </div>

          {loading ? (
            <div className="py-6 text-center text-slate-400">Loading…</div>
          ) : sessions.length === 0 ? (
            <div className="py-6 text-center text-slate-400">No interviews match these filters.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400">
                    <th className="py-2 pr-3">Candidate</th>
                    <th className="py-2 pr-3">Role</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Score</th>
                    <th className="py-2 pr-3">Decision</th>
                    <th className="py-2 pr-3">Feedback</th>
                    <th className="py-2 pr-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s) => {
                    const done = s.state === "complete" && s.overall_score !== null;
                    return (
                      <tr key={s.id} className="border-b border-slate-100 last:border-0">
                        <td className="py-2 pr-3 font-medium text-slate-800">{s.candidate_name || <span className="text-slate-400">Unknown</span>}</td>
                        <td className="py-2 pr-3 text-slate-600">{s.role_title}</td>
                        <td className="py-2 pr-3 text-slate-600">{s.state}</td>
                        <td className="py-2 pr-3">{done ? <span className="font-semibold">{s.overall_score?.toFixed(1)}/10</span> : "—"}</td>
                        <td className="py-2 pr-3">
                          {s.move_forward === null ? "—" : (
                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${s.move_forward ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}>
                              {s.move_forward ? "Move forward" : "No"}
                            </span>
                          )}
                        </td>
                        <td className="py-2 pr-3 text-amber-500">{s.feedback_rating ? "★".repeat(s.feedback_rating) : <span className="text-slate-300">—</span>}</td>
                        <td className="py-2 pr-3">
                          <div className="flex gap-3">
                            {done && <Link to={`/result/${s.id}`} className="text-indigo-600 hover:underline">View</Link>}
                            <button onClick={() => onDeleteSession(s)} className="text-red-600 hover:underline">Delete</button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
            <span>{total} result{total === 1 ? "" : "s"}</span>
            <div className="flex items-center gap-2">
              <button disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}
                className="rounded-md border border-slate-200 px-3 py-1 disabled:opacity-40">← Prev</button>
              <span>Page {page + 1} of {pageCount}</span>
              <button disabled={page + 1 >= pageCount} onClick={() => setPage((p) => p + 1)}
                className="rounded-md border border-slate-200 px-3 py-1 disabled:opacity-40">Next →</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
