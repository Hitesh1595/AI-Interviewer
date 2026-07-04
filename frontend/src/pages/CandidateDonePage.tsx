import { useState } from "react";
import { useParams } from "react-router-dom";
import { submitFeedback } from "../api/client";

// Candidate-facing completion screen. Deliberately shows NO score/summary —
// the evaluation is for the admin only. We just thank them and collect feedback.
export default function CandidateDonePage() {
  const { id = "" } = useParams();
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [recommend, setRecommend] = useState<boolean | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    if (!rating) return setErr("Please pick a star rating.");
    setBusy(true);
    setErr(null);
    try {
      await submitFeedback(id, { rating, comment, would_recommend: recommend });
      setDone(true);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-full bg-gradient-to-b from-slate-50 to-slate-100 py-12 px-4">
      <div className="mx-auto max-w-lg">
        <div className="mb-6 text-center">
          <div className="text-5xl">🎉</div>
          <h1 className="mt-3 text-2xl font-bold text-slate-900">Interview complete</h1>
          <p className="mt-2 text-slate-600">
            Thanks for your time! Your responses have been recorded and the hiring team
            will review them. We'll be in touch about next steps.
          </p>
        </div>

        {done ? (
          <div className="rounded-2xl bg-emerald-50 p-6 text-center text-emerald-800 ring-1 ring-emerald-200">
            🙏 Thank you for your feedback — it helps us improve the interview experience.
          </div>
        ) : (
          <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <h2 className="font-semibold text-slate-800">How was your experience?</h2>
            <p className="mt-1 text-sm text-slate-500">
              Your feedback helps us mature this AI interviewer.
            </p>

            <div className="mt-4 flex gap-1 text-3xl">
              {[1, 2, 3, 4, 5].map((n) => (
                <button key={n} onMouseEnter={() => setHover(n)} onMouseLeave={() => setHover(0)} onClick={() => setRating(n)}>
                  <span className={(hover || rating) >= n ? "text-amber-400" : "text-slate-300"}>★</span>
                </button>
              ))}
            </div>

            <textarea
              className="mt-4 h-28 w-full resize-y rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              placeholder="What felt good? What was confusing? What should we improve?"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />

            <div className="mt-3 flex items-center gap-4 text-sm text-slate-600">
              <span>Would you recommend this experience?</span>
              <label className="flex items-center gap-1">
                <input type="radio" name="rec" onChange={() => setRecommend(true)} /> Yes
              </label>
              <label className="flex items-center gap-1">
                <input type="radio" name="rec" onChange={() => setRecommend(false)} /> No
              </label>
            </div>

            {err && <div className="mt-3 text-sm text-red-600">{err}</div>}

            <button
              onClick={submit}
              disabled={busy}
              className="mt-4 w-full rounded-lg bg-indigo-600 px-5 py-2.5 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {busy ? "Submitting…" : "Submit feedback"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
