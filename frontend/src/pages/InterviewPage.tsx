import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useInterviewSocket } from "../hooks/useInterviewSocket";
import { useSpeech } from "../hooks/useSpeech";
import { finishSession } from "../api/client";

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

function fmt(ms: number) {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export default function InterviewPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const socket = useInterviewSocket(id);
  const speech = useSpeech();

  const [input, setInput] = useState("");
  const [typeMode, setTypeMode] = useState(!speech.supported); // voice-first; text is fallback
  const [voiceOn, setVoiceOn] = useState(speech.supported);
  const [ending, setEnding] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const remaining = useCountdown(socket.deadline);

  const sendRef = useRef(socket.send);
  sendRef.current = socket.send;

  // Voice-first loop: speak each interviewer message, then auto-listen for the
  // candidate's spoken answer and send it automatically.
  useEffect(() => {
    socket.onInterviewerDone.current = (text: string) => {
      if (!voiceOn) return;
      speech.speak(text, () => {
        if (!typeMode) speech.listen((answer) => sendRef.current(answer));
      });
    };
  }, [voiceOn, typeMode, speech, socket.onInterviewerDone]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [socket.messages, socket.streaming]);

  useEffect(() => {
    if (socket.evaluation) navigate(`/done/${id}`);
  }, [socket.evaluation, id, navigate]);

  useEffect(() => {
    if (remaining === 0 && !ending) handleEnd();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining]);

  function sendText() {
    if (!input.trim()) return;
    speech.cancelSpeech();
    socket.send(input.trim());
    setInput("");
  }

  function toggleMic() {
    speech.cancelSpeech();
    if (speech.listening) speech.stop();
    else speech.listen((answer) => sendRef.current(answer));
  }

  async function handleEnd() {
    setEnding(true);
    speech.cancelSpeech();
    speech.stop();
    try {
      socket.finish();
      await finishSession(id);
    } catch {
      /* ignore */
    } finally {
      navigate(`/done/${id}`);
    }
  }

  const speaking = typeof window !== "undefined" && "speechSynthesis" in window && window.speechSynthesis.speaking;

  return (
    <div className="flex h-full flex-col bg-slate-100">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div>
          <div className="text-sm font-semibold text-slate-900">Live Interview</div>
          <div className="text-xs text-slate-500">
            {socket.connected ? "● connected" : "○ connecting…"} · phase: {socket.interviewState}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {remaining !== null && (
            <span className={`rounded-md px-2 py-1 font-mono text-sm ${remaining < 60000 ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-700"}`}>
              ⏱ {fmt(remaining)}
            </span>
          )}
          <label className="flex items-center gap-1 text-sm text-slate-600">
            <input type="checkbox" checked={voiceOn} disabled={!speech.supported}
              onChange={(e) => { setVoiceOn(e.target.checked); if (!e.target.checked) speech.cancelSpeech(); }} />
            🔊 Voice
          </label>
          <button onClick={handleEnd} disabled={ending}
            className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">
            End
          </button>
        </div>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto flex max-w-2xl flex-col gap-4">
          {socket.messages.map((m, i) => (
            <Bubble key={i} role={m.role} text={m.content} />
          ))}
          {socket.streaming && <Bubble role="interviewer" text={socket.streaming} streaming />}
          {socket.error && (
            <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{socket.error}</div>
          )}
        </div>
      </div>

      {/* Voice-first composer */}
      <div className="border-t border-slate-200 bg-white px-4 py-4">
        <div className="mx-auto max-w-2xl">
          {!typeMode ? (
            <div className="flex flex-col items-center gap-3">
              <button
                onClick={toggleMic}
                disabled={!speech.supported}
                className={`flex h-20 w-20 items-center justify-center rounded-full text-3xl shadow-md transition disabled:opacity-40 ${
                  speech.listening ? "animate-pulse bg-red-500 text-white" : "bg-indigo-600 text-white hover:bg-indigo-700"
                }`}
                title={speech.listening ? "Listening… tap to stop" : "Tap and speak your answer"}
              >
                {speech.listening ? "🔴" : "🎤"}
              </button>
              <div className="text-sm text-slate-600">
                {speaking
                  ? "🔊 Interviewer is speaking…"
                  : speech.listening
                  ? "Listening — speak your answer"
                  : "Tap the mic and answer by voice"}
              </div>
              <button onClick={() => setTypeMode(true)} className="text-xs text-slate-400 hover:underline">
                Type instead
              </button>
            </div>
          ) : (
            <div className="flex items-end gap-2">
              <textarea
                className="h-12 max-h-40 flex-1 resize-y rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                placeholder="Type your answer… (Enter to send)"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendText();
                  }
                }}
              />
              <button onClick={sendText} className="rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700">
                Send
              </button>
              {speech.supported && (
                <button onClick={() => setTypeMode(false)} className="rounded-lg bg-slate-100 px-3 py-2 text-lg" title="Back to voice">
                  🎤
                </button>
              )}
            </div>
          )}
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
        <div className="mb-0.5 text-xs font-medium opacity-60">
          {isInterviewer ? "Interviewer" : "You"}
        </div>
        {text}
        {streaming && <span className="ml-0.5 animate-pulse">▌</span>}
      </div>
    </div>
  );
}
