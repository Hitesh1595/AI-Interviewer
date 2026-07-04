import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useRealtime } from "../hooks/useRealtime";
import { finishSession, postTranscript } from "../api/client";

function useCountdown(deadline: number | null) {
  const [remaining, setRemaining] = useState<number | null>(null);
  useEffect(() => {
    if (!deadline) return;
    const tick = () => setRemaining(Math.max(0, deadline * 1000 - Date.now()));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [deadline]);
  return remaining;
}

const fmt = (ms: number) => {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
};

export default function InterviewPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const rt = useRealtime();
  const remaining = useCountdown(rt.deadline);
  const scrollRef = useRef<HTMLDivElement>(null);
  const endedRef = useRef(false);

  // StrictMode-safe single start; tear down on unmount.
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      if (!cancelled) rt.start(id);
    }, 0);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      rt.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [rt.messages, rt.aiSpeaking]);

  // Auto-end when time runs out.
  useEffect(() => {
    if (remaining === 0 && !endedRef.current) endInterview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining]);

  async function endInterview() {
    if (endedRef.current) return;
    endedRef.current = true;
    const turns = rt.stop();
    try {
      if (turns.length) await postTranscript(id, turns);
      await finishSession(id);
    } catch {
      /* proceed to thank-you regardless */
    } finally {
      navigate(`/done/${id}`);
    }
  }

  const statusLabel =
    rt.status === "connecting"
      ? "Connecting…"
      : rt.aiSpeaking
      ? "🔊 Interviewer is speaking…"
      : rt.status === "live"
      ? "🎙️ Listening — just speak"
      : rt.status;

  return (
    <div className="flex h-full flex-col bg-slate-100">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div>
          <div className="text-sm font-semibold text-slate-900">Voice Interview</div>
          <div className="text-xs text-slate-500">{statusLabel}</div>
        </div>
        <div className="flex items-center gap-3">
          {remaining !== null && (
            <span className={`rounded-md px-2 py-1 font-mono text-sm ${remaining < 60000 ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-700"}`}>
              ⏱ {fmt(remaining)}
            </span>
          )}
          <button onClick={endInterview}
            className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700">
            End & finish
          </button>
        </div>
      </header>

      {rt.status === "error" && (
        <div className="bg-red-50 px-4 py-2 text-center text-sm text-red-700">
          {rt.error || "Voice interview unavailable."} Please check your microphone permission and try again.
        </div>
      )}

      {/* Live transcript */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto flex max-w-2xl flex-col gap-4">
          {rt.status === "connecting" && (
            <div className="text-center text-sm text-slate-400">Setting up your voice interview…</div>
          )}
          {rt.messages.map((m, i) => (
            <Bubble key={i} role={m.role} text={m.content} />
          ))}
          {rt.aiSpeaking && <Bubble role="interviewer" text="…" streaming />}
        </div>
      </div>

      {/* Voice indicator (no text input — this is a spoken interview) */}
      <div className="border-t border-slate-200 bg-white px-4 py-5">
        <div className="mx-auto flex max-w-2xl flex-col items-center gap-2">
          <div
            className={`flex h-16 w-16 items-center justify-center rounded-full text-3xl ${
              rt.aiSpeaking ? "bg-indigo-100" : rt.status === "live" ? "animate-pulse bg-emerald-100" : "bg-slate-100"
            }`}
          >
            {rt.aiSpeaking ? "🔊" : "🎙️"}
          </div>
          <div className="text-sm text-slate-500">
            {rt.status === "live" ? "Speak naturally — the interviewer is listening." : statusLabel}
          </div>
        </div>
      </div>
    </div>
  );
}

function Bubble({ role, text, streaming }: { role: string; text: string; streaming?: boolean }) {
  const isInterviewer = role === "interviewer";
  return (
    <div className={`flex ${isInterviewer ? "justify-start" : "justify-end"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
          isInterviewer
            ? "rounded-tl-sm bg-white text-slate-800 ring-1 ring-slate-200"
            : "rounded-tr-sm bg-indigo-600 text-white"
        }`}
      >
        <div className="mb-0.5 text-xs font-medium opacity-60">{isInterviewer ? "Interviewer" : "You"}</div>
        {text}
        {streaming && <span className="ml-0.5 animate-pulse">▌</span>}
      </div>
    </div>
  );
}
