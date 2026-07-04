import { useCallback, useRef, useState } from "react";
import { getRealtimeToken } from "../api/client";

export interface RtMessage {
  role: "interviewer" | "candidate";
  content: string;
}

type Status = "idle" | "connecting" | "live" | "ended" | "error";

// Drives an OpenAI Realtime voice interview over WebRTC. The browser connects
// directly to OpenAI with a short-lived token minted by our backend; mic audio
// streams up, the AI voice plays natively, and transcripts arrive as events.
export function useRealtime() {
  const [messages, setMessages] = useState<RtMessage[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [deadline, setDeadline] = useState<number | null>(null);
  const [aiSpeaking, setAiSpeaking] = useState(false);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const messagesRef = useRef<RtMessage[]>([]);
  const partialRef = useRef("");

  const push = (m: RtMessage) => {
    messagesRef.current = [...messagesRef.current, m];
    setMessages(messagesRef.current);
  };

  const handleEvent = (ev: any) => {
    switch (ev.type) {
      case "response.output_audio_transcript.delta":
      case "response.audio_transcript.delta":
        partialRef.current += ev.delta || "";
        setAiSpeaking(true);
        break;
      case "response.output_audio_transcript.done":
      case "response.audio_transcript.done": {
        const text = (ev.transcript || partialRef.current).trim();
        partialRef.current = "";
        setAiSpeaking(false);
        if (text) push({ role: "interviewer", content: text });
        break;
      }
      case "conversation.item.input_audio_transcription.completed": {
        const text = (ev.transcript || "").trim();
        if (text) push({ role: "candidate", content: text });
        break;
      }
      case "error":
        setError(ev.error?.message || "Realtime error");
        break;
    }
  };

  const start = useCallback(async (sessionId: string) => {
    setStatus("connecting");
    setError(null);
    try {
      const { token, deadline_ts } = await getRealtimeToken(sessionId);
      if (deadline_ts) setDeadline(deadline_ts);

      const pc = new RTCPeerConnection();
      pcRef.current = pc;

      // Native playback of the AI voice.
      const audio = document.createElement("audio");
      audio.autoplay = true;
      audioRef.current = audio;
      pc.ontrack = (e) => {
        audio.srcObject = e.streams[0];
      };

      // Microphone.
      const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = ms;
      ms.getTracks().forEach((t) => pc.addTrack(t, ms));

      // Event channel.
      const dc = pc.createDataChannel("oai-events");
      dcRef.current = dc;
      dc.onmessage = (e) => {
        try {
          handleEvent(JSON.parse(e.data));
        } catch {
          /* ignore malformed */
        }
      };
      dc.onopen = () => {
        // Have the interviewer greet first.
        dc.send(JSON.stringify({ type: "response.create" }));
        setStatus("live");
      };

      // SDP offer/answer exchange with OpenAI.
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      const resp = await fetch("https://api.openai.com/v1/realtime/calls", {
        method: "POST",
        body: offer.sdp,
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/sdp" },
      });
      if (!resp.ok) throw new Error(`OpenAI connection failed (${resp.status})`);
      await pc.setRemoteDescription({ type: "answer", sdp: await resp.text() });
    } catch (e: any) {
      setError(e.message || "Could not start the voice interview.");
      setStatus("error");
    }
  }, []);

  const stop = useCallback((): RtMessage[] => {
    try {
      dcRef.current?.close();
    } catch {
      /* ignore */
    }
    try {
      pcRef.current?.close();
    } catch {
      /* ignore */
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    if (audioRef.current) audioRef.current.srcObject = null;
    setStatus((s) => (s === "error" ? s : "ended"));
    return messagesRef.current;
  }, []);

  return { messages, status, error, deadline, aiSpeaking, start, stop };
}
