import { useCallback, useEffect, useRef, useState } from "react";

// Minimal typings for the (vendor-prefixed) Web Speech API.
type SpeechRecognitionResult = { transcript: string; isFinal: boolean };

// Preferred, natural-sounding voices in priority order (name substrings).
// "Natural" = Microsoft neural voices (Edge); then Google/Apple premium voices.
const VOICE_PREFERENCES = [
  "natural",
  "google us english",
  "samantha",
  "ava",
  "allison",
  "serena",
  "jenny",
  "aria",
];

function pickVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  if (!voices.length) return null;
  const en = voices.filter((v) => v.lang?.toLowerCase().startsWith("en"));
  const pool = en.length ? en : voices;
  for (const pref of VOICE_PREFERENCES) {
    const match = pool.find((v) => v.name.toLowerCase().includes(pref));
    if (match) return match;
  }
  // Fall back to a US English voice, else the first available.
  return pool.find((v) => v.lang?.toLowerCase() === "en-us") || pool[0];
}

export function useSpeech() {
  const supported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  const recognitionRef = useRef<any>(null);
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null);
  const [listening, setListening] = useState(false);

  // Voices load asynchronously; pick the best one now and on `voiceschanged`.
  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const refresh = () => {
      voiceRef.current = pickVoice(window.speechSynthesis.getVoices());
    };
    refresh();
    window.speechSynthesis.addEventListener?.("voiceschanged", refresh);
    return () => window.speechSynthesis.removeEventListener?.("voiceschanged", refresh);
  }, []);

  const stop = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch {
      /* ignore */
    }
    setListening(false);
  }, []);

  const listen = useCallback(
    (onFinal: (text: string) => void) => {
      if (!supported) return;
      const Ctor =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const rec = new Ctor();
      rec.lang = "en-US";
      rec.interimResults = false;
      rec.continuous = false;
      rec.onresult = (event: any) => {
        const results = Array.from(event.results) as any[];
        const text = results
          .map((r) => (r[0] as SpeechRecognitionResult).transcript)
          .join(" ")
          .trim();
        if (text) onFinal(text);
      };
      rec.onend = () => setListening(false);
      rec.onerror = () => setListening(false);
      recognitionRef.current = rec;
      rec.start();
      setListening(true);
    },
    [supported]
  );

  const speak = useCallback((text: string, onEnd?: () => void) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      onEnd?.();
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    if (voiceRef.current) utterance.voice = voiceRef.current;
    // Warm, natural delivery: a touch slower than default, slightly higher pitch.
    utterance.rate = 0.95;
    utterance.pitch = 1.05;
    utterance.onend = () => onEnd?.();
    utterance.onerror = () => onEnd?.();
    window.speechSynthesis.speak(utterance);
  }, []);

  const cancelSpeech = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }, []);

  useEffect(() => () => cancelSpeech(), [cancelSpeech]);

  return { supported, listening, listen, stop, speak, cancelSpeech };
}
