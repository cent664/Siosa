import type {
  EvaluateResponse,
  HealthResponse,
  ProviderSettingsResponse,
  QueryResponse,
  ScoreRequest,
  ScoreResponse,
  TranscribeResponse,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getProvider(): Promise<ProviderSettingsResponse> {
  return request<ProviderSettingsResponse>("/settings/provider");
}

export function setProvider(mode: string): Promise<ProviderSettingsResponse> {
  return request<ProviderSettingsResponse>("/settings/provider", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
}

export function postQuery(question: string): Promise<QueryResponse> {
  return request<QueryResponse>("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export function postScore(body: ScoreRequest): Promise<ScoreResponse> {
  return request<ScoreResponse>("/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function postEvaluate(
  question: string,
  answer: string,
): Promise<EvaluateResponse> {
  return request<EvaluateResponse>("/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, answer }),
  });
}

export function postTranscribe(audio: Blob, filename = "recording.wav"): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append("audio", audio, filename);
  return request<TranscribeResponse>("/transcribe", {
    method: "POST",
    body: form,
  });
}

export function docsUrl(path: string): string {
  const base = API_BASE || window.location.origin;
  return `${base}/docs/${path.replace(/^\//, "")}`;
}
