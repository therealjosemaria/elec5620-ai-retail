import { useEffect, useRef, useState } from "react";
import { AgentTrace, type AgentEvent } from "./AgentTrace";
import { readApi, type Availability } from "./api";
import type { Product } from "./Catalogue";

type Report = {
  workflow_id: string; created_at: string; outcome: string; trace: AgentEvent[]; limitations: string[];
  recommendations: {cache_hit: boolean; mode: string; model_provider: string; model_name: string | null; recommendations: {product: Product; explanation: string}[]} | null;
  budget: {products: Product[]} | null; availability: Availability[];
};

export function CustomerWorkflow({requestId, onComplete}: {requestId: string; onComplete: () => void}) {
  const [result, setResult] = useState<Report | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const actionVersion = useRef(0);
  useEffect(() => {
    let active = true;
    const version = ++actionVersion.current;
    readApi<Report>(`/api/requests/${requestId}/workflow`).then(report => {if (active && version === actionVersion.current) setResult(report);}).catch(() => {});
    return () => {active = false;};
  }, [requestId]);
  async function run() {
    if (busy) return;
    actionVersion.current++;
    setBusy(true); setError(""); setResult(null);
    try {
      setResult(await readApi<Report>(`/api/requests/${requestId}/workflow`, {method: "POST"}));
      onComplete();
    } catch (e) {setError(e instanceof Error ? e.message : "Assistance workflow failed.");}
    finally {setBusy(false);}
  }
  const products = result?.budget?.products ?? result?.recommendations?.recommendations.map(row => row.product) ?? [];
  return <section className="result" aria-label="Customer agent workflow">
    <h2>Customer assistance workflow</h2>
    <p>Run the separate recommendation, budget and inventory steps together. Recommendations are generated once for this saved request, then reused.</p>
    <button type="button" onClick={run} disabled={busy}>{busy ? "Running agents…" : "Run agent workflow"}</button>
    {error && <p role="alert" className="error">{error}</p>}
    {result && <div aria-live="polite"><p role="status">Workflow result: {result.outcome.replaceAll("_", " ")}</p>
      <small>Run time: {result.created_at}</small>
      {result.recommendations && <p>Recommendation data: {result.recommendations.mode} · {result.recommendations.cache_hit ? "reused from SQLite" : "generated and saved"}</p>}
      {result.recommendations && <p>Provider: {result.recommendations.model_provider}{result.recommendations.model_name ? ` · ${result.recommendations.model_name}` : ""}</p>}
      <ul>{result.limitations.map(line => <li key={line}>{line}</li>)}</ul>
      {products.map(product => {
        const availability = result.availability.find(row => row.product_id === product.product_id);
        return <article className="product-card" key={product.product_id}><h3>{product.name}</h3>
          <p>AUD {product.price} · Availability: {availability?.status ?? "Not checked"}</p>
          <p>{result.recommendations?.recommendations.find(row => row.product.product_id === product.product_id)?.explanation}</p>
          {availability && <p>{availability.reason} · Source updated: {availability.last_updated ?? "Unknown"}</p>}
        </article>;
      })}
      <AgentTrace trace={result.trace} workflowId={result.workflow_id}/>
    </div>}
  </section>;
}
