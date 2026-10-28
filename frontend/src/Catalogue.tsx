import { useEffect, useId, useRef, useState } from "react";

export type Product = {
  product_id: string; name: string; category: string; price: string;
  abv: string; sweetness: string; flavour_tags: string[];
};

// Original vector illustration, not a photograph or a claim about product packaging.
export function Bottle({ kind = "Spirits", hero = false }: { kind?: string; hero?: boolean }) {
  const id = useId().replaceAll(":", "");
  const wine = kind === "Wine";
  const beer = kind === "Beer";
  const body = wine ? "#485344" : beer ? "#9c6139" : "#dce5dc";
  return <svg viewBox="0 0 240 420" className={`bottle ${hero ? "hero-bottle" : ""}`} aria-hidden="true">
    <defs>
      <linearGradient id={id} x1="0" x2="1"><stop stopColor={body}/><stop offset=".35" stopColor={wine ? "#68745d" : beer ? "#bc8754" : "#f1f4ed"}/><stop offset="1" stopColor={body}/></linearGradient>
      <linearGradient id={`${id}cap`} x1="0" x2="1"><stop stopColor="#444c3e"/><stop offset=".5" stopColor="#7d846c"/><stop offset="1" stopColor="#3e493a"/></linearGradient>
    </defs>
    <ellipse cx="120" cy="400" rx="63" ry="9" fill="#283121" opacity=".10"/>
    <path d="M98 50 L142 50 L142 119 Q142 137 165 154 Q178 166 178 188 L178 371 Q178 391 158 391 L82 391 Q62 391 62 371 L62 188 Q62 166 75 154 Q98 137 98 119 Z" fill={`url(#${id})`} stroke={wine ? "#334331" : "#abb6a6"} strokeWidth="1.5"/>
    <path d="M105 64 L105 122 Q105 145 83 164 Q75 173 75 191 L75 367" fill="none" stroke="white" strokeWidth="5" opacity=".4"/>
    <rect x="96" y="27" width="48" height="42" rx="4" fill={`url(#${id}cap)`}/>
    <path d="M99 58 H141 M99 62 H141" stroke="#aeb39e" strokeWidth="1"/>
    <rect x="69" y="211" width="102" height="119" rx="1" fill="#f8f6ec" stroke="#e0ddcb"/>
    <text x="120" y="235" textAnchor="middle" fontSize="8" letterSpacing="3" fill="#657057">THE STILL</text>
    <path d="M91 247 H149" stroke="#9f9c83" strokeWidth=".6"/>
    <text x="120" y="272" textAnchor="middle" fontSize={beer ? "22" : "20"} fontFamily="Georgia, serif" fill="#394b35">{wine ? "WINE" : beer ? "BEER" : "VODKA"}</text>
    <text x="120" y="289" textAnchor="middle" fontSize="6.5" letterSpacing="2" fill="#747a65">CATALOGUE EDITION</text>
    <circle cx="120" cy="310" r="8" fill="none" stroke="#8b927b" strokeWidth=".7"/>
    <path d="M116 313 L120 305 L124 313 Z" fill="none" stroke="#8b927b" strokeWidth=".7"/>
    <path d="M78 377 H162" stroke="white" opacity=".4" strokeWidth="3"/>
  </svg>;
}

export function ProductDetail({ product, close }: { product: Product; close: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { ref.current?.showModal(); }, []);
  return <dialog ref={ref} className="product-dialog" onCancel={close} aria-labelledby="detail-name">
    <button className="dialog-close text-button" aria-label="Close product details" onClick={close}>×</button>
    <div className="detail-art"><Bottle kind={product.category}/><small>Illustration · packaging may differ</small></div>
    <div className="detail-copy"><p className="eyebrow">{product.category} / CATALOGUE</p>
      <h2 id="detail-name">{product.name}</h2><p className="detail-price">{product.price}<span> catalogue price</span></p>
      <dl><div><dt>Alcohol</dt><dd>{product.abv}% ABV</dd></div><div><dt>Sweetness</dt><dd>{product.sweetness}</dd></div>
        <div><dt>Flavour</dt><dd>{product.flavour_tags.join(", ") || "Not specified"}</dd></div></dl>
      <p className="muted">Availability has not been checked. Prototype catalogue prices are in AUD.</p>
      <small>{product.product_id}</small>
    </div>
  </dialog>;
}

export function Catalogue({ products, loading, error }: { products: Product[]; loading: boolean; error: string }) {
  const [category, setCategory] = useState("All");
  const [query, setQuery] = useState("");
  const [detail, setDetail] = useState<Product | null>(null);
  const filtered = products.filter(p => (category === "All" || p.category === category)
    && `${p.name} ${p.flavour_tags.join(" ")}`.toLowerCase().includes(query.trim().toLowerCase()));
  const ordered = [...filtered].sort((a, b) => Number(b.category === "Spirits") - Number(a.category === "Spirits"));
  return <section id="collection" className="collection" aria-labelledby="collection-title">
    <div className="section-heading"><div><p className="eyebrow">THE COLLECTION</p><h2 id="collection-title">Find your next favourite.</h2></div>
      <span className="muted">{loading ? "Loading catalogue…" : `${products.length} catalogue products`}</span></div>
    <div className="catalogue-toolbar"><div className="filter-pills" role="group" aria-label="Product category">
      {["All", "Spirits", "Wine", "Beer"].map(c => <button key={c} aria-pressed={category === c} onClick={() => setCategory(c)}>{c === "All" ? "All bottles" : c}</button>)}
    </div><label className="search-label"><span className="sr-only">Search catalogue</span><span aria-hidden="true">⌕</span><input type="search" placeholder="Search the collection" value={query} onChange={e => setQuery(e.target.value)}/></label></div>
    {error && <p role="alert" className="error">{error}</p>}
    {!loading && !error && !ordered.length && <p className="empty-state" role="status">No products match this search. Try another name or category.</p>}
    <div className="catalogue-grid">{ordered.map((p, index) => <article className="catalogue-card" key={p.product_id}>
      <button className={`catalogue-art art-${p.category.toLowerCase()}`} onClick={() => setDetail(p)} aria-label={`View ${p.name}`}>
        {p.category === "Spirits" && <span className="art-label">IN THE SPOTLIGHT</span>}
        <Bottle kind={p.category}/><span className="art-number">{String(index + 1).padStart(2, "0")}</span><span className="art-arrow" aria-hidden="true">↗</span>
      </button>
      <div className="card-meta"><span>{p.category}</span><span>{p.abv}% ABV</span></div>
      <h3><button className="text-button" onClick={() => setDetail(p)}>{p.name}</button></h3>
      <p className="card-bottom"><span>{p.flavour_tags.slice(0, 2).join(" · ") || "Flavour not specified"}</span><strong>{p.price}</strong></p>
    </article>)}</div>
    <p className="catalogue-note">Project catalogue prices in AUD · availability unchecked · original bottle illustrations</p>
    {detail && <ProductDetail product={detail} close={() => setDetail(null)}/>}
  </section>;
}
