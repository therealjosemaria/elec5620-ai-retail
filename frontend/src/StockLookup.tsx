import { useState } from "react";
import type { Product } from "./Catalogue";
import type { Availability } from "./api";

type StockResult = {
  product_id: string; status: "found" | "not_found" | "stale" | "error";
  item: {stock_quantity: number; reorder_threshold: number; last_updated: string} | null;
  reason: string | null;
};

export function StockLookup({ products, error, availability = false }: {products: Product[]; error: string; availability?: boolean}) {
  const [token, setToken] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [results, setResults] = useState<(StockResult | Availability)[] | null>(null);
  const [failure, setFailure] = useState("");
  const [busy, setBusy] = useState(false);

  async function lookup(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (!selected.length) { setFailure("Select at least one product."); return; }
    setBusy(true); setFailure(""); setResults(null);
    try {
      const response = await fetch(availability ? "/api/inventory/availability" : "/api/inventory/lookup", {
        method: "POST", headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`},
        body: JSON.stringify({product_ids: selected}),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Stock lookup failed.");
      setResults(data);
    } catch (e) { setFailure(e instanceof Error ? e.message : "Inventory source unavailable."); }
    finally { setBusy(false); }
  }

  return <section aria-labelledby="stock-title" className="inventory-list">
    <h3 id="stock-title">{availability ? "Check product availability" : "Check current stock"}</h3>
    <p>Prototype inventory snapshot. Quantities are sample data; source timestamps are preserved and stale records stay labelled.</p>
    <form onSubmit={lookup} className="stock-form">
      <label htmlFor="operator-token">Operator token</label>
      <input id="operator-token" type="password" autoComplete="off" value={token} disabled={busy}
        onChange={e => {setToken(e.target.value); setResults(null);}} required/>
      <p className="muted">Use the private operator token configured on the server. It is kept only in this page's memory.</p>
      {error ? <p role="alert" className="error">{error}</p> : <fieldset disabled={busy}>
        <legend>Select products</legend>
        {products.map(p => <label key={p.product_id} className="stock-choice">
          <input type="checkbox" checked={selected.includes(p.product_id)}
            onChange={e => {
              setSelected(current => e.target.checked ? [...current, p.product_id] : current.filter(id => id !== p.product_id));
              setResults(null);
            }}/><span>{p.name} <small>{p.product_id}</small></span>
        </label>)}
      </fieldset>}
      <button type="submit" disabled={busy || !products.length}>{busy ? "Checking…" : availability ? "Check selected availability" : "Check selected stock"}</button>
    </form>
    {failure && <p role="alert" className="error">{failure}</p>}
    {results && <div aria-live="polite"><h3>{availability ? "Availability results" : "Stock lookup results"}</h3>
      <div className="table-scroll stock-results" tabIndex={0} aria-label="Stock results table; scroll horizontally for all columns"><table>
        <thead><tr><th>Product</th><th>Status</th><th>Quantity</th>{!availability && <th>Threshold</th>}<th>Source updated</th><th>Detail</th></tr></thead>
        <tbody>{results.map(row => <tr key={row.product_id}>
          <td>{row.product_id}</td><td>{row.status}</td><td>{("item" in row ? row.item?.stock_quantity : row.stock_quantity) ?? "Unknown"}</td>
          {!availability && <td>{"item" in row ? row.item?.reorder_threshold ?? "Unknown" : "Unknown"}</td>}
          <td>{("item" in row ? row.item?.last_updated : row.last_updated) ?? "Unknown"}</td>
          <td>{row.reason ?? "Current record returned."}</td>
        </tr>)}</tbody>
      </table></div>
    </div>}
  </section>;
}
