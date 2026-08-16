/**
 * TypeScript contract definitions synchronized with QuantLab OpenAPI 3.1 schema.
 */

export interface HealthResponse {
  status: string;
  version: string;
}

export interface DatasetItem {
  dataset_id: string;
  instruments_count: number;
}

export interface DatasetListResponse {
  datasets: DatasetItem[];
}

export interface FactorResearchRequest {
  factor_name: string;
  dataset_id?: string;
}

export interface FactorResearchResponse {
  factor_name: string;
  mean_ic: number;
  ic_ir: number;
  annualized_return: number;
  sharpe_ratio: number;
}

export interface BacktestRequest {
  strategy_config?: string;
  dataset_id?: string;
}

export interface BacktestResponse {
  annualized_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
}

export interface ValidationResponse {
  verdict: string;
  lookahead_leakage_clean?: boolean;
  data_integrity_passed?: boolean;
  reproducibility_verified?: boolean;
}

export interface ModelComparisonReport {
  model_name: string;
  mean_ic: number;
  ic_ir: number;
  top_bottom_spread: number;
  is_monotonic: boolean;
}

export interface ModelComparisonResponse {
  champion_model: string;
  champion_reason?: string;
  reports: ModelComparisonReport[];
}

export interface PaperRunResponse {
  session: string;
  orders_count: number;
  fills_count: number;
  total_equity: string;
}

export interface ReconciliationBreak {
  break_type: string;
  instrument_id?: string | null;
  difference: string;
  severity: string;
  reason: string;
}

export interface ReconciliationResponse {
  is_clean: boolean;
  max_severity: string;
  breaks: ReconciliationBreak[];
}

export interface CampaignResponse {
  report_id: string;
  campaign_id: string;
  verdicts: Record<string, string>;
}
