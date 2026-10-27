import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import { DrinkRecommendations, RestockingDemo } from "./Member2";

type Status = {
  mode: "fixture" | "live"; live_attempts_today: number; local_daily_limit: number;
  live_configured: boolean; sample: string;
};
type Saved = {
  request_id: string; text: string; needs: Record<string, string | number | string[] | null>;
  missing_fields: string[]; created_at: string; mode: string;
  outcome: string; message: string;
};
async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Invalid request. Check your input.");
  return data;
}
function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [text, setText] = useState("");
  const [saved, setSaved] = useState<Saved | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState<{text: string; id: string} | null>(null);
  const refreshStatus = () => api<Status>("/api/status").then(setStatus);
  useEffect(() => {
    refreshStatus().catch(() => setError("Backend unavailable. Start FastAPI and reload."));
    try {
      const previous = JSON.parse(sessionStorage.getItem("captureAttempt") || "null");
      if (previous && typeof previous.text === "string" && typeof previous.id === "string") {
        setAttempt(previous);
        setText(previous.text);
      }
    } catch { sessionStorage.removeItem("captureAttempt"); }
    const id = localStorage.getItem("lastRequestId");
    if (id) api<Saved>(`/api/requests/${id}`).then(setSaved).catch(() => localStorage.removeItem("lastRequestId"));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(""); setSaved(null);
    const current = attempt?.text === text ? attempt : {text, id: crypto.randomUUID()};
    setAttempt(current);
    try {
      sessionStorage.setItem("captureAttempt", JSON.stringify(current));
      const result = await api<Saved>("/api/requests", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({request_id: current.id, text}),
      });
      // Separate GET verifies the displayed data really comes back from SQLite.
      const persisted = await api<Saved>(`/api/requests/${result.request_id}`);
      localStorage.setItem("lastRequestId", result.request_id);
      setSaved(persisted);
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setBusy(false); refreshStatus().catch(() => {}); }
  }
  return <main>
    <header><p className="eyebrow">ELEC5620 · STAGE 2 / FIRST SLICE</p>
      <h1>Capture a customer request</h1>
      <p>UC-M1-01 · Record stated needs. No recommendations, filtering or stock checks.</p>
    </header>
    <section className="notice" aria-label="Model status">
      <strong>{status?.mode === "live" ? "Live · campus-qwen" : "Fixture mode · no AI calls"}</strong>
      <p>{status ? `${status.live_attempts_today} / ${status.local_daily_limit} local live attempts today (UTC). University quota is separate.` : "Connecting to backend…"}</p>
      {status?.mode === "fixture" && <p>Only the fixed sample works in this mode. This validates the pipeline, not AI quality.</p>}
      {status?.mode === "live" && !status.live_configured && <p>Backend API key is missing. Configure it privately before using live mode.</p>}
    </section>
    <form onSubmit={submit}>
      <label htmlFor="needs">What are you looking for?</label>
      <textarea id="needs" maxLength={1500} rows={4} value={text}
        onChange={e => setText(e.target.value)} disabled={busy} required
        placeholder="Describe your budget, occasion, preferences or constraints…" />
      <div className="actions">
        <button type="button" className="secondary" disabled={!status || busy}
          onClick={() => setText(status!.sample)}>Use sample</button>
        <button disabled={busy || !text.trim() || !status || (status.mode === "live" && !status.live_configured)}>
          {busy ? "Capturing…" : "Capture and save"}
        </button>
      </div>
      <small>Up to 1,500 characters. One live call per new attempt; no automatic retries.</small>
    </form>
    {error && <p role="alert" className="error">{error}</p>}
    {saved && <section aria-live="polite" className="result">
      <h2>Saved in SQLite</h2><p>Mode: {saved.mode} · Read back from the database</p>
      <p role={saved.outcome === "downstream_unavailable" ? "alert" : "status"}>{saved.message}</p>
      <dl>{Object.entries(saved.needs).map(([key, value]) => <div key={key}>
        <dt>{key.replaceAll("_", " ")}</dt><dd>{Array.isArray(value) ? (value.join(", ") || "Unknown / not stated") : (value ?? "Unknown / not stated")}</dd>
      </div>)}</dl>
      <p>Missing or unresolved: {saved.missing_fields.join(", ") || "None"}</p>
      <small>Request ID: {saved.request_id}<br />Saved: {saved.created_at}</small>
      <details><summary>Inspect stored record</summary><pre>{JSON.stringify(saved, null, 2)}</pre></details>
    </section>}
    {saved && <DrinkRecommendations key={saved.request_id} requestId={saved.request_id} />}
    {status?.mode === "fixture" && <RestockingDemo />}
  </main>;
}
createRoot(document.getElementById("root")!).render(<App />);
