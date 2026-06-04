export interface Citation {
  title: string;
  url: string;
  snippet?: string;
}

export interface LLMCallTrace {
  call_id: string;
  purpose: string;
  provider: string;
  model: string;
  system_prompt: string;
  user_prompt: string;
  response: string;
  latency_ms: number;
  token_counts?: Record<string, number>;
}

export interface QualityScores {
  context_precision?: number | null;
  context_recall?: number | null;
  faithfulness?: number | null;
  relevance?: number | null;
  prompt_adherence?: number | null;
  notes?: Record<string, string>;
}

export interface RetrievalDebug {
  subtask_query?: string;
  user_question?: string;
  fused_search_queries?: string[];
  title_probe_candidates?: string[];
  pages_fetched?: PageFetched[];
  chunks_returned?: number;
}

export interface PageFetched {
  title: string;
  path: string;
  wiki_url: string;
  fetch_reason: string;
  search_query?: string;
  fetch_ok?: boolean;
}

export interface ToolCallTrace {
  tool: string;
  query?: string;
  result_count?: number;
  refine_queries?: string[];
  retrieval_debug?: RetrievalDebug;
}

export interface RetrievedChunkTrace {
  chunk_id?: string;
  page_title?: string;
  wiki_url?: string;
  score?: number;
  retrieval?: string;
  fetch_reason?: string;
  search_query?: string;
  text_preview?: string;
  /** Full excerpt for on-demand /score (dev UI only). */
  text?: string;
}

export interface PlanStep {
  action?: string;
  query?: string;
}

export interface QueryTrace {
  pipeline?: string;
  retrieval_source?: string;
  retrieval_mode?: string;
  retrieval_config?: Record<string, unknown>;
  retrieval_refined?: boolean;
  refine_queries?: string[];
  retrieval_gate_reason?: string;
  plan?: PlanStep[];
  tool_calls?: ToolCallTrace[];
  retrieved_chunks?: RetrievedChunkTrace[];
  timing_ms?: Record<string, number>;
  llm_calls?: LLMCallTrace[];
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  run_id: string;
  mode: string;
  retrieved_count: number;
  trace?: QueryTrace;
  quality_scores?: QualityScores;
}

export interface HealthResponse {
  status: string;
  provider_mode: string;
  chunk_count: number;
  chroma_ready: boolean;
  retrieval_mode?: string;
  live_retrieval_hint?: string;
  inline_eval?: boolean;
  dev_ui_enabled?: boolean;
  deployment_profile?: string;
  deployment_hint?: string;
  judge_provider?: string;
  judge_reachable?: boolean;
  judge_hint?: string;
}

export interface ProviderModeInfo {
  id: string;
  label: string;
  available: boolean;
}

export interface ProviderSettingsResponse {
  mode: string;
  source: string;
  available_modes: ProviderModeInfo[];
  judge_provider?: string;
  judge_reachable?: boolean;
  judge_hint?: string;
}

export interface EvaluateResponse {
  run_id: string;
  metrics: Record<string, unknown>;
}

export interface ScoreChunkInput {
  page_title?: string;
  wiki_url?: string;
  text: string;
  chunk_id?: string;
  score?: number | null;
}

export interface ScoreRequest {
  question: string;
  answer: string;
  chunks: ScoreChunkInput[];
}

export interface ScoreResponse {
  run_id: string;
  quality_scores: QualityScores;
  timing_ms?: Record<string, number>;
}

export interface TranscribeResponse {
  text: string;
}
