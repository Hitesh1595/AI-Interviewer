import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getInvite, startFromInvite, type InterviewConfigInput } from "../api/client";

export default function InvitePage() {
  const { inviteId = "" } = useParams();
  const navigate = useNavigate();

  const [config, setConfig] = useState<InterviewConfigInput | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  const [githubUrl, setGithubUrl] = useState("");
  const [linkedinText, setLinkedinText] = useState("");
  const [linkedinPdf, setLinkedinPdf] = useState<File | null>(null);
  const [resumePdf, setResumePdf] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getInvite(inviteId)
      .then((res) => setConfig(res.config))
      .catch((e) => setLoadErr(e.message));
  }, [inviteId]);

  const field = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";
  const labelCls = "block text-sm font-medium text-slate-700 mb-1";
  const hasSource = !!(githubUrl.trim() || linkedinText.trim() || linkedinPdf || resumePdf);

  async function handleStart(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!hasSource) return setError("Please add at least one: GitHub, LinkedIn, or a resume PDF.");

    const form = new FormData();
    if (githubUrl.trim()) form.set("github_url", githubUrl.trim());
    if (linkedinText.trim()) form.set("linkedin_text", linkedinText);
    if (linkedinPdf) form.set("linkedin_pdf", linkedinPdf);
    if (resumePdf) form.set("resume_pdf", resumePdf);

    setLoading(true);
    try {
      const res = await startFromInvite(inviteId, form);
      navigate(`/interview/${res.id}`);
    } catch (err: any) {
      setError(err.message || "Could not start the interview.");
    } finally {
      setLoading(false);
    }
  }

  if (loadErr)
    return (
      <div className="flex h-full items-center justify-center bg-slate-100 px-4 text-center text-slate-600">
        <div>This interview link is invalid or has expired.</div>
      </div>
    );

  return (
    <div className="min-h-full bg-gradient-to-b from-slate-50 to-slate-100 py-10 px-4">
      <div className="mx-auto max-w-xl">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {config?.candidate_name ? `Hi ${config.candidate_name}, you're invited!` : "You're invited to an interview"}
          </h1>
          {config && (
            <p className="mt-2 text-slate-600">
              Role: <span className="font-semibold text-slate-800">{config.role_title}</span>
              {" · "}{config.seniority} · ~{config.duration_minutes} min
              {config.focus_areas?.length ? <> · focus: {config.focus_areas.join(", ")}</> : null}
            </p>
          )}
        </div>

        <form onSubmit={handleStart} className="space-y-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <p className="text-sm text-slate-500">
            Share your profile so the interviewer can tailor questions to your work. Add at least one.
          </p>
          <div>
            <label className={labelCls}>GitHub URL</label>
            <input className={field} placeholder="https://github.com/username" value={githubUrl} onChange={(e) => setGithubUrl(e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>LinkedIn (paste About / Experience text)</label>
            <textarea className={field + " h-24 resize-y"} placeholder="Paste your LinkedIn text, or upload the PDF export below." value={linkedinText} onChange={(e) => setLinkedinText(e.target.value)} />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>LinkedIn PDF export</label>
              <input type="file" accept="application/pdf" onChange={(e) => setLinkedinPdf(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-indigo-700" />
            </div>
            <div>
              <label className={labelCls}>Resume PDF</label>
              <input type="file" accept="application/pdf" onChange={(e) => setResumePdf(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-indigo-700" />
            </div>
          </div>

          {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">{error}</div>}

          <button type="submit" disabled={loading} className="w-full rounded-lg bg-indigo-600 px-4 py-3 font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50">
            {loading ? "Preparing your interview…" : "Start interview →"}
          </button>
        </form>
      </div>
    </div>
  );
}
