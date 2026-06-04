/** Timing keys from API (milliseconds). */

export const PIPELINE_TIMING_ORDER = [
  "plan",
  "retrieval",
  "retrieval_refine",
  "generation",
] as const;

export const JUDGE_TIMING_ORDER = [
  "judge_context_precision",
  "judge_context_recall",
  "judge_faithfulness",
  "judge_relevance",
  "judge_prompt_adherence",
] as const;

const PIPELINE_LABELS: Record<string, string> = {
  plan: "Plan",
  retrieval: "Retrieval",
  retrieval_refine: "Retrieval refine",
  generation: "Generation",
};

const JUDGE_LABELS: Record<string, string> = {
  judge_context_precision: "Context precision",
  judge_context_recall: "Context recall",
  judge_faithfulness: "Faithfulness",
  judge_relevance: "Relevance",
  judge_prompt_adherence: "Prompt adherence",
};

const LLM_PURPOSE_LABELS: Record<string, string> = {
  answer: "Answer",
  judge_faithfulness: "Judge faithfulness",
  judge_relevance: "Judge relevance",
  judge_prompt_adherence: "Judge prompt adherence",
  judge_context_precision: "Judge context precision",
  judge_context_recall: "Judge context recall",
};

export function formatTimingLabel(key: string): string {
  if (JUDGE_LABELS[key]) {
    return JUDGE_LABELS[key];
  }
  if (PIPELINE_LABELS[key]) {
    return PIPELINE_LABELS[key];
  }
  if (key.startsWith("judge_")) {
    return key
      .slice(6)
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function formatLlmPurpose(purpose: string): string {
  if (LLM_PURPOSE_LABELS[purpose]) {
    return LLM_PURPOSE_LABELS[purpose];
  }
  return purpose
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Convert ms to seconds with two significant figures. */
export function formatSeconds(ms: number): string {
  if (!Number.isFinite(ms)) {
    return "—";
  }
  const seconds = ms / 1000;
  if (seconds === 0) {
    return "0 s";
  }
  return `${Number(seconds.toPrecision(2))} s`;
}

export function partitionTiming(timing: Record<string, number> | undefined): {
  pipeline: Record<string, number>;
  scoring: Record<string, number>;
} {
  const pipeline: Record<string, number> = {};
  const scoring: Record<string, number> = {};
  if (!timing) {
    return { pipeline, scoring };
  }
  for (const [key, value] of Object.entries(timing)) {
    if (key === "total") {
      continue;
    }
    if (key.startsWith("judge_") || key === "evaluation") {
      scoring[key] = value;
    } else {
      pipeline[key] = value;
    }
  }
  return { pipeline, scoring };
}

export function orderedPipelineEntries(
  timing: Record<string, number>,
): [string, number][] {
  const seen = new Set<string>();
  const out: [string, number][] = [];
  for (const key of PIPELINE_TIMING_ORDER) {
    if (timing[key] != null) {
      out.push([key, timing[key]]);
      seen.add(key);
    }
  }
  for (const [k, v] of Object.entries(timing)) {
    if (!seen.has(k)) {
      out.push([k, v]);
    }
  }
  return out;
}

export function orderedJudgeEntries(timing: Record<string, number>): [string, number][] {
  const seen = new Set<string>();
  const out: [string, number][] = [];
  for (const key of JUDGE_TIMING_ORDER) {
    if (timing[key] != null) {
      out.push([key, timing[key]]);
      seen.add(key);
    }
  }
  for (const [k, v] of Object.entries(timing)) {
    if (k.startsWith("judge_") && !seen.has(k)) {
      out.push([k, v]);
    }
  }
  return out;
}

/** Bar width as percentage of max in section (min 10%, max 100%). */
export function barWidthPercent(value: number, maxMs: number): number {
  if (!Number.isFinite(value) || value <= 0 || maxMs <= 0) {
    return 10;
  }
  const pct = (value / maxMs) * 100;
  return Math.max(10, Math.min(100, pct));
}
