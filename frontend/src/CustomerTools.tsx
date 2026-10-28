import { useState } from "react";
import { readApi, type Availability } from "./api";
import type { Product } from "./Catalogue";

type Budget = {budget: string; status: string; products: Product[]; excluded_product_ids: string[]};

export function CustomerTools({requestId}: {requestId: string | null}) {
  const [budget, setBudget] = useState<Budget | null>(null);
  const [availability, setAvailability] = useState<Availability[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(kind: "budget-filter" | "availability") {
    if (!requestId || busy) return;
    setBusy(true); setError(""); setAvailability(null);
    if (kind === "budget-filter") setBudget(null);
    try {
      if (kind === "budget-filter") setBudget(await readApi<Budget>(`/api/requests/${requestId}/budget-filter`));
      else setAvailability(await readApi<Availability[]>(`/api/requests/${requestId}/availability?within_budget=${budget !== null}`));
    } catch (e) {setError(e instanceof Error ? e.message : "Request failed.");}
    finally {setBusy(false);}
  }
  return <section className="result" aria-label="Budget and availability">
    <p className="eyebrow">Member 4 · UC-M4-01 / UC-M4-02</p>
    <h2>Budget filtering</h2>
    <p>Filter the catalogue recommendations using your saved budget. Catalogue prices and unqualified dollars use AUD.</p>
    {!requestId && <p>Capture a request first to enable these checks.</p>}
    <button type="button" disabled={!requestId || busy} onClick={() => run("budget-filter")}>Apply budget filter</button>
    {budget && <div aria-live="polite"><p role="status">Budget result: {budget.status} · AUD {budget.budget}</p>
      {budget.products.map(p => <article className="product-card" key={p.product_id}><h3>{p.name}</h3><p>AUD {p.price} · {p.product_id}</p></article>)}
      {!budget.products.length && <p>No candidate products are within budget.</p>}
      <p>Excluded above budget: {budget.excluded_product_ids.join(", ") || "None"}</p></div>}
    <h2>Product availability</h2>
    <p>Check inventory for {budget ? "budget-filtered products" : "the catalogue recommendations"}. Unknown or stale stock is never presented as available.</p>
    <button type="button" disabled={!requestId || (budget !== null && !budget.products.length) || busy} onClick={() => run("availability")}>
      {budget ? "Check filtered availability" : "Check recommended availability"}</button>
    {error && <p role="alert" className="error">{error}</p>}
    {availability && <div aria-live="polite">{!availability.length && <p>No candidate products to check.</p>}{availability.map(row => <article className="product-card" key={row.product_id}>
      <h3>{row.product_id}: {row.status}</h3><p>Quantity: {row.stock_quantity ?? "Unknown"} · Updated: {row.last_updated ?? "Unknown"}</p><p>{row.reason}</p>
    </article>)}</div>}
  </section>;
}
