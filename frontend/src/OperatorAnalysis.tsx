import { useState } from "react";
import { readApi } from "./api";
import type { Product } from "./Catalogue";
import type { Restocking } from "./Member2";
import { AgentTrace, type AgentEvent } from "./AgentTrace";

type Profit = {
  outcome: string; revenue: string | null; total_cost: string | null;
  profit: string | null; profit_margin_percent: string | null; record_count: number;
  excluded_missing_cost: number; excluded_invalid: number; unassigned: number;
  limitations: string[]; calculation_basis: string;
};

export function OperatorAnalysis({kind, products}: {kind: "restocking" | "profit"; products: Product[]}) {
  const [token, setToken] = useState("");
  const [scope, setScope] = useState("product");
  const [product, setProduct] = useState("");
  const [category, setCategory] = useState("Wine");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [result, setResult] = useState<((Restocking | Profit) & {workflow_id: string; trace: AgentEvent[]}) | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const prefix = `analysis-${kind}`;
  function clear() {setResult(null); setError("");}
  async function run(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); clear();
    const body: Record<string, string> = {};
    if (scope === "product") body.product_id = product;
    if (scope === "category") body.category = category;
    if (kind === "profit") {
      if (start) body.start_date = start;
      if (end) body.end_date = end;
    }
    try {setResult(await readApi<(Restocking | Profit) & {workflow_id: string; trace: AgentEvent[]}>(kind === "profit" ? "/api/profit-margins" : "/api/restocking-priorities", {
      method: "POST", headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`},
      body: JSON.stringify(body),
    }));}
    catch (e) {setError(e instanceof Error ? e.message : "Analysis failed.");}
    finally {setBusy(false);}
  }
  return <section className="result" aria-label={kind === "profit" ? "Connected profit margins" : "Connected restocking priorities"}>
    <p className="eyebrow">{kind === "profit" ? "Member 3 · UC-M3-02" : "Member 2 · UC-M2-02"}</p>
    <h2>{kind === "profit" ? "Profit margins" : "Restocking priorities"}</h2>
    <p>Read-only analysis of the shared prototype database. Operator authorisation is required.</p>
    <form className="stock-form" onSubmit={run}>
      <label htmlFor={`${prefix}-token`}>Business access token</label>
      <input id={`${prefix}-token`} type="password" autoComplete="off" value={token} required disabled={busy}
        onChange={e => {setToken(e.target.value); clear();}}/>
      <label htmlFor={`${prefix}-scope`}>Analysis scope</label>
      <select id={`${prefix}-scope`} value={scope} disabled={busy} onChange={e => {setScope(e.target.value); clear();}}>
        <option value="product">Product</option><option value="category">Category</option>
        <option value="all">{kind === "profit" ? "Completed date range" : "All products"}</option>
      </select>
      {scope === "product" && <><label htmlFor={`${prefix}-product`}>Analysis product</label>
        <select id={`${prefix}-product`} value={product} required disabled={busy} onChange={e => {setProduct(e.target.value); clear();}}>
          <option value="">Choose a product</option>{products.map(p => <option key={p.product_id} value={p.product_id}>{p.name}</option>)}
        </select></>}
      {scope === "category" && <><label htmlFor={`${prefix}-category`}>Analysis category</label>
        <select id={`${prefix}-category`} value={category} disabled={busy} onChange={e => {setCategory(e.target.value); clear();}}>
          {[...new Set(products.map(p => p.category))].map(c => <option key={c}>{c}</option>)}
        </select></>}
      {kind === "profit" && <><label htmlFor={`${prefix}-start`}>Sales period start</label>
        <input id={`${prefix}-start`} type="date" value={start} disabled={busy} required={scope === "all"} onChange={e => {setStart(e.target.value); clear();}}/>
        <label htmlFor={`${prefix}-end`}>Sales period end</label>
        <input id={`${prefix}-end`} type="date" value={end} disabled={busy} required={scope === "all"} onChange={e => {setEnd(e.target.value); clear();}}/>
        <small>Optional for a product/category; provide both dates when restricting the period. End before today.</small></>}
      <button disabled={busy}>{busy ? "Analysing…" : kind === "profit" ? "Review profit margins" : "Review connected priorities"}</button>
    </form>
    {error && <p role="alert" className="error">{error}</p>}
    {result && <div aria-live="polite"><p role="status">Analysis result: {result.outcome.replaceAll("_", " ")}</p>
      <ul>{result.limitations.map(line => <li key={line}>{line}</li>)}</ul>
      {"revenue" in result ? <>
        <dl>{[["Revenue (AUD)", result.revenue], ["Cost (AUD)", result.total_cost], ["Profit (AUD)", result.profit],
              ["Margin (%)", result.profit_margin_percent], ["Analysed records", result.record_count],
              ["Missing-cost exclusions", result.excluded_missing_cost], ["Invalid exclusions", result.excluded_invalid],
              ["Unassigned records", result.unassigned]].map(([label,value]) => <div key={label}><dt>{label}</dt><dd>{value ?? "Unknown"}</dd></div>)}</dl>
        <p>{result.calculation_basis}</p>
      </> : <><p>{result.ranking_basis}</p>{result.priorities.map(p => <article className="product-card" key={p.product_id}>
        <h3>Priority {p.rank} · {p.product_name}</h3><p>{p.explanation}</p><p>Inventory updated: {p.last_updated}</p>
      </article>)}<small>Completed sales: {result.sales_start_date ?? "Unknown"} – {result.sales_end_date ?? "Unknown"} · {result.data_mode}</small></>}
      <AgentTrace trace={result.trace} workflowId={result.workflow_id}/>
    </div>}
  </section>;
}
