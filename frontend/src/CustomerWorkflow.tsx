import { useEffect, useRef, useState } from "react";
import { AgentTrace, type AgentEvent } from "./AgentTrace";
import { readApi, type Availability } from "./api";
import type { Product } from "./Catalogue";

type Report = {
  workflow_id: string; created_at: string; outcome: string; trace: AgentEvent[]; limitations: string[];
  recommendations: {cache_hit: boolean; mode: string; model_provider: string; model_name: string | null; recommendations: {product: Product; explanation: string; matched_needs: string[]}[]} | null;
  budget: {budget: string; products: Product[]} | null; availability: Availability[];
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
    {result && <div aria-live="polite">
      <section aria-label="Customer assistance summary">
        <h3>{products.length > 0
          ? result.outcome === "complete" ? `We found ${products.length} matching ${products.length === 1 ? "product" : "products"}` : "Product matches found — some checks remain unresolved"
          : result.outcome === "no_match" ? "No product matched the supported requirements" : "We could not complete your request"}</h3>
        {products.length > 0 && <p>These products match the preferences shown below. Review each product’s price, stock status and any explicitly stated party-size assumption.</p>}
        {result.budget && products.length > 0 && <p>Each listed product is within AUD {result.budget.budget} per package. This is not a combined order total.</p>}
        <p role="status">Workflow result: {result.outcome.replaceAll("_", " ")}</p>
      </section>
      {products.map(product => {
        const availability = result.availability.find(row => row.product_id === product.product_id);
        const recommendation = result.recommendations?.recommendations.find(row => row.product.product_id === product.product_id);
        const explanation = recommendation?.explanation ?? "";
        const coverageStart = explanation.indexOf("Assuming one ");
        const coverage = coverageStart >= 0 ? explanation.slice(coverageStart).split(";")[0] : null;
        return <article className="product-card" key={product.product_id}><h3>{product.name}</h3>
          <p><strong>Preference match:</strong> {recommendation?.matched_needs.join(", ") || "See recommendation evidence below."}</p>
          <p>AUD {product.price} · Availability: {availability?.status ?? "Not checked"}</p>
          <p><strong>Price check:</strong> {result.budget?.products.some(row => row.product_id === product.product_id)
            ? `Within your AUD ${result.budget.budget} per-package budget.` : "Budget has not been confirmed for this product."}</p>
          {coverage && <p><strong>Party coverage:</strong> {coverage}.</p>}
          {!coverage && explanation.includes("Prototype serving estimate:") && <p><strong>Party coverage:</strong> Not established; package or serving information is missing.</p>}
          {availability && <p>{availability.reason} · Source updated: {availability.last_updated ?? "Unknown"}</p>}
          {explanation && <details><summary>Recommendation evidence and serving assumptions</summary><p>{explanation}</p></details>}
        </article>;
      })}
      <h3>Workflow details and limitations</h3>
      <small>Run time: {result.created_at}</small>
      {result.recommendations && <p>Recommendation data: {result.recommendations.mode} · {result.recommendations.cache_hit ? "reused from SQLite" : "generated and saved"}</p>}
      {result.recommendations && <p>Provider: {result.recommendations.model_provider}{result.recommendations.model_name ? ` · ${result.recommendations.model_name}` : ""}</p>}
      <ul>{result.limitations.map(line => <li key={line}>{line}</li>)}</ul>
      <AgentTrace trace={result.trace} workflowId={result.workflow_id}/>
    </div>}
  </section>;
}
