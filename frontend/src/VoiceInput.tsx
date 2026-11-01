import { useEffect, useRef, useState } from "react";

type RecognitionResult = {isFinal: boolean; [index: number]: {transcript: string}};
type Recognition = {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: {results: ArrayLike<RecognitionResult>}) => void) | null;
  onerror: ((event: {error: string}) => void) | null;
  onend: (() => void) | null;
  start: () => void; stop: () => void; abort: () => void;
};
type SpeechWindow = Window & {
  SpeechRecognition?: new () => Recognition;
  webkitSpeechRecognition?: new () => Recognition;
};

export function VoiceInput({value, onChange, onListeningChange, disabled}: {
  value: string; onChange: (text: string) => void;
  onListeningChange: (listening: boolean) => void; disabled: boolean;
}) {
  const [listening, setListening] = useState(false);
  const [message, setMessage] = useState("");
  const active = useRef<Recognition | null>(null);
  const speech = window as SpeechWindow;
  const Constructor = speech.SpeechRecognition ?? speech.webkitSpeechRecognition;
  const supported = Boolean(Constructor) && window.isSecureContext;

  useEffect(() => {
    const leave = () => {
      if (!document.hidden && window.location.hash === "#assistant") return;
      const recognition = active.current;
      if (!recognition) return;
      active.current = null;
      recognition.abort();
      setListening(false);
      onListeningChange(false);
      setMessage("Dictation stopped when you left the assistant. Review any text already added.");
    };
    window.addEventListener("hashchange", leave);
    document.addEventListener("visibilitychange", leave);
    return () => {
      window.removeEventListener("hashchange", leave);
      document.removeEventListener("visibilitychange", leave);
      const recognition = active.current;
      active.current = null;
      recognition?.abort();
    };
  }, [onListeningChange]);

  function toggle() {
    if (active.current) {
      setMessage("Finishing dictation…");
      active.current.stop();
      return;
    }
    if (!Constructor || !supported || disabled || value.length >= 1500) return;
    const recognition = new Constructor();
    active.current = recognition;
    const prefix = value.trimEnd();
    let receivedText = false;
    let failed = false;
    let limited = false;
    recognition.lang = "en-AU";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.onresult = event => {
      if (active.current !== recognition) return;
      const final: string[] = [];
      const interim: string[] = [];
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        (result.isFinal ? final : interim).push(result[0].transcript);
      }
      if (final.length) {
        receivedText = true;
        const text = [prefix, final.join(" ").trim()].filter(Boolean).join(" ");
        limited = text.length > 1500;
        onChange(text.slice(0, 1500));
      }
      setMessage(interim.length ? `Listening: ${interim.join(" ")}` : "Listening…");
    };
    recognition.onerror = event => {
      if (active.current !== recognition) return;
      failed = true;
      const errors: Record<string, string> = {
        "not-allowed": "Microphone permission was denied. Allow it in your browser settings, or type your request.",
        "service-not-allowed": "Your browser’s speech service is unavailable. Type your request instead.",
        "audio-capture": "No microphone is available. Check your microphone, or type your request.",
        "network": "The browser speech service could not connect. Check your connection, or type your request.",
        "no-speech": "No speech was detected. Try again, or type your request.",
        "aborted": "Dictation stopped. Review any text already added.",
      };
      setMessage(errors[event.error] ?? "Dictation could not finish. Review your text or type your request.");
      // Release the controls even if this browser omits the end event on error.
      active.current = null;
      setListening(false);
      onListeningChange(false);
      recognition.abort();
    };
    recognition.onend = () => {
      if (active.current !== recognition) return;
      active.current = null;
      setListening(false);
      onListeningChange(false);
      if (!failed) setMessage(limited
        ? "The 1,500-character limit was reached; extra dictation was omitted. Review your text."
        : receivedText ? "Dictation added. Review or edit your text before Capture and save."
        : "No speech was captured. Try again, or type your request.");
    };
    setListening(true);
    onListeningChange(true);
    setMessage("Listening… Allow microphone access if prompted.");
    try { recognition.start(); }
    catch {
      active.current = null;
      setListening(false);
      onListeningChange(false);
      setMessage("Could not start dictation. Check microphone permissions, or type your request.");
    }
  }

  return <div className="voice-input">
    <button type="button" className="secondary" onClick={toggle}
      aria-pressed={listening} aria-controls="needs" aria-describedby="voice-help"
      disabled={disabled || !supported || (!listening && value.length >= 1500)}>
      {listening ? "Stop listening" : "Speak request"}
    </button>
    <small id="voice-help">{!supported
      ? "Dictation is unavailable in this browser. You can still type your request."
      : "Australian English dictation. Your browser’s speech service may process audio online. Text is not submitted until you choose Capture and save."}</small>
    {message && <p role="status" className="voice-status">{message}</p>}
  </div>;
}
