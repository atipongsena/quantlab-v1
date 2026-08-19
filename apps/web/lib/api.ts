/**
 * Typed reader for the QuantLab API.
 *
 * A missing artifact is a normal state, not an error: the CLI has simply not produced
 * that evidence in this working directory yet. The reader distinguishes "not produced"
 * (404 with the command that would produce it) from a genuine failure, so the dashboard
 * can tell the user what to run instead of showing an empty panel.
 */

import type {
  ArtifactListResponse,
  BacktestResponse,
  DatasetListResponse,
  FactorResearchResponse,
  HealthResponse,
  MarketDataVerificationResponse,
  MissingArtifact,
  ModelComparisonResponse,
  PaperEvidenceResponse,
  ResearchReportResponse,
  ValidationResponse,
} from "../types/api";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export type Loaded<T> =
  | { state: "ok"; data: T }
  | { state: "missing"; detail: MissingArtifact }
  | { state: "error"; message: string };

async function read<T>(path: string): Promise<Loaded<T>> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  } catch (err) {
    return {
      state: "error",
      message:
        `Could not reach the API at ${API_BASE}. Start it with ` +
        `\`python -m uvicorn apps.api.app:app --port 8000\`. (${String(err)})`,
    };
  }

  if (response.status === 404) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: MissingArtifact }
      | null;
    if (body?.detail?.produce_with) {
      return { state: "missing", detail: body.detail };
    }
    return { state: "error", message: `Not found: ${path}` };
  }

  if (!response.ok) {
    return { state: "error", message: `${response.status} ${response.statusText}` };
  }

  return { state: "ok", data: (await response.json()) as T };
}

export const getHealth = () => read<HealthResponse>("/health");
export const getArtifacts = () => read<ArtifactListResponse>("/api/v1/artifacts");
export const getDatasets = () => read<DatasetListResponse>("/api/v1/datasets");
export const getFactorResearch = () => read<FactorResearchResponse>("/api/v1/factor-research");
export const getBacktest = () => read<BacktestResponse>("/api/v1/backtest");
export const getValidation = () => read<ValidationResponse>("/api/v1/validation");
export const getModelComparison = () =>
  read<ModelComparisonResponse>("/api/v1/models/comparison");
export const getMarketDataVerification = () =>
  read<MarketDataVerificationResponse>("/api/v1/market-data/verification");
export const getResearchReport = () => read<ResearchReportResponse>("/api/v1/research-report");
export const getPaperEvidence = () => read<PaperEvidenceResponse>("/api/v1/paper/evidence");

export function formatPercent(value: number | undefined, digits = 2): string {
  if (value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatNumber(value: number | undefined, digits = 2): string {
  if (value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function formatSigned(value: number | undefined, digits = 2): string {
  if (value === undefined || Number.isNaN(value)) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
}
