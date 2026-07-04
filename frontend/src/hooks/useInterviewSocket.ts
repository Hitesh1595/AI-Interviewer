import { useEffect, useRef, useState } from "react";
import type { Evaluation } from "../api/client";

export interface ChatMessage {
  role: "interviewer" | "candidate";
  content: string;
}

export function useInterviewSocket(id: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const bufferRef = useRef("");
  // Callback fired when a full interviewer message completes (used for TTS).
  const onInterviewerDone = useRef<((text: string) => void) | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState("");
  const [interviewState, setInterviewState] = useState("greeting");
  const [deadline, setDeadline] = useState<number | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // StrictMode-safe: schedule the connect on a macrotask. React's dev
    // double-mount clears this timer on the throwaway pass BEFORE it fires, so
    // exactly one socket is ever created (no "closed before established" error).
    let cancelled = false;
    const timer = setTimeout(() => {
      if (cancelled) return;
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${location.host}/api/ws/interview/${id}`);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);
      ws.onerror = () => setError("Connection error");
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        switch (msg.type) {
          case "state":
            setInterviewState(msg.state);
            if (msg.deadline_ts) setDeadline(msg.deadline_ts);
            break;
          case "history":
            if (Array.isArray(msg.turns) && msg.turns.length) {
              setMessages(msg.turns.map((t: any) => ({ role: t.role, content: t.content })));
            }
            break;
          case "interviewer_token":
            bufferRef.current += msg.token;
            setStreaming(bufferRef.current);
            break;
          case "done": {
            const text = bufferRef.current.trim();
            bufferRef.current = "";
            setStreaming("");
            if (text) {
              setMessages((m) => [...m, { role: "interviewer", content: text }]);
              onInterviewerDone.current?.(text);
            }
            break;
          }
          case "evaluation_ready":
            setEvaluation(msg.evaluation);
            break;
          case "error":
            setError(msg.detail);
            break;
        }
      };
    }, 0);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) ws.close();
      wsRef.current = null;
    };
  }, [id]);

  const send = (content: string) => {
    if (!content.trim()) return;
    setMessages((m) => [...m, { role: "candidate", content }]);
    wsRef.current?.send(JSON.stringify({ type: "candidate_msg", content }));
  };

  const finish = () => wsRef.current?.send(JSON.stringify({ type: "finish" }));

  return {
    messages,
    streaming,
    interviewState,
    deadline,
    evaluation,
    connected,
    error,
    send,
    finish,
    onInterviewerDone,
  };
}
