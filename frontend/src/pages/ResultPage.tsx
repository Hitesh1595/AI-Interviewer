import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getResult, type Evaluation } from "../api/client";

const DIM_LABELS: Record<string, string> = {
  technical_depth: "Technical depth",
  problem_solving: "Problem solving",
  communication: "Communication",
  experience_relevance: "Experience relevance",
  behavioral: "Behavioral / culture",
};

export default function ResultPage() {
  const { id = "" } = useParams();
  const [data, setData] = useState<{
    evaluation: Evaluation;
    config: any;
    context?: any;
    feedback: any;
    transcript?: { role: string; content: string }[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let tries = 0;
    async function poll() {
      try {
        const res = await getResult(id);
        if (!cancelled) setData(res);
      } catch (e: any) {
        // 409 = evaluation not ready; retry a few times.
        if (tries++ < 10 && !cancelled) setTimeout(poll, 1500);
        else if (!cancelled) setError(e.message);
      }
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) return <Centered>{error} — <Link className="text-indigo-600 underline" to="/">start over</Link></Centered>;
  if (!data) return <Centered>Scoring the interview…</Centered>;

  const ev = data.evaluation;
  const scoreColor = ev.overall_score >= 7 ? "text-emerald-600" : ev.overall_score >= 5 ? "text-amber-600" : "text-red-600";

  return (
    <div className="min-h-full bg-slate-100 py-10 px-4">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-indigo-500">Admin view</div>
            <h1 className="text-2xl font-bold text-slate-900">Interview Result</h1>
          </div>
          <Link to="/" className="text-sm text-indigo-600 hover:underline">← New interview</Link>
        </div>

        {/* Verdict card */}
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-sm text-slate-500">
                {data.config.candidate_name ? `${data.config.candidate_name} · ` : ""}{data.config.role_title} · {data.config.seniority}
              </div>
              <div className={`mt-1 text-5xl font-bold ${scoreColor}`}>
                {ev.overall_score.toFixed(1)}<span className="text-2xl text-slate-400">/10</span>
              </div>
            </div>
            <div className="text-right">
              <span className={`inline-block rounded-full px-4 py-2 text-sm font-semibold ${
                ev.move_forward ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}>
                {ev.move_forward ? "✓ Move forward" : "✕ Do not move forward"}
              </span>
              <div className="mt-1 text-xs uppercase tracking-wide text-slate-400">
                Recommendation: {ev.recommendation.replace("_", " ")}
              </div>
            </div>
          </div>
          <p className="mt-4 text-slate-700">{ev.summary}</p>
        </div>

        {/* Dimension bars */}
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-4 font-semibold text-slate-800">Scorecard</h2>
          <div className="space-y-3">
            {Object.entries(ev.dimension_scores).map(([k, v]) => (
              <div key={k}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="text-slate-600">{DIM_LABELS[k] ?? k}</span>
                  <span className="font-medium text-slate-800">{v.toFixed(1)}</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div className="h-2 rounded-full bg-indigo-500" style={{ width: `${(v / 10) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Strengths / weaknesses */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <ListCard title="Strengths" items={ev.strengths} titleClass="text-emerald-700" />
          <ListCard title="Areas to improve" items={ev.weaknesses} titleClass="text-amber-700" />
        </div>

        {/* Candidate profile that was used */}
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-3 font-semibold text-slate-800">Candidate profile used</h2>
          <div className="text-sm text-slate-600">
            <div className="mb-2">
              Sources: {(data.context?.available_sources || []).join(", ") || "none"}
              {data.config?.focus_areas?.length ? <> · Focus: {data.config.focus_areas.join(", ")}</> : null}
            </div>
            {data.context?.tech_stack?.length ? (
              <div className="flex flex-wrap gap-1.5">
                {data.context.tech_stack.slice(0, 30).map((t: string) => (
                  <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">{t}</span>
                ))}
              </div>
            ) : (
              <span className="text-slate-400">No tech signals extracted.</span>
            )}
          </div>
        </div>

        {/* Full conversation transcript */}
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-3 font-semibold text-slate-800">
            Conversation <span className="text-sm font-normal text-slate-400">({data.transcript?.length || 0} turns)</span>
          </h2>
          {data.transcript?.length ? (
            <div className="flex flex-col gap-3">
              {data.transcript.map((t, i) => (
                <div key={i} className={`flex ${t.role === "interviewer" ? "justify-start" : "justify-end"}`}>
                  <div className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${
                    t.role === "interviewer" ? "bg-slate-100 text-slate-800" : "bg-indigo-600 text-white"}`}>
                    <div className="mb-0.5 text-xs font-medium opacity-60">{t.role === "interviewer" ? "Interviewer" : "Candidate"}</div>
                    {t.content}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400">No transcript recorded.</p>
          )}
        </div>

        {/* Candidate feedback (read-only, for admin) */}
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-2 font-semibold text-slate-800">Candidate feedback</h2>
          {data.feedback ? (
            <div className="space-y-1 text-sm text-slate-700">
              <div>Rating: <span className="text-amber-500">{"★".repeat(data.feedback.rating)}</span>{"☆".repeat(5 - data.feedback.rating)} ({data.feedback.rating}/5)</div>
              {data.feedback.would_recommend !== null && (
                <div>Would recommend: {data.feedback.would_recommend ? "Yes" : "No"}</div>
              )}
              {data.feedback.comment && <div className="text-slate-600">“{data.feedback.comment}”</div>}
            </div>
          ) : (
            <p className="text-sm text-slate-400">No feedback submitted yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function ListCard({ title, items, titleClass }: { title: string; items: string[]; titleClass: string }) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <h3 className={`mb-3 font-semibold ${titleClass}`}>{title}</h3>
      <ul className="space-y-1.5 text-sm text-slate-700">
        {items.length ? items.map((s, i) => <li key={i}>• {s}</li>) : <li className="text-slate-400">None noted.</li>}
      </ul>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center bg-slate-100 px-4 text-center text-slate-600">
      <div>{children}</div>
    </div>
  );
}
