import type {
  PageFetched,
  QueryResponse,
  RetrievedChunkTrace,
  ToolCallTrace,
} from "../api/types";
import { formatLlmPurpose, formatSeconds } from "./timingFormat";

interface Props {
  data: QueryResponse;
}

function sortChunks(chunks: RetrievedChunkTrace[]): RetrievedChunkTrace[] {
  return [...chunks].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
}

export default function TracePanels({ data }: Props) {
  const trace = data.trace ?? {};
  const chunks = sortChunks(trace.retrieved_chunks ?? []);

  return (
    <>
      <details className="panel">
        <summary>Agent reasoning trace</summary>

        <div className="trace-summary">
          <p>
            <strong>Pipeline:</strong> <code>{trace.pipeline ?? ""}</code>
          </p>
          {trace.retrieval_mode && (
            <p>
              <strong>Retrieval mode:</strong> <code>{trace.retrieval_mode}</code>
              {trace.retrieval_source && (
                <>
                  {" "}
                  · <strong>Source:</strong> <code>{trace.retrieval_source}</code>
                </>
              )}
            </p>
          )}
          {trace.retrieval_config && Object.keys(trace.retrieval_config).length > 0 && (
            <p className="caption">
              Config: max pages {String(trace.retrieval_config.max_pages)}, fused queries{" "}
              {String(trace.retrieval_config.max_search_queries)}, title probe{" "}
              {String(trace.retrieval_config.title_probe)}
            </p>
          )}
          {trace.retrieval_refined && (
            <p className="trace-refine-banner">
              <strong>Retrieval refined</strong>
              {trace.retrieval_gate_reason && (
                <> (gate: {trace.retrieval_gate_reason})</>
              )}
              {trace.refine_queries && trace.refine_queries.length > 0 && (
                <>
                  {" "}
                  — queries: {trace.refine_queries.map((q) => `"${q}"`).join(", ")}
                </>
              )}
            </p>
          )}
        </div>

        {trace.plan && trace.plan.length > 0 && (
          <section className="trace-section">
            <h4>Plan</h4>
            <ol className="trace-plan-list">
              {trace.plan.map((step, i) => (
                <li key={`plan-${i}`}>
                  <code>{step.action ?? "retrieve"}</code>
                  {step.query && <span> — {step.query}</span>}
                </li>
              ))}
            </ol>
          </section>
        )}

        {trace.tool_calls && trace.tool_calls.length > 0 && (
          <section className="trace-section">
            <h4>Tool calls</h4>
            {trace.tool_calls.map((call, i) => (
              <ToolCallPanel key={`tool-${i}`} call={call} index={i + 1} />
            ))}
          </section>
        )}

        {chunks.length > 0 && (
          <section className="trace-section">
            <h4>Retrieved chunks ({chunks.length})</h4>
            <div className="trace-table-wrap">
              <table className="trace-table">
                <thead>
                  <tr>
                    <th>Page</th>
                    <th>Score</th>
                    <th>Reason</th>
                    <th>Search query</th>
                    <th>Preview</th>
                  </tr>
                </thead>
                <tbody>
                  {chunks.map((ch, i) => (
                    <tr key={ch.chunk_id ?? `chunk-${i}`}>
                      <td>
                        {ch.wiki_url ? (
                          <a href={ch.wiki_url} target="_blank" rel="noreferrer">
                            {ch.page_title ?? "Wiki"}
                          </a>
                        ) : (
                          ch.page_title ?? "—"
                        )}
                      </td>
                      <td>{ch.score != null ? ch.score.toFixed(3) : "—"}</td>
                      <td>
                        <code>{ch.fetch_reason ?? "—"}</code>
                      </td>
                      <td className="trace-cell-narrow">
                        {ch.search_query ? (
                          <span title={ch.search_query}>{ch.search_query}</span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="trace-preview">{ch.text_preview ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <details className="trace-raw-json">
          <summary>Raw trace JSON</summary>
          <pre className="json-block">{JSON.stringify(trace, null, 2)}</pre>
        </details>
      </details>

      {trace.llm_calls && trace.llm_calls.length > 0 && (
        <div className="llm-calls-section">
          <h3>LLM calls</h3>
          {trace.llm_calls.map((call) => (
            <details key={call.call_id} className="panel llm-call">
              <summary>
                {formatLlmPurpose(call.purpose)} · {call.provider} ·{" "}
                {formatSeconds(call.latency_ms)}
              </summary>
              <p className="caption">
                Model: <code>{call.model}</code>
              </p>
              <p>
                <strong>System prompt</strong>
              </p>
              <pre className="code-block">{call.system_prompt}</pre>
              <p>
                <strong>User prompt</strong>
              </p>
              <pre className="code-block">{call.user_prompt}</pre>
              <p>
                <strong>Response</strong>
              </p>
              <pre className="code-block">{call.response}</pre>
            </details>
          ))}
        </div>
      )}
    </>
  );
}

function ToolCallPanel({ call, index }: { call: ToolCallTrace; index: number }) {
  const debug = call.retrieval_debug;
  const label =
    call.query === "refine"
      ? `Refine pass ${index}`
      : `wiki_search ${index}: ${call.query ?? ""}`;

  return (
    <details className="panel trace-tool-panel">
      <summary>
        {label} — {call.result_count ?? 0} chunks
      </summary>
      {call.refine_queries && call.refine_queries.length > 0 && (
        <p>
          <strong>Refine queries:</strong> {call.refine_queries.join(", ")}
        </p>
      )}
      {debug ? (
        <RetrievalDebugBlock debug={debug} />
      ) : (
        <p className="caption">No live retrieval debug (local index only).</p>
      )}
    </details>
  );
}

function RetrievalDebugBlock({ debug }: { debug: NonNullable<ToolCallTrace["retrieval_debug"]> }) {
  return (
    <div className="trace-debug-block">
      {debug.user_question && (
        <p>
          <strong>User question:</strong> {debug.user_question}
        </p>
      )}
      {debug.subtask_query && debug.subtask_query !== debug.user_question && (
        <p>
          <strong>Subtask query:</strong> {debug.subtask_query}
        </p>
      )}
      {debug.fused_search_queries && debug.fused_search_queries.length > 0 && (
        <>
          <p>
            <strong>Fused MediaWiki searches</strong>
          </p>
          <ul>
            {debug.fused_search_queries.map((q, i) => (
              <li key={`fq-${i}`}>{q}</li>
            ))}
          </ul>
        </>
      )}
      {debug.title_probe_candidates && debug.title_probe_candidates.length > 0 && (
        <>
          <p>
            <strong>Title probes</strong>
          </p>
          <ul>
            {debug.title_probe_candidates.map((t, i) => (
              <li key={`tp-${i}`}>
                <code>{t}</code>
              </li>
            ))}
          </ul>
        </>
      )}
      {debug.search_errors && debug.search_errors.length > 0 && (
        <>
          <p>
            <strong>Search errors</strong>
          </p>
          <ul>
            {debug.search_errors.map((e, i) => (
              <li key={`se-${i}`} className="status-err">
                {e}
              </li>
            ))}
          </ul>
        </>
      )}
      {debug.pages_fetched && debug.pages_fetched.length > 0 && (
        <>
          <p>
            <strong>Pages fetched</strong>
          </p>
          <PagesTable pages={debug.pages_fetched} />
        </>
      )}
      {debug.chunks_returned != null && (
        <p className="caption">Chunks returned after rerank: {debug.chunks_returned}</p>
      )}
    </div>
  );
}

function PagesTable({ pages }: { pages: PageFetched[] }) {
  return (
    <div className="trace-table-wrap">
      <table className="trace-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Reason</th>
            <th>Surfaced by</th>
            <th>OK</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          {pages.map((p, i) => (
            <tr key={`${p.path}-${i}`}>
              <td>
                <a href={p.wiki_url} target="_blank" rel="noreferrer">
                  {p.title}
                </a>
              </td>
              <td>
                <code>{p.fetch_reason}</code>
              </td>
              <td>{p.search_query || "—"}</td>
              <td>{p.fetch_ok === false ? "no" : "yes"}</td>
              <td className="caption">{p.fetch_error || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
