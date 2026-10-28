import { useState } from "react";

type Recommendation = {
  outcome: string; limitations: string[];
  recommendations: { rank: number; explanation: string; product: {
    product_id: string; name: string; category: string; price: string; abv: string;
    sweetness: string; flavour_tags: string[];
  } }[];
};
type Restocking = {
  outcome: string; generated_at: string; data_mode: string; ranking_basis: string;
  sales_start_date: string | null; sales_end_date: string | null; limitations: string[];
  priorities: { product_id: string; product_name: string; rank: number; stock_quantity: number;
    reorder_threshold: number; sold_quantity: number; last_updated: string; explanation: string }[];
};
async function read<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Unable to complete the request.");
  return data;
}

// Parent keys this component by saved request ID, preventing results from a previous request.
export function DrinkRecommendations({ requestId }: { requestId: string }) {
  const [result, setResult] = useState<Recommendation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run() {
    setBusy(true); setError(""); setResult(null);
    try { setResult(await read<Recommendation>(`/api/requests/${requestId}/recommendations`)); }
    catch (e) { setError(e instanceof Error ? e.message : "Recommendation failed."); }
    finally { setBusy(false); }
  }
  return <section className="result" aria-label="Drink recommendations">
    <p className="eyebrow">Member 2 · UC-M2-01</p>
    <h2>Drink recommendations</h2>
    <p>Match your saved preferences against the product catalogue. This prototype uses rules and makes no AI calls.</p>
    <p><small>Supported examples: red wine, white wine, beer, dry, sweet wine, citrus, fruity, no sweet drinks.</small></p>
    <button type="button" onClick={run} disabled={busy}>{busy ? "Matching…" : "Recommend drinks"}</button>
    {error && <p role="alert" className="error">{error}</p>}
    {result && <div aria-live="polite">
      <p role="status">Recommendation result: {result.outcome.replaceAll("_", " ")}</p>
      <ul>{result.limitations.map(line => <li key={line}>{line}</li>)}</ul>
      {result.recommendations.map(item => <article className="product-card" key={item.product.product_id}>
        <h3>Rank {item.rank} · {item.product.name}</h3>
        <p>{item.product.category} · ABV {item.product.abv}% · {item.product.sweetness}</p>
        <p>Catalogue price: {item.product.price} · {item.product.flavour_tags.join(", ") || "No flavour tags"}</p>
        <p>{item.explanation}</p><small>Product ID: {item.product.product_id}</small>
      </article>)}
    </div>}
  </section>;
}

export function RestockingDemo() {
  const [scope, setScope] = useState("");
  const [result, setResult] = useState<Restocking | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setResult(null);
    try {
      setResult(await read<Restocking>("/api/demo/restocking-priorities", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify(scope ? {category: scope} : {}),
      }));
    } catch (e) { setError(e instanceof Error ? e.message : "Analysis failed."); }
    finally { setBusy(false); }
  }
  return <section className="result" aria-label="Restocking demonstration">
    <p className="eyebrow">Member 2 · UC-M2-02</p>
    <h2>Restocking priorities · sample demonstration</h2>
    <p>Fixed sample stock and sales, dated 27 October 2026. This demonstrates prioritisation; it is not connected to current store inventory.</p>
    <form onSubmit={run} className="inline-form">
      <label htmlFor="restocking-category">Sample category</label>
      <select id="restocking-category" value={scope} disabled={busy}
        onChange={event => {setScope(event.target.value); setResult(null); setError("");}}>
        <option value="">All sample products</option><option value="Wine">Wine</option><option value="Beer">Beer</option>
      </select>
      <button disabled={busy}>{busy ? "Analysing…" : "Review sample priorities"}</button>
    </form>
    {error && <p role="alert" className="error">{error}</p>}
    {result && <div aria-live="polite">
      <p role="status">Restocking result: {result.outcome.replaceAll("_", " ")}</p>
      <p>{result.ranking_basis}</p>
      <ul>{result.limitations.map(line => <li key={line}>{line}</li>)}</ul>
      {result.priorities.map(item => <article className="product-card" key={item.product_id}>
        <h3>Priority {item.rank} · {item.product_name}</h3>
        <p>{item.explanation}</p>
        <small>Stock updated: {item.last_updated} · Product: {item.product_id}</small>
      </article>)}
      <small>Sales period: {result.sales_start_date ?? "Unavailable"} – {result.sales_end_date ?? "Unavailable"}<br />
        Generated at: {result.generated_at} · Data: {result.data_mode}</small>
    </div>}
  </section>;
}
