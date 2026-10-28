import { useState } from "react";
import { RestockingDemo } from "./Member2";
import type { Product } from "./Catalogue";

const inventoryFeatures = [
  {title: "Stock lookup", member: "M1", id: "UC-M1-02", description: "Current stock quantities and source update times for selected products.", dependency: "The inventory query service is not connected."},
  {title: "Low-stock alerts", member: "M3", id: "UC-M3-01", description: "Products at or below their configured stock threshold, with supporting evidence.", dependency: "Current stock and threshold data are required before alerts can be generated."},
  {title: "Availability", member: "M4", id: "UC-M4-02", description: "Available, unavailable or unknown status based on verified current inventory.", dependency: "Product availability cannot be confirmed until the inventory service is connected."},
  {title: "Reorder suggestions", member: "M5", id: "UC-M5-01", description: "Suggested replenishment quantities with the inventory evidence and rule used.", dependency: "Current stock, thresholds and the team's reorder rule are required."},
];

export function PendingFeature({ title, description, detail }: { title: string; description: string; detail: string }) {
  return <div className="pending-feature"><span className="outline-mark" aria-hidden="true">↗</span>
    <span className="badge pending">Awaiting integration</span><h3>{title}</h3><p>{description}</p>
    <p className="muted">{detail}</p><span className="empty-note">No result has been generated.</span></div>;
}

export function InventoryWorkspace({ products, error }: { products: Product[]; error: string }) {
  const [tab, setTab] = useState(0);
  const feature = inventoryFeatures[tab];
  return <div className="operations-workspace">
    <header className="page-heading"><p className="eyebrow">02 / INVENTORY & PROCUREMENT AGENT</p>
      <h1>A clearer view.<br/><em>Of every bottle.</em></h1><p>Review stock, spot shortages and plan replenishment from verified inventory evidence.</p></header>
    <div className="workspace-notice"><span className="status-dot pending-dot"/>Inventory service awaiting integration. Catalogue entries below do not imply current stock.</div>
    <div className="workspace-tabs" role="tablist" aria-label="Inventory tools">{inventoryFeatures.map((f, i) =>
      <button key={f.id} role="tab" id={`inv-tab-${i}`} aria-controls="inventory-panel" aria-selected={tab === i} onClick={() => setTab(i)}>{f.title}<small>{f.member}</small></button>)}</div>
    <section id="inventory-panel" role="tabpanel" aria-labelledby={`inv-tab-${tab}`}>
      <div className="tool-heading"><p className="eyebrow">{feature.id}</p><span className="badge pending">Not connected</span></div>
      <PendingFeature title={feature.title} description={feature.description} detail={feature.dependency}/>
      {tab === 0 && <div className="inventory-list"><h3>Catalogue reference</h3>
        {error ? <p role="alert" className="error">{error}</p> : <div className="table-scroll"><table>
          <thead><tr><th>Product</th><th>Category</th><th>Stock</th><th>Updated</th></tr></thead>
          <tbody>{products.map(p => <tr key={p.product_id}><td><strong>{p.name}</strong><small>{p.product_id}</small></td><td>{p.category}</td><td>Unknown</td><td>Not connected</td></tr>)}</tbody>
        </table></div>}</div>}
    </section>
  </div>;
}

export function InsightsWorkspace({ mode }: { mode: string | null }) {
  const [tab, setTab] = useState(0);
  const tabs = ["Restocking priorities", "Profit margins", "Demand trends"];
  return <div className="operations-workspace">
    <header className="page-heading"><p className="eyebrow">03 / BUSINESS INSIGHTS AGENT</p>
      <h1>Good evidence.<br/><em>Better decisions.</em></h1><p>Understand what needs attention, what earns its place, and how demand is changing.</p></header>
    <div className="workspace-notice">Operator workspace preview · navigation does not grant access to business data.</div>
    <div className="workspace-tabs" role="tablist" aria-label="Business tools">{tabs.map((t, i) =>
      <button key={t} role="tab" id={`insight-tab-${i}`} aria-controls="insights-panel" aria-selected={tab === i} onClick={() => setTab(i)}>{t}<small>M{i + 2 === 4 ? 5 : i + 2}</small></button>)}</div>
    <section id="insights-panel" role="tabpanel" aria-labelledby={`insight-tab-${tab}`}>
      {tab === 0 && (mode === "fixture" ? <RestockingDemo/> : <PendingFeature title="Restocking priorities" description="Decide which products need replenishment attention first." detail="The sample demonstration runs in fixture mode. Connected analysis requires operator authentication and authorised inventory and sales services."/>)}
      {tab === 1 && <><p className="eyebrow tool-heading">UC-M3-02 / MEMBER 3</p><PendingFeature title="Profit margin analysis" description="Review revenue, cost, profit and margin for a product, category or completed period." detail="The calculation module exists. Its authenticated API and page integration are still pending."/></>}
      {tab === 2 && <><p className="eyebrow tool-heading">UC-M5-02 / MEMBER 5</p><PendingFeature title="Demand trends" description="Compare completed sales periods to understand increasing, decreasing or stable demand." detail="The analysis service and comparison rule have not been connected. No sales trend is inferred."/></>}
    </section>
  </div>;
}

export function CustomerPendingTools() {
  return <section className="next-steps" aria-label="Customer workflow integrations"><p className="eyebrow">NEXT IN THE CUSTOMER JOURNEY</p>
    <div className="next-step-grid"><div><span className="badge pending">Awaiting integration</span><h3>Budget filtering</h3><p>Keep recommended products within your stated budget.</p><small>M4 · UC-M4-01</small></div>
    <div><span className="badge pending">Awaiting integration</span><h3>Product availability</h3><p>Confirm availability through the Inventory & Procurement Agent.</p><small>M4 · UC-M4-02</small></div></div>
  </section>;
}
