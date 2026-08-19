/**
 * Response shapes served by apps/api. Kept in step with the FastAPI schema by
 * scripts/check_openapi_web_types.py, which fails if the API grows a path the client
 * has no typed reader for.
 */

export interface ArtifactProvenance {
  key: string;
  path: string;
  produced_by: string;
  generated_at: string;
  bytes: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  base_dir: string;
  artifacts_available: number;
  artifacts_total: number;
}

export interface ArtifactInventoryItem {
  key: string;
  description: string;
  path: string;
  produced_by: string;
  available: boolean;
  generated_at: string | null;
}

export interface ArtifactListResponse {
  artifacts: ArtifactInventoryItem[];
}

export interface DatasetItem {
  dataset_id: string;
  instruments_count: number;
  equities_count: number;
  etfs_count: number;
  sectors: string[];
}

export interface DatasetListResponse {
  datasets: DatasetItem[];
}

export interface FactorResearchResponse {
  factor_id: string;
  start_session: string;
  end_session: string;
  num_sessions: number;
  ic_mean: number;
  ic_std: number;
  rank_ic_mean: number;
  rank_ic_std: number;
  rank_ic_ir: number;
  rank_ic_tstat: number;
  rank_ic_tstat_newey_west: number;
  ic_positive_pct: number;
  breadth_mean: number;
  coverage_mean: number;
  turnover_mean: number;
  decay_profile: Record<string, number>;
  quantile_returns: Record<string, number>;
  quantile_monotonicity: number;
  spread_q5_minus_q1: number;
  long_short_ann_return: number;
  long_short_ann_vol: number;
  long_short_sharpe: number;
  subperiod_rank_ic: Record<string, number>;
  diagnostic_label: string;
  _artifact?: ArtifactProvenance;
}

export interface BenchmarkComparison {
  benchmark_symbol: string;
  sessions: number;
  strategy_total_return: number;
  benchmark_total_return: number;
  strategy_cagr: number;
  benchmark_cagr: number;
  beta: number;
  annualized_alpha: number;
  tracking_error: number;
  information_ratio: number;
  correlation: number;
}

export interface BacktestMetrics {
  total_return: number;
  cagr: number;
  annualized_volatility: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  calmar_ratio: number;
  win_rate: number;
  profit_factor: number;
  total_turnover: number;
  total_fees: number;
  total_slippage: number;
  [key: string]: number;
}

export interface BacktestResponse {
  strategy_id: string;
  dataset_id: string;
  start_session: string;
  end_session: string;
  initial_cash: string;
  ending_equity: string;
  total_orders: number;
  total_fills: number;
  metrics: BacktestMetrics;
  benchmark: BenchmarkComparison | null;
  equity: Record<string, string>;
  content_hash: string;
  _artifact?: ArtifactProvenance;
}

export interface GateDecision {
  gate_type: string;
  passed: boolean;
  reason: string | null;
}

export interface ValidationResponse {
  candidate_id: string;
  strategy_id: string;
  verdict: string;
  reasons: string[];
  hard_gates: GateDecision[];
  robustness: {
    top_k_topology: string;
    top_k_cells: Array<{
      top_k: number;
      sharpe_ratio: number;
      cagr: number;
      max_drawdown: number;
    }>;
    break_even_cost_bps: number;
    is_cost_fragile: boolean;
    herfindahl_index: number;
    is_excessively_concentrated: boolean;
    ablations: Array<{
      omitted_factor: string;
      sharpe_ratio: number;
      cagr: number;
      marginal_contribution_sharpe: number;
    }>;
    subperiod_cagr: Record<string, number>;
  };
  bootstrap: {
    metric_name: string;
    point_estimate: number;
    ci_lower: number;
    ci_upper: number;
    standard_error: number;
  };
  multiple_testing: {
    n_trials: number;
    observed_sharpe: number;
    deflated_sharpe_p_value: number;
    is_statistically_significant: boolean;
    is_multiple_testing_warned: boolean;
  };
  run?: {
    dataset_id: string;
    start_session: string;
    end_session: string;
    sessions: number;
    annual_turnover: number;
    baseline_cagr: number;
    gross_of_cost_cagr: number;
    sweeps_run: boolean;
  };
  _artifact?: ArtifactProvenance;
}

export interface ModelEvaluationReport {
  model_name: string;
  mean_ic: number;
  ic_std: number;
  ic_ir: number;
  top_bottom_spread: number;
  quintile_returns: number[];
  is_monotonic: boolean;
}

export interface ModelComparisonResponse {
  champion_model: string;
  champion_reason: string;
  reports: ModelEvaluationReport[];
  n_folds: number;
  panel?: {
    dataset_id: string;
    features: string[];
    label: string;
    monthly_cross_sections: number;
    labelled_rows: number;
    first_session: string;
    last_session: string;
    purge_periods: number;
    embargo_periods: number;
  };
  _artifact?: ArtifactProvenance;
}

export interface MarketDataVerificationResponse {
  fixture: string;
  instruments: number;
  sessions_compared: number;
  splits_replayed: number;
  dividends_replayed: number;
  median_relative_error: number;
  max_relative_error: number;
  instruments_within_tolerance: number;
  median_tolerance: number;
  worst_case_tolerance: number;
  _artifact?: ArtifactProvenance;
}

export interface ResearchReportResponse {
  [key: string]: unknown;
  _artifact?: ArtifactProvenance;
}

export interface PaperEvidenceResponse {
  [key: string]: unknown;
  _artifact?: ArtifactProvenance;
}

export interface MissingArtifact {
  error: string;
  expected_path: string;
  produce_with: string;
}
