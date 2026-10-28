import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Bottle, Catalogue, type Product } from "./Catalogue";
import { CustomerWorkspace } from "./CustomerWorkspace";
import { InsightsWorkspace, InventoryWorkspace } from "./Operations";
import "./style.css";

type Page = "discover" | "assistant" | "inventory" | "insights";
const pages: {id: Page; label: string}[] = [
  {id: "discover", label: "Discover"}, {id: "assistant", label: "Customer assistant"},
  {id: "inventory", label: "Inventory & procurement"}, {id: "insights", label: "Business insights"},
];
const currentPage = (): Page => pages.find(p => `#${p.id}` === location.hash)?.id ?? "discover";

function App() {
  const [page, setPage] = useState<Page>(currentPage);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<string | null>(null);
  const [connection, setConnection] = useState("Connecting");
  useEffect(() => {
    const changed = () => { setPage(currentPage()); window.scrollTo({top: 0}); };
    window.addEventListener("hashchange", changed);
    fetch("/api/products").then(async response => {
      if (!response.ok) throw new Error();
      return response.json() as Promise<Product[]>;
    }).then(setProducts).catch(() => setError("Catalogue unavailable. Check that the updated backend is running.")).finally(() => setLoading(false));
    fetch("/api/status").then(async response => {
      if (!response.ok) throw new Error();
      return response.json();
    }).then(data => {setMode(data.mode); setConnection(data.mode === "fixture" ? "Fixture mode" : "Live extraction");})
      .catch(() => setConnection("Backend offline"));
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  function navigate(next: Page) { location.hash = next; }
  return <>
    <a className="skip-link" href="#page-content" onClick={e => { e.preventDefault(); document.getElementById("page-content")?.focus(); }}>Skip to content</a>
    <div className="announcement">A considered approach to spirits. <span>ELEC5620 · LOCAL PROJECT</span></div>
    <header className="site-header">
      <a className="wordmark" href="#discover" aria-label="The Still home">THE STILL<span>SPIRITS, WITH INSIGHT.</span></a>
      <nav aria-label="Main navigation">{pages.map(p => <a key={p.id} href={`#${p.id}`} aria-current={page === p.id ? "page" : undefined}>{p.label}</a>)}</nav>
      <span className={`connection ${mode ? "" : "offline"}`}><i/>{connection}</span>
    </header>
    <main id="page-content" className="site-main" tabIndex={-1}>
      {page === "discover" && <>
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy"><p className="eyebrow"><span/>THE SPIRIT OF GOOD CHOICE</p>
            <h1>Find your spirit.<br/><em>Know your choice.</em></h1>
            <p>From a bottle of vodka to something unexpected.<br className="desktop-break"/> Explore the collection, with a little considered guidance.</p>
            <div className="hero-actions"><button onClick={() => navigate("assistant")}>Find my drink <span aria-hidden="true">↗</span></button>
              <a className="text-link" href="#collection" onClick={e => {e.preventDefault(); document.getElementById("collection")?.scrollIntoView({behavior: "smooth"});}}>Explore the collection <span aria-hidden="true">↓</span></a></div>
            <div className="hero-footnote"><span className="line"/> CATALOGUE FACTS. EXPLAINED CHOICES.</div>
          </div>
          <div className="hero-visual"><div className="hero-circle"/><span className="vertical-label">THE COLLECTION / NO. 001</span>
            <Bottle hero/><div className="hero-caption"><span>IN FOCUS</span><strong>Vodka</strong><small>One spirit. A place to begin.</small></div><span className="illustration-note">Original illustration</span>
          </div>
        </section>
        <section className="agent-links" aria-label="Agent workspaces">
          <button onClick={() => navigate("assistant")}><span className="agent-number">01</span><span><strong>Customer Agent</strong><small>Discover what suits you</small></span><span className="agent-arrow">↗</span></button>
          <button onClick={() => navigate("inventory")}><span className="agent-number">02</span><span><strong>Inventory & Procurement</strong><small>A clear view of your stock</small></span><span className="agent-arrow">↗</span></button>
          <button onClick={() => navigate("insights")}><span className="agent-number">03</span><span><strong>Business Insights</strong><small>Evidence behind every decision</small></span><span className="agent-arrow">↗</span></button>
        </section>
        <Catalogue products={products} loading={loading} error={error}/>
        <section className="editorial-note"><p className="eyebrow">THOUGHTFUL BY DESIGN</p><h2>Three perspectives.<br/><em>One considered experience.</em></h2><p>Choose with the Customer Agent. Review stock with Inventory & Procurement. Explore the evidence with Business Insights.</p><a className="text-link" href="#insights">Explore the workspace ↗</a></section>
      </>}
      <div hidden={page !== "assistant"}><CustomerWorkspace/></div>
      <div hidden={page !== "inventory"}><InventoryWorkspace products={products} error={error}/></div>
      <div hidden={page !== "insights"}><InsightsWorkspace mode={mode} products={products}/></div>
    </main>
    <footer className="site-footer"><div><a className="wordmark" href="#discover">THE STILL<span>SPIRITS, WITH INSIGHT.</span></a><p>AI Multi-Agent Alcohol Retail · University prototype</p></div>
      <div><span>Customer · Inventory · Business</span><p>Sample data is labelled. Unconnected services stay explicit.</p></div>
      <details><summary>Design references</summary><p>Catalogue organisation inspired by <a href="https://www.danmurphys.com.au/spirits/vodka" target="_blank" rel="noreferrer">Dan Murphy’s</a> and <a href="https://www.thewhiskyexchange.com/c/335/vodka" target="_blank" rel="noreferrer">The Whisky Exchange</a>. Original visual identity and illustrations.</p></details>
    </footer>
  </>;
}
createRoot(document.getElementById("root")!).render(<App/>);
