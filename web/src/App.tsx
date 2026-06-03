import { FormEvent, useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  docsUrl,
  getHealth,
  getProvider,
  postQuery,
  setProvider,
} from "./api/client";
import type { HealthResponse, ProviderSettingsResponse, QueryResponse } from "./api/types";
import QualityScores from "./components/QualityScores";
import TimingRow from "./components/TimingRow";
import TracePanels from "./components/TracePanels";
import VoiceRecordButton from "./components/VoiceRecordButton";

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [providerInfo, setProviderInfo] = useState<ProviderSettingsResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [lastQuestion, setLastQuestion] = useState("");

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
    try {
      const data = await postQuery(q);
      setResult(data);
      setLastQuestion(q);
    } catch (err) {
      setQueryError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const modes = providerInfo?.available_modes ?? [];
  const currentMode = providerInfo?.mode ?? health?.provider_mode ?? "stub";
  const showDevUi = health?.inline_eval !== false;

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <h2>System</h2>
        {apiError ? (
          <p className="status-err">{apiError}</p>
        ) : (
          <>
            <p className="status-ok">API: {health?.status ?? "unknown"}</p>
            <p>Indexed chunks: {health?.chunk_count ?? 0}</p>
            <p>Chroma ready: {String(health?.chroma_ready ?? false)}</p>
            {health?.retrieval_mode && (
              <p>
                Retrieval: <code>{health.retrieval_mode}</code>
              </p>
            )}
            {health?.live_retrieval_hint && (
              <p className="caption" style={{ fontSize: "0.85rem" }}>
                {health.live_retrieval_hint}
              </p>
            )}
            {health?.deployment_hint && (
              <p className="status-err" style={{ fontSize: "0.85rem" }}>
                {health.deployment_hint}
              </p>
            )}
            {showDevUi && health?.judge_provider && (
              <p>
                Judges: <code>{health.judge_provider}</code>
                {health.judge_reachable === false ? " (unreachable)" : ""}
              </p>
            )}
            {showDevUi && health?.judge_hint && (
              <p className="status-err" style={{ fontSize: "0.85rem" }}>
                {health.judge_hint}
              </p>
            )}
          </>
        )}

        <h2>Answer mode</h2>
        <label htmlFor="provider">Provider</label>
        <select
          id="provider"
          value={currentMode}
          onChange={(ev) => void handleProviderChange(ev.target.value)}
          disabled={modes.length === 0}
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
        {providerInfo && (
          <p className="caption" style={{ marginTop: "0.5rem" }}>
            Active: <strong>{providerInfo.mode}</strong> ({providerInfo.source})
            {showDevUi && providerInfo.judge_provider && (
              <>
                <br />
                Judges: <strong>{providerInfo.judge_provider}</strong>
                {currentMode === "claude" || currentMode === "gpt4"
                  ? " (matched to answer provider)"
                  : ""}
              </>
            )}
          </p>
        )}

        <h2>Documentation</h2>
        <div className="doc-links">
          <a href={docsUrl("index.html")} target="_blank" rel="noreferrer">
            Docs hub
          </a>
          <a href={docsUrl("architecture.html")} target="_blank" rel="noreferrer">
            Architecture
          </a>
          <a href={docsUrl("changelog.html")} target="_blank" rel="noreferrer">
            Changelog
          </a>
        </div>
      </aside>

      <main className="main">
        <h1>Path of Exile Wiki Agent</h1>
        <p className="caption">
          PoE 1 mechanics Q&A · curated wiki index · Press Enter to submit · mic button
          transcribes into your question
        </p>

        <form onSubmit={(e) => void handleAsk(e)}>
          <label htmlFor="question">Your question</label>
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
            {showDevUi ? "Retrieving, generating, and scoring…" : "Retrieving and generating…"}
          </p>
        )}

        {result && (
          <div className="answer-block">
            <h2>Answer</h2>
            <ReactMarkdown>{result.answer}</ReactMarkdown>
            <p className="meta">
              Run ID: <code>{result.run_id}</code> · Mode: <code>{result.mode}</code>
            </p>

            <QualityScores scores={showDevUi ? result.quality_scores : undefined} />
            {showDevUi && <TimingRow timing={result.trace?.timing_ms} />}

            {result.citations && result.citations.length > 0 && (
              <div className="citations">
                <h3>Sources</h3>
                <ul>
                  {result.citations.map((cite, i) => (
                    <li key={`${cite.url}-${i}`}>
                      <a href={cite.url} target="_blank" rel="noreferrer">
                        {cite.title}
                      </a>
                      {cite.snippet && (
                        <span className="snippet">
                          {cite.snippet.length > 300
                            ? `${cite.snippet.slice(0, 300)}…`
                            : cite.snippet}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {showDevUi && <TracePanels data={result} question={lastQuestion} />}
          </div>
        )}
      </main>
    </div>
  );
}
