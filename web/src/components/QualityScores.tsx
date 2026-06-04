import type { QualityScores as Qs } from "../api/types";

interface Props {
  scores: Qs | undefined;
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${Math.round(v * 100)}%`;
}

type MetricDef = {
  noteKey: string;
  label: string;
  definition: string;
  format: (s: Qs) => string | number | null | undefined;
};

const RETRIEVAL_METRICS: MetricDef[] = [
  {
    noteKey: "context_precision",
    label: "Context precision",
    definition: "Share of retrieved wiki text that actually matters for your question.",
    format: (s) => fmtPct(s.context_precision),
  },
  {
    noteKey: "context_recall",
    label: "Context recall",
    definition: "Whether retrieval pulled in enough of the facts needed to answer.",
    format: (s) => fmtPct(s.context_recall),
  },
];

const GENERATION_METRICS: MetricDef[] = [
  {
    noteKey: "faithfulness",
    label: "Faithfulness",
    definition: "Whether claims in the answer are supported by the retrieved excerpts.",
    format: (s) => s.faithfulness,
  },
  {
    noteKey: "relevance",
    label: "Relevance",
    definition: "Whether the answer addresses what you asked.",
    format: (s) => s.relevance,
  },
  {
    noteKey: "prompt_adherence",
    label: "Prompt adherence",
    definition: "Whether the answer follows PoE 1 focus and excerpts-only rules.",
    format: (s) => s.prompt_adherence,
  },
];

function MetricBullet({ def, scores }: { def: MetricDef; scores: Qs }) {
  const val = def.format(scores);
  const note = scores.notes?.[def.noteKey]?.trim();

  return (
    <li className="metric-def-item">
      <span className="metric-def-line">
        <strong>{def.label}</strong>
        {val != null && val !== "—" && (
          <span className="metric-def-score"> — {val}</span>
        )}
        : {def.definition}
      </span>
      {note && (
        <details className="metric-notes-details">
          <summary>Show judge notes</summary>
          <p className="metric-note-text">{note}</p>
        </details>
      )}
    </li>
  );
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

      <details className="panel metrics-help-panel">
        <summary>What do these metrics mean?</summary>
        <div className="metrics-help">
          {hasRetrieval && (
            <>
              <p className="metrics-help-heading">Retrieval</p>
              <ul>
                {RETRIEVAL_METRICS.map((def) => (
                  <MetricBullet key={def.noteKey} def={def} scores={scores} />
                ))}
              </ul>
            </>
          )}
          {hasGeneration && (
            <>
              <p className="metrics-help-heading">Generation</p>
              <ul>
                {GENERATION_METRICS.map((def) => (
                  <MetricBullet key={def.noteKey} def={def} scores={scores} />
                ))}
              </ul>
            </>
          )}
        </div>
      </details>
    </div>
  );
}
