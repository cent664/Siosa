import {
  barWidthPercent,
  formatSeconds,
  formatTimingLabel,
  orderedJudgeEntries,
  orderedPipelineEntries,
} from "./timingFormat";

interface Props {
  pipeline?: Record<string, number>;
  scoring?: Record<string, number>;
}

function TimingBarChart({ entries }: { entries: [string, number][] }) {
  if (entries.length === 0) {
    return null;
  }
  const maxMs = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <div className="timing-bars">
      {entries.map(([key, ms]) => (
        <div key={key} className="timing-bar-row">
          <div className="timing-bar-meta">
            <span className="timing-bar-label">{formatTimingLabel(key)}</span>
            <span className="timing-bar-val">{formatSeconds(ms)}</span>
          </div>
          <div className="timing-bar-track">
            <div
              className="timing-bar-fill"
              style={{ width: `${barWidthPercent(ms, maxMs)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function TimingSection({
  title,
  entries,
}: {
  title: string;
  entries: [string, number][];
}) {
  if (entries.length === 0) {
    return null;
  }
  return (
    <div className="timing-section">
      <p className="section-label">{title}</p>
      <TimingBarChart entries={entries} />
    </div>
  );
}

export default function TimingRow({ pipeline, scoring }: Props) {
  const pipelineEntries = pipeline ? orderedPipelineEntries(pipeline) : [];
  const judgeEntries = scoring ? orderedJudgeEntries(scoring) : [];
  const evalMs = scoring?.evaluation;

  if (pipelineEntries.length === 0 && judgeEntries.length === 0) {
    return null;
  }

  return (
    <div className="timing-sections">
      <TimingSection title="Pipeline timing" entries={pipelineEntries} />
      {judgeEntries.length > 0 && (
        <TimingSection
          title={`Scoring Timing${evalMs != null ? ` - ${formatSeconds(evalMs)}` : ""}`}
          entries={judgeEntries}
        />
      )}
    </div>
  );
}
