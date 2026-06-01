import type { QualityScores as Qs } from "../api/types";
import { docsUrl } from "../api/client";

interface Props {
  scores: Qs | undefined;
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${Math.round(v * 100)}%`;
}

export default function QualityScores({ scores }: Props) {
  if (!scores) return null;

  const hasRetrieval =
    scores.context_precision != null || scores.context_recall != null;
  const hasGeneration =
    scores.faithfulness != null ||
    scores.relevance != null ||
    scores.prompt_adherence != null;

  if (!hasRetrieval && !hasGeneration) return null;

  const retrievalCells = [
    ["Context precision", fmtPct(scores.context_precision)],
    ["Context recall", fmtPct(scores.context_recall)],
  ];

  const generationCells = [
    ["Faithfulness", scores.faithfulness],
    ["Relevance", scores.relevance],
    ["Prompt adherence", scores.prompt_adherence],
  ];

  return (
    <div>
      {hasRetrieval && (
        <>
          <p className="section-label">Retrieval quality (LLM-judged, 0–100%)</p>
          <table className="compact-metrics">
            <tbody>
              <tr>
                {retrievalCells.map(([label, val]) => (
                  <td key={label}>
                    <b>{label}</b>
                    <span className="val">{val ?? "—"}</span>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </>
      )}

      {hasGeneration && (
        <>
          <p className="section-label">Generation quality (1–5, higher is better)</p>
          <table className="compact-metrics">
            <tbody>
              <tr>
                {generationCells.map(([label, val]) => (
                  <td key={label}>
                    <b>{label}</b>
                    <span className="val">{val ?? "—"}</span>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </>
      )}

      <details className="panel">
        <summary>What do these metrics mean?</summary>
        <div className="metrics-help">
          <p>
            Scores are separate LLM judge calls (default: Ollama via{" "}
            <code>JUDGE_PROVIDER</code>). Display-only — they do not change the answer.
          </p>
          <p>
            <strong>Retrieval (Ask):</strong> LLM estimates how relevant retrieved excerpts are
            (context precision) and whether enough was retrieved to answer (context recall).
          </p>
          <p>
            <strong>Evaluate</strong> can still run exact page-title precision/recall when you
            supply gold <code>expected_pages</code>.
          </p>
          <ul>
            <li>Context precision — Share of retrieved text that matters for the question</li>
            <li>Context recall — Whether retrieval captured the facts needed</li>
            <li>Faithfulness — Are answer claims supported by retrieved excerpts?</li>
            <li>Relevance — Does the answer address your question?</li>
            <li>Prompt adherence — PoE 1 only, excerpts-only rules?</li>
          </ul>
          <a
            href={docsUrl("architecture.html#quality-metrics-reference")}
            target="_blank"
            rel="noreferrer"
          >
            Full metrics reference
          </a>
          {scores.notes && Object.keys(scores.notes).length > 0 && (
            <>
              <p>
                <strong>Latest judge notes</strong>
              </p>
              <ul>
                {Object.entries(scores.notes).map(
                  ([k, v]) =>
                    v && (
                      <li key={k}>
                        <small>
                          {k}: {v}
                        </small>
                      </li>
                    ),
                )}
              </ul>
            </>
          )}
        </div>
      </details>
    </div>
  );
}
