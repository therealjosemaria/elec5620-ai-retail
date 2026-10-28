import { useState } from "react";
import type { Product } from "./Catalogue";
import { readApi } from "./api";
import { AgentTrace, type AgentEvent } from "./AgentTrace";

type Decision = {outcome:string; rule:string; limitations:string[]; workflow_id:string; trace:AgentEvent[];
  items:{product_id:string;status:string;stock_quantity:number|null;reorder_threshold:number|null;last_updated:string|null;suggested_quantity:number|null;explanation:string}[]};

export function InventoryDecisions({kind,products}:{kind:"alerts"|"reorder";products:Product[]}) {
  const [token,setToken]=useState("");
  const [selected,setSelected]=useState<string[]>([]);
  const [result,setResult]=useState<Decision|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const reorder=kind==="reorder", prefix=`decision-${kind}`;
  async function run(event:React.FormEvent) {
    event.preventDefault(); if(busy)return;
    setBusy(true);setError("");setResult(null);
    try{setResult(await readApi<Decision>(reorder?"/api/reorder-suggestions":"/api/low-stock-alerts",{
      method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},
      body:JSON.stringify({product_ids:selected})}));}
    catch(e){setError(e instanceof Error?e.message:"Unable to read inventory evidence.");}
    finally{setBusy(false);}
  }
  return <section className="result" aria-label={reorder?"Connected reorder suggestions":"Connected low-stock alerts"}>
    <h2>{reorder?"Reorder suggestions":"Low-stock alerts"}</h2>
    <p>Inventory Agent decisions from current stock evidence. No inventory changes or supplier orders.</p>
    <form onSubmit={run} className="stock-form">
      <label htmlFor={`${prefix}-token`}>Operator token</label>
      <input id={`${prefix}-token`} type="password" autoComplete="off" value={token} required disabled={busy} onChange={e=>{setToken(e.target.value);setResult(null);}}/>
      <fieldset disabled={busy}><legend>Select products · leave all unchecked to review all</legend>
        {products.map(p=><label className="stock-choice" key={p.product_id}>
          <input type="checkbox" checked={selected.includes(p.product_id)} onChange={e=>{setSelected(old=>e.target.checked?[...old,p.product_id]:old.filter(x=>x!==p.product_id));setResult(null);}}/>
          <span>{p.name}</span></label>)}
      </fieldset>
      <button disabled={busy}>{busy?"Checking…":reorder?"Review reorder suggestions":"Review low-stock alerts"}</button>
    </form>
    {error&&<p role="alert" className="error">{error}</p>}
    {result&&<div aria-live="polite"><p role="status">Result: {result.outcome.replaceAll("_"," ")}</p>
      <p>{result.rule}</p><ul>{result.limitations.map(x=><li key={x}>{x}</li>)}</ul>
      <div className="table-scroll" tabIndex={0} aria-label="Inventory decision evidence"><table>
        <thead><tr><th>Product</th><th>Status</th><th>Stock</th><th>Threshold</th>{reorder&&<th>Suggested quantity</th>}<th>Source updated</th><th>Explanation</th></tr></thead>
        <tbody>{result.items.map(x=><tr key={x.product_id}><td>{x.product_id}</td><td>{x.status.replaceAll("_"," ")}</td><td>{x.stock_quantity??"Unknown"}</td><td>{x.reorder_threshold??"Unknown"}</td>{reorder&&<td>{x.suggested_quantity??"Not calculated"}</td>}<td>{x.last_updated??"Unknown"}</td><td>{x.explanation}</td></tr>)}</tbody>
      </table></div><AgentTrace trace={result.trace} workflowId={result.workflow_id}/>
    </div>}
  </section>;
}

type Demand = {outcome:string;scope:{start_date:string;end_date:string};comparison_start:string|null;comparison_end:string|null;units_sold:number|null;comparison_units:number|null;change:number|null;percent_change:string|null;trend:string|null;rule:string;limitations:string[];workflow_id:string;trace:AgentEvent[]};

export function DemandTrends({products}:{products:Product[]}) {
  const [token,setToken]=useState("");
  const [scope,setScope]=useState("product");
  const [product,setProduct]=useState("product-001");
  const [category,setCategory]=useState("Wine");
  const [start,setStart]=useState("2026-09-01"),[end,setEnd]=useState("2026-09-30");
  const [result,setResult]=useState<Demand|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  async function run(event:React.FormEvent){
    event.preventDefault();if(busy)return;setBusy(true);setResult(null);setError("");
    try{setResult(await readApi<Demand>("/api/demand-trends",{method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},
      body:JSON.stringify({...(scope==="product"?{product_id:product}:{category}),start_date:start,end_date:end})}));}
    catch(e){setError(e instanceof Error?e.message:"Demand analysis failed.");}finally{setBusy(false);}
  }
  return <section className="result" aria-label="Connected demand trends">
    <p className="eyebrow">UC-M5-02</p><h2>Demand trends</h2>
    <p>Compare completed sales quantities with the preceding equal-length period. This is historical analysis, not a forecast.</p>
    <form className="stock-form" onSubmit={run} onChange={()=>setResult(null)}>
      <label htmlFor="demand-token">Business access token</label><input id="demand-token" type="password" autoComplete="off" value={token} required disabled={busy} onChange={e=>setToken(e.target.value)}/>
      <label htmlFor="demand-scope">Analysis scope</label><select id="demand-scope" value={scope} disabled={busy} onChange={e=>setScope(e.target.value)}><option value="product">Product</option><option value="category">Category</option></select>
      {scope==="product"?<><label htmlFor="demand-product">Analysis product</label><select id="demand-product" value={product} required disabled={busy} onChange={e=>setProduct(e.target.value)}>{products.map(p=><option key={p.product_id} value={p.product_id}>{p.name}</option>)}</select></>:<><label htmlFor="demand-category">Analysis category</label><select id="demand-category" value={category} disabled={busy} onChange={e=>setCategory(e.target.value)}>{[...new Set(products.map(p=>p.category))].map(c=><option key={c}>{c}</option>)}</select></>}
      <label htmlFor="demand-start">Sales period start</label><input id="demand-start" type="date" value={start} required disabled={busy} onChange={e=>setStart(e.target.value)}/>
      <label htmlFor="demand-end">Sales period end</label><input id="demand-end" type="date" value={end} required disabled={busy} onChange={e=>setEnd(e.target.value)}/>
      <small>Default dates match the labelled prototype sales dataset. Both periods must be historical.</small>
      <button disabled={busy}>{busy?"Analysing…":"Review demand trends"}</button>
    </form>
    {error&&<p role="alert" className="error">{error}</p>}
    {result&&<div aria-live="polite"><p role="status">Trend result: {result.outcome.replaceAll("_"," ")}</p>
      <p>Analysed period: {result.scope.start_date} – {result.scope.end_date}</p>
      <p>Comparison: {result.comparison_start??"Unknown"} – {result.comparison_end??"Unknown"}</p>
      <dl>{[["Analysed units",result.units_sold],["Comparison units",result.comparison_units],["Change (units)",result.change],["Change (%)",result.percent_change],["Trend",result.trend]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value??"Unknown"}</dd></div>)}</dl>
      <p>{result.rule}</p><ul>{result.limitations.map(x=><li key={x}>{x}</li>)}</ul>
      <AgentTrace trace={result.trace} workflowId={result.workflow_id}/>
    </div>}
  </section>;
}
