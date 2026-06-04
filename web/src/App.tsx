import { FormEvent, useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  docsUrl,
  getHealth,
  getProvider,
  postQuery,
  postScore,
  setProvider,
} from "./api/client";
import type { QualityScores as Qs } from "./api/types";
import type { ProviderSettingsResponse, QueryResponse } from "./api/types";
import QualityScores from "./components/QualityScores";
import { TimingSection } from "./components/TimingRow";
import {
  formatSeconds,
  orderedJudgeEntries,
  orderedPipelineEntries,
} from "./components/timingFormat";
import TracePanels from "./components/TracePanels";
import { partitionTiming } from "./components/timingFormat";
import VoiceRecordButton from "./components/VoiceRecordButton";

export default function App() {
  const [health, setHealth] = useState<Awaited<ReturnType<typeof getHealth>> | null>(null);
  const [providerInfo, setProviderInfo] = useState<ProviderSettingsResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [lastQuestion, setLastQuestion] = useState("");
  const [qualityScores, setQualityScores] = useState<Qs | undefined>(undefined);
  const [pipelineTiming, setPipelineTiming] = useState<Record<string, number> | undefined>(
    undefined,
  );
  const [scoringTiming, setScoringTiming] = useState<Record<string, number> | undefined>(
    undefined,
  );
  const [scoreBusy, setScoreBusy] = useState(false);
  const [scoreError, setScoreError] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const [h, p] = await Promise.all([getHealth(), getProvider()]);
      setHealth(h);
      setProviderInfo(p);
      setApiError(null);
    } catch (e) {
      setApiError(e instanceof Error ? e.message : "API not reachable");
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const handleProviderChange = async (mode: string) => {
    try {
      const p = await setProvider(mode);
      setProviderInfo(p);
      setApiError(null);
      await refreshStatus();
    } catch (e) {
      setApiError(e instanceof Error ? e.message : "Could not set provider");
    }
  };

  const handleAsk = async (e?: FormEvent) => {
    e?.preventDefault();
    const q = question.trim();
    if (!q) {
      setQueryError("Enter a question first.");
      return;
    }
    setQueryError(null);
    setLoading(true);
    setResult(null);
    setQualityScores(undefined);
    setPipelineTiming(undefined);
    setScoringTiming(undefined);
    setScoreError(null);
    try {
      const data = await postQuery(q);
      setResult(data);
      setLastQuestion(q);
      const { pipeline, scoring } = partitionTiming(data.trace?.timing_ms);
      setPipelineTiming(Object.keys(pipeline).length > 0 ? pipeline : undefined);
      if (health?.inline_eval) {
        setQualityScores(data.quality_scores);
        setScoringTiming(Object.keys(scoring).length > 0 ? scoring : undefined);
      }
    } catch (err) {
      setQueryError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const modes = providerInfo?.available_modes ?? [];
  const currentMode = providerInfo?.mode ?? health?.provider_mode ?? "stub";
  const showDevUi = health?.dev_ui_enabled !== false;
  const inlineEval = health?.inline_eval === true;

  const handleScore = async () => {
    if (!result || !lastQuestion) return;
    const chunks = (result.trace?.retrieved_chunks ?? [])
      .filter((ch) => ch.text && ch.text.trim().length > 0)
      .map((ch) => ({
        page_title: ch.page_title ?? "",
        wiki_url: ch.wiki_url ?? "",
        text: ch.text!,
        chunk_id: ch.chunk_id,
        score: ch.score ?? null,
      }));
    if (chunks.length === 0) {
      setScoreError("No chunk text in trace — restart API after update.");
      return;
    }
    setScoreBusy(true);
    setScoreError(null);
    try {
      const res = await postScore({
        question: lastQuestion,
        answer: result.answer,
        chunks,
      });
      setQualityScores(res.quality_scores);
      setScoringTiming(res.timing_ms);
    } catch (e) {
      setScoreError(e instanceof Error ? e.message : "Scoring failed");
    } finally {
      setScoreBusy(false);
    }
  };

  return (
    <div className="app-shell">
      <div className="siosa-portrait" role="presentation" aria-hidden="true" />
      <main className="main">
        <header className="app-header">
          <h1 className="app-title">Siosa&apos;s Library</h1>
          <div className="provider-row">
            <label htmlFor="provider">Provider</label>
            <select
              id="provider"
              value={currentMode}
              onChange={(ev) => void handleProviderChange(ev.target.value)}
              disabled={modes.length === 0 || !!apiError}
            >
              {(modes.length > 0 ? modes : [{ id: "stub", label: "Stub", available: true }]).map(
                (m) => (
                  <option key={m.id} value={m.id} disabled={!m.available}>
                    {m.label}
                    {!m.available ? " (needs API key)" : ""}
                  </option>
                ),
              )}
            </select>
          </div>
        </header>

        {apiError && <div className="error-banner">{apiError}</div>}
        {health?.deployment_hint && (
          <div className="error-banner">{health.deployment_hint}</div>
        )}

        <section className="question-section">
          <form className="question-form" onSubmit={(e) => void handleAsk(e)}>
            <label htmlFor="question" className="question-prompt">
              May Reason preserve us. What are we curious about today?
            </label>
            <div className="question-row">
              <input
                id="question"
                type="text"
                placeholder="How does poison damage scale?"
                maxLength={2000}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={loading}
              />
              <VoiceRecordButton
                onTranscribed={setQuestion}
                onError={setQueryError}
                disabled={loading}
              />
              <button type="submit" className="btn btn-primary" disabled={loading}>
                Ask
              </button>
            </div>
          </form>

          {queryError && <div className="error-banner">{queryError}</div>}
          {loading && (
            <p className="spinner">
              {inlineEval
                ? "Retrieving, generating, and scoring…"
                : "Retrieving and generating…"}
            </p>
          )}
        </section>

        {result && (
          <div className="answer-block answer-panel">
            <div className="answer-display">
              <ReactMarkdown>{result.answer}</ReactMarkdown>
            </div>

            {showDevUi && pipelineTiming && (
              <TimingSection
                title="Pipeline timing"
                entries={orderedPipelineEntries(pipelineTiming)}
              />
            )}

            {showDevUi && !inlineEval && (
              <p className="score-actions">
                <button
                  type="button"
                  className="btn"
                  onClick={() => void handleScore()}
                  disabled={scoreBusy}
                >
                  {scoreBusy ? "Scoring…" : "Score response"}
                </button>
                {scoreError && <span className="status-err score-error">{scoreError}</span>}
              </p>
            )}

            {showDevUi && scoringTiming && (
              <TimingSection
                title={`Scoring Timing${
                  scoringTiming.evaluation != null
                    ? ` - ${formatSeconds(scoringTiming.evaluation)}`
                    : ""
                }`}
                entries={orderedJudgeEntries(scoringTiming)}
              />
            )}

            <QualityScores scores={showDevUi ? qualityScores ?? result.quality_scores : undefined} />

            {result.citations && result.citations.length > 0 && (
              <div className="citations">
                <h3>Sources</h3>
                <ul>
                  {result.citations.map((cite, i) => (
                    <li key={`${cite.url}-${i}`}>
                      <a href={cite.url} target="_blank" rel="noreferrer">
                        {cite.title}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {showDevUi && <TracePanels data={result} />}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <nav className="footer-docs" aria-label="Documentation">
          <a href={docsUrl("architecture.html")} target="_blank" rel="noreferrer">
            Architecture
          </a>
          <a href={docsUrl("changelog.html")} target="_blank" rel="noreferrer">
            Changelog
          </a>
        </nav>
      </footer>
    </div>
  );
}
