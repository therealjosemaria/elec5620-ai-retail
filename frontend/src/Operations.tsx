import { useState } from "react";
import { RestockingDemo } from "./Member2";
import type { Product } from "./Catalogue";
import { StockLookup } from "./StockLookup";
import { OperatorAnalysis } from "./OperatorAnalysis";
import { InventoryDecisions, DemandTrends } from "./RemainingTools";

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
    <div className="workspace-notice">Stock, availability, low-stock alerts and reorder suggestions use the shared inventory service. Operator authorisation is required.</div>
    <div className="workspace-tabs" role="tablist" aria-label="Inventory tools">{inventoryFeatures.map((f, i) =>
      <button key={f.id} role="tab" id={`inv-tab-${i}`} aria-controls="inventory-panel" aria-selected={tab === i} onClick={() => setTab(i)}>{f.title}<small>{f.member}</small></button>)}</div>
    <section id="inventory-panel" role="tabpanel" aria-labelledby={`inv-tab-${tab}`}>
      <div className="tool-heading"><p className="eyebrow">{feature.id}</p><span className="badge pending">Operator access</span></div>
      {tab === 0 || tab === 2 ? <StockLookup key={tab} products={products} error={error} availability={tab === 2}/> :
        <InventoryDecisions key={tab} kind={tab===1?"alerts":"reorder"} products={products}/>}
    </section>
  </div>;
}
export function InsightsWorkspace({ mode, products }: { mode: string | null; products: Product[] }) {
  const [tab, setTab] = useState(0);
  const tabs = ["Restocking priorities", "Profit margins", "Demand trends"];
  return <div className="operations-workspace">
    <header className="page-heading"><p className="eyebrow">03 / BUSINESS INSIGHTS AGENT</p>
      <h1>Good evidence.<br/><em>Better decisions.</em></h1><p>Understand what needs attention, what earns its place, and how demand is changing.</p></header>
    <div className="workspace-notice">Operator workspace preview · navigation does not grant access to business data.</div>
    <div className="workspace-tabs" role="tablist" aria-label="Business tools">{tabs.map((t, i) =>
      <button key={t} role="tab" id={`insight-tab-${i}`} aria-controls="insights-panel" aria-selected={tab === i} onClick={() => setTab(i)}>{t}<small>M{i + 2 === 4 ? 5 : i + 2}</small></button>)}</div>
    <section id="insights-panel" role="tabpanel" aria-labelledby={`insight-tab-${tab}`}>
      {tab === 0 && <><OperatorAnalysis key="restocking" kind="restocking" products={products}/>{mode === "fixture" && <RestockingDemo/>}</>}
      {tab === 1 && <OperatorAnalysis key="profit" kind="profit" products={products}/>}
      {tab === 2 && <DemandTrends products={products}/>}
    </section>
  </div>;
}
