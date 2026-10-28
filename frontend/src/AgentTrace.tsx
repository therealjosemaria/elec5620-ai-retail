export type AgentEvent = {sender: string; receiver: string; operation: string; status: string; product_ids: string[]};

export function AgentTrace({trace, workflowId}: {trace: AgentEvent[]; workflowId: string}) {
  return <details className="agent-trace" open>
    <summary>Agent communication</summary>
    <p><small>Workflow: {workflowId}</small></p>
    <div className="table-scroll" tabIndex={0} aria-label="Agent communication trace"><table>
      <thead><tr><th>From</th><th>To</th><th>Action</th><th>Result</th><th>Products</th></tr></thead>
      <tbody>{trace.map((step, index) => <tr key={index}>
        <td>{step.sender.replaceAll("_", " ")}</td><td>{step.receiver.replaceAll("_", " ")}</td>
        <td>{step.operation.replaceAll("_", " ")}</td><td>{step.status.replaceAll("_", " ")}</td>
        <td>{step.product_ids.join(", ") || "—"}</td>
      </tr>)}</tbody>
    </table></div>
  </details>;
}
