import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { clearAdminToken, createInvite, isAdmin } from "../api/client";

const seniorities = ["intern", "junior", "senior"];
const levels = ["supportive", "balanced", "rigorous"];

export default function AdminSetupPage() {
  const navigate = useNavigate();
  const [roleTitle, setRoleTitle] = useState("");
  const [candidateName, setCandidateName] = useState("");
  const [seniority, setSeniority] = useState("junior");
  const [level, setLevel] = useState("balanced");
  const [duration, setDuration] = useState(15);
  const [focus, setFocus] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [link, setLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const field = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";
  const labelCls = "block text-sm font-medium text-slate-700 mb-1";

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!roleTitle.trim()) return setError("Please enter the role/position.");
    setLoading(true);
    try {
      const res = await createInvite({
        role_title: roleTitle,
        candidate_name: candidateName.trim() || null,
        seniority,
        interviewer_level: level,
        duration_minutes: duration,
        focus_areas: focus.split(",").map((f) => f.trim()).filter(Boolean),
      });
      setLink(`${window.location.origin}${res.link_path}`);
    } catch (err: any) {
      setError(err.message || "Failed to create invite.");
      if (!isAdmin()) navigate("/admin/login");
    } finally {
      setLoading(false);
    }
  }

  function copy() {
    if (link) {
      navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div className="min-h-full bg-gradient-to-b from-slate-50 to-slate-100 py-10 px-4">
      <div className="mx-auto max-w-2xl">
        <div className="mb-4 flex justify-end gap-4">
          <Link to="/admin" className="text-sm text-indigo-600 hover:underline">📊 Dashboard</Link>
          <button onClick={() => { clearAdminToken(); navigate("/admin/login"); }} className="text-sm text-slate-500 hover:underline">Sign out</button>
        </div>
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">🤖 AI Interviewer · Admin</h1>
          <p className="mt-2 text-slate-600">
            Configure the interview, then share the link with your candidate.
          </p>
        </div>

        {link ? (
          <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <h2 className="text-lg font-semibold text-slate-900">✅ Invite ready</h2>
            <p className="mt-1 text-sm text-slate-600">
              Send this link to the candidate. They'll add their resume/links and the interview begins.
            </p>
            <div className="mt-4 flex gap-2">
              <input readOnly value={link} className={field + " font-mono text-xs"} />
              <button onClick={copy} className="whitespace-nowrap rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <div className="mt-4 flex gap-3">
              <a href={link} target="_blank" rel="noreferrer" className="text-sm text-indigo-600 hover:underline">
                Open candidate page →
              </a>
              <button onClick={() => setLink(null)} className="text-sm text-slate-500 hover:underline">
                Create another
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleCreate} className="space-y-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className={labelCls}>Candidate name</label>
                <input className={field} placeholder="e.g. Alex Johnson" value={candidateName} onChange={(e) => setCandidateName(e.target.value)} />
              </div>
              <div>
                <label className={labelCls}>Role / position *</label>
                <input className={field} placeholder="e.g. Backend Engineer" value={roleTitle} onChange={(e) => setRoleTitle(e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className={labelCls}>Seniority</label>
                <select className={field} value={seniority} onChange={(e) => setSeniority(e.target.value)}>
                  {seniorities.map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Interviewer style</label>
                <select className={field} value={level} onChange={(e) => setLevel(e.target.value)}>
                  {levels.map((l) => <option key={l} value={l}>{l[0].toUpperCase() + l.slice(1)}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Duration (minutes)</label>
                <input type="number" min={1} max={60} className={field} value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
              </div>
              <div>
                <label className={labelCls}>Focus areas (comma separated)</label>
                <input className={field} placeholder="APIs, databases" value={focus} onChange={(e) => setFocus(e.target.value)} />
              </div>
            </div>

            {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">{error}</div>}

            <button type="submit" disabled={loading} className="w-full rounded-lg bg-indigo-600 px-4 py-3 font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50">
              {loading ? "Creating…" : "Generate invite link →"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
