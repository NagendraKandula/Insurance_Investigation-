// Typed client for the FastAPI backend (api/main.py).

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type RiskLevel = "HIGH" | "MEDIUM" | "LOW";

export interface Coverage {
  threshold: number;
  flagged_total: number;
  flagged_in_labelled_set: number;
  flagged_outside_labelled_set: number;
  note: string;
}

export interface Metrics {
  precision: number;
  recall: number;
  f1_score: number;
  accuracy: number;
}

export interface ConfusionMatrix {
  TP: number;
  FP: number;
  TN: number;
  FN: number;
}

export interface Summary {
  total_entities: number;
  by_risk_level: Record<string, number>;
  by_entity_type: Record<string, number>;
  by_indicator_type: Record<string, number>;
  detector_findings: Record<string, number>;
  evaluation: {
    threshold: number;
    metrics: Metrics;
    confusion_matrix: ConfusionMatrix;
  };
  coverage: Coverage;
}

export interface PatternMetrics extends ConfusionMatrix {
  precision: number;
  recall: number;
  f1_score: number;
}

export interface Evaluation {
  threshold: number;
  metrics: Metrics;
  confusion_matrix: ConfusionMatrix;
  pattern_metrics: Record<string, PatternMetrics>;
  coverage: Coverage;
}

export interface EntityScore {
  entity_type: string;
  entity_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  signal_count: number;
  indicator_types: string[];
}

export interface EntityPage {
  total: number;
  limit: number;
  offset: number;
  items: EntityScore[];
}

export interface Signal {
  indicator_type: string;
  weight: number;
  evidence: Record<string, unknown>;
}

export interface EntityDetail extends EntityScore {
  signals: Signal[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function get<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  const url = new URL(path, API_BASE);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  }

  let response: Response;
  try {
    response = await fetch(url, { cache: "no-store" });
  } catch {
    throw new ApiError(
      `Cannot reach the API at ${API_BASE}. Start it with: uvicorn api.main:app --port 8000`,
      0,
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* keep the status text */
    }
    throw new ApiError(String(detail), response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  summary: () => get<Summary>("/summary"),
  evaluation: () => get<Evaluation>("/evaluation"),
  riskScores: (params: {
    entity_type?: string;
    risk_level?: string;
    indicator_type?: string;
    limit?: number;
    offset?: number;
  }) => get<EntityPage>("/risk-scores", params),
  entity: (type: string, id: string) =>
    get<EntityDetail>(
      `/risk-scores/${encodeURIComponent(type)}/${encodeURIComponent(id)}`,
    ),
};
