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

const SESSION_KEY = "siosa_session_id";

type ConversationTurn = {
  question: string;
  response: QueryResponse;
};

function TurnDetails({
  turn,
  expanded,
  onToggle,
  isLatest,
  inlineEval,
  scoreBusy,
  scoreError,
  qualityScores,
  scoringTiming,
  pipelineTiming,
  onScore,
}: {
  turn: ConversationTurn;
  expanded: boolean;
  onToggle: () => void;
  isLatest: boolean;
  inlineEval: boolean;
  scoreBusy: boolean;
  scoreError: string | null;
  qualityScores?: Qs;
  scoringTiming?: Record<string, number>;
  pipelineTiming?: Record<string, number>;
  onScore: () => void;
}) {
  const response = turn.response;
  const showDetails = isLatest || expanded;
  const scores = isLatest ? qualityScores ?? response.quality_scores : response.quality_scores;
  const timing =
    isLatest && pipelineTiming
      ? pipelineTiming
      : partitionTiming(response.trace?.timing_ms).pipeline;
  const scoring =
    isLatest && scoringTiming
      ? scoringTiming
      : partitionTiming(response.trace?.timing_ms).scoring;

  return (
    <div className={`conversation-turn ${isLatest ? "turn-latest" : ""} ${expanded ? "expanded" : ""}`}>
      <button
        type="button"
        className="turn-header"
        onClick={onToggle}
        aria-expanded={showDetails}
      >
        <span className="turn-question">{turn.question}</span>
        {!isLatest && (
          <span className="turn-toggle">{expanded ? "Collapse" : "Expand"}</span>
        )}
      </button>
      {showDetails && (
        <div className={`answer-block ${isLatest ? "answer-panel" : "turn-panel"}`}>
          <div className="answer-display">
            <ReactMarkdown>{response.answer}</ReactMarkdown>
          </div>

          {Object.keys(timing).length > 0 && (
            <TimingSection title="Pipeline timing" entries={orderedPipelineEntries(timing)} />
          )}

          {!inlineEval && (
            <p className="score-actions">
              <button
                type="button"
                className="btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onScore();
                }}
                disabled={scoreBusy}
              >
                {scoreBusy ? "Scoring…" : "Score response"}
              </button>
              {scoreError && <span className="status-err score-error">{scoreError}</span>}
            </p>
          )}

          {Object.keys(scoring).length > 0 && (
            <TimingSection
              title={`Scoring Timing${
                scoring.evaluation != null ? ` - ${formatSeconds(scoring.evaluation)}` : ""
              }`}
              entries={orderedJudgeEntries(scoring)}
            />
          )}

          <QualityScores scores={scores} />

          {response.citations && response.citations.length > 0 && (
            <div className="citations">
              <h3>Sources</h3>
              <ul>
                {response.citations.map((cite, i) => (
                  <li key={`${cite.url}-${i}`}>
                    <a href={cite.url} target="_blank" rel="noreferrer">
                      {cite.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <TracePanels data={response} />
        </div>
      )}
      {!showDetails && (
        <div className="turn-answer-preview">
          <ReactMarkdown>{response.answer}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState<Awaited<ReturnType<typeof getHealth>> | null>(null);
  const [providerInfo, setProviderInfo] = useState<ProviderSettingsResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(() => {
    try {
      return localStorage.getItem(SESSION_KEY);
    } catch {
      return null;
    }
  });
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [qualityScores, setQualityScores] = useState<Qs | undefined>(undefined);
  const [pipelineTiming, setPipelineTiming] = useState<Record<string, number> | undefined>(
    undefined,
  );
  const [scoringTiming, setScoringTiming] = useState<Record<string, number> | undefined>(
    undefined,
  );
  const [scoringTurnIndex, setScoringTurnIndex] = useState<number | null>(null);
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

  const handleNewConversation = () => {
    try {
      localStorage.removeItem(SESSION_KEY);
    } catch {
      /* ignore */
    }
    setSessionId(null);
    setTurns([]);
    setExpandedIds(new Set());
    setQuestion("");
    setQualityScores(undefined);
    setPipelineTiming(undefined);
    setScoringTiming(undefined);
    setScoringTurnIndex(null);
    setScoreError(null);
    setQueryError(null);
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
    setQualityScores(undefined);
    setPipelineTiming(undefined);
    setScoringTiming(undefined);
    setScoringTurnIndex(null);
    setScoreError(null);
    try {
      const data = await postQuery(q, sessionId);
      if (data.session_id) {
        setSessionId(data.session_id);
        try {
          localStorage.setItem(SESSION_KEY, data.session_id);
        } catch {
          /* ignore */
        }
      }
      setTurns((prev) => [...prev, { question: q, response: data }]);
      setQuestion("");
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
  const currentMode = providerInfo?.mode ?? health?.provider_mode ?? "claude";
  const inlineEval = health?.inline_eval === true;
  const latestIndex = turns.length - 1;

  const handleScore = async (turnIndex: number) => {
    const turn = turns[turnIndex];
    if (!turn) return;
    const chunks = (turn.response.trace?.retrieved_chunks ?? [])
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
      setScoringTurnIndex(turnIndex);
      return;
    }
    setScoreBusy(true);
    setScoringTurnIndex(turnIndex);
    setScoreError(null);
    try {
      const res = await postScore({
        question: turn.question,
        answer: turn.response.answer,
        chunks,
      });
      setTurns((prev) =>
        prev.map((t, i) =>
          i === turnIndex
            ? {
                ...t,
                response: {
                  ...t.response,
                  quality_scores: res.quality_scores,
                  trace: {
                    ...t.response.trace,
                    timing_ms: {
                      ...(t.response.trace?.timing_ms ?? {}),
                      ...(res.timing_ms ?? {}),
                    },
                  },
                },
              }
            : t,
        ),
      );
      if (turnIndex === latestIndex) {
        setQualityScores(res.quality_scores);
        setScoringTiming(res.timing_ms);
      }
    } catch (e) {
      setScoreError(e instanceof Error ? e.message : "Scoring failed");
    } finally {
      setScoreBusy(false);
    }
  };

  const toggleExpand = (index: number) => {
    if (index === latestIndex) return;
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <div className="app-shell">
      <div className="app-stage">
        <img
          className="siosa-portrait"
          src="/art assets/siosa_nobg.png"
          srcSet="/art assets/siosa_nobg.webp 1x, /art assets/siosa_nobg@2x.webp 2x"
          alt=""
          aria-hidden="true"
          decoding="async"
        />
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
              {(modes.length > 0
                ? modes
                : [{ id: "claude", label: "Claude", available: false }]
              ).map(
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
              <span className="question-epigraph">May Reason preserve us.</span>
              <span className="question-ask">What are you curious about today?</span>
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
          {(turns.length > 0 || sessionId) && (
            <p className="session-actions">
              <button
                type="button"
                className="btn"
                onClick={handleNewConversation}
                disabled={loading}
              >
                New conversation
              </button>
            </p>
          )}

          {queryError && <div className="error-banner">{queryError}</div>}
        </section>

        {turns.length > 0 && (
          <div className="conversation-thread" aria-label="Conversation">
            {turns.map((turn, i) => {
              const isLatest = i === latestIndex;
              return (
                <TurnDetails
                  key={`turn-${i}-${turn.response.run_id}`}
                  turn={turn}
                  isLatest={isLatest}
                  expanded={isLatest || expandedIds.has(i)}
                  onToggle={() => toggleExpand(i)}
                  inlineEval={inlineEval}
                  scoreBusy={scoreBusy && scoringTurnIndex === i}
                  scoreError={scoringTurnIndex === i ? scoreError : null}
                  qualityScores={isLatest ? qualityScores : undefined}
                  scoringTiming={isLatest ? scoringTiming : undefined}
                  pipelineTiming={isLatest ? pipelineTiming : undefined}
                  onScore={() => void handleScore(i)}
                />
              );
            })}
          </div>
        )}
        </main>
      </div>

      <footer className="app-footer">
        <nav className="footer-docs" aria-label="Documentation">
          <a href={docsUrl("architecture.html")}>Architecture</a>
          <a href={docsUrl("planned.html")}>Planned</a>
          <a href={docsUrl("changelog.html")}>Changelog</a>
        </nav>
        <p className="footer-disclaimer">
          Not affiliated with or endorsed by Grinding Gear Games. Path of Exile and related assets
          are © Grinding Gear Games. Wiki excerpts via{" "}
          <a href="https://www.poewiki.net" target="_blank" rel="noreferrer">
            poewiki.net
          </a>{" "}
          (CC BY-NC-SA 3.0 where applicable).
        </p>
        <p className="footer-disclaimer footer-privacy">
          <strong>Privacy:</strong> This demo may log coarse request metadata for the operator
          (time, approximate region from IP, and which pages or Asks were used) to understand usage
          while the app is in development. No account is required. Data is not sold. Contact the
          site operator to request deletion of logs.
        </p>
      </footer>
    </div>
  );
}
