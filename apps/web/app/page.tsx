"use client";

import { useEffect, useMemo, useState } from "react";

import { EquityCurve, type CurvePoint } from "../components/EquityCurve";
import { Card, Panel, Provenance, Stat } from "../components/primitives";
import {
  API_BASE,
  formatNumber,
  formatPercent,
  formatSigned,
  getBacktest,
  getDatasets,
  getFactorResearch,
  getHealth,
  getMarketDataVerification,
  getModelComparison,
  getValidation,
  type Loaded,
} from "../lib/api";
import type {
  BacktestResponse,
  DatasetListResponse,
  FactorResearchResponse,
  HealthResponse,
  MarketDataVerificationResponse,
  ModelComparisonResponse,
  ValidationResponse,
} from "../types/api";

type TabKey = "performance" | "factors" | "models" | "validation" | "data";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "performance", label: "Performance" },
  { key: "factors", label: "Factor research" },
  { key: "models", label: "Walk-forward ML" },
  { key: "validation", label: "Falsification" },
  { key: "data", label: "Data integrity" },
];

function useLoaded<T>(loader: () => Promise<Loaded<T>>): Loaded<T> | null {
  const [value, setValue] = useState<Loaded<T> | null>(null);
  useEffect(() => {
    let live = true;
    loader().then((result) => {
      if (live) setValue(result);
    });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return value;
}

/** Rebuild growth-of-1.0 series from the recorded equity path. */
function toCurve(backtest: BacktestResponse): CurvePoint[] {
  const sessions = Object.keys(backtest.equity).sort();
  if (sessions.length === 0) return [];

  const first = Number(backtest.equity[sessions[0]]);
  if (!Number.isFinite(first) || first === 0) return [];

  // The benchmark path is not stored session by session, only as summary statistics, so
  // it is drawn as the constant-growth path that reaches its recorded total return. It
  // is a reference level, not a claim about the benchmark's actual drawdowns.
  const benchmarkTotal = backtest.benchmark?.benchmark_total_return ?? null;

  const step = Math.max(1, Math.floor(sessions.length / 600));
  const points: CurvePoint[] = [];
  for (let i = 0; i < sessions.length; i += step) {
    const session = sessions[i];
    const strategy = Number(backtest.equity[session]) / first;
    const progress = i / (sessions.length - 1);
    points.push({
      session,
      strategy,
      benchmark:
        benchmarkTotal === null ? null : Math.pow(1 + benchmarkTotal, progress),
    });
  }
  const lastSession = sessions[sessions.length - 1];
  points.push({
    session: lastSession,
    strategy: Number(backtest.equity[lastSession]) / first,
    benchmark: benchmarkTotal === null ? null : 1 + benchmarkTotal,
  });
  return points;
}

const TAB_KEYS = new Set<string>(TABS.map((entry) => entry.key));

function tabFromHash(): TabKey {
  if (typeof window === "undefined") return "performance";
  const hash = window.location.hash.replace("#", "");
  return TAB_KEYS.has(hash) ? (hash as TabKey) : "performance";
}

export default function DashboardPage() {
  // The tab lives in the URL hash so a specific view can be linked, bookmarked, or
  // opened directly by a screenshot run.
  const [tab, setTabState] = useState<TabKey>("performance");

  useEffect(() => {
    setTabState(tabFromHash());
    const onHashChange = () => setTabState(tabFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const setTab = (key: TabKey) => {
    setTabState(key);
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `#${key}`);
    }
  };

  const health = useLoaded<HealthResponse>(getHealth);
  const datasets = useLoaded<DatasetListResponse>(getDatasets);
  const backtest = useLoaded<BacktestResponse>(getBacktest);
  const factors = useLoaded<FactorResearchResponse>(getFactorResearch);
  const models = useLoaded<ModelComparisonResponse>(getModelComparison);
  const validation = useLoaded<ValidationResponse>(getValidation);
  const verification = useLoaded<MarketDataVerificationResponse>(getMarketDataVerification);

  const curve = useMemo(
    () => (backtest?.state === "ok" ? toCurve(backtest.data) : []),
    [backtest],
  );

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">QuantLab</h1>
          <p className="mt-1 text-sm text-slate-400">
            Point-in-time research, event-driven backtesting, and falsification gates.
          </p>
        </div>
        <div className="text-right text-xs text-slate-500">
          <div>
            API <code className="text-slate-400">{API_BASE}</code>
          </div>
          {health?.state === "ok" ? (
            <div className="mt-1 text-slate-400">
              {health.data.artifacts_available} of {health.data.artifacts_total} artifacts on disk
            </div>
          ) : null}
        </div>
      </header>

      <nav className="mb-6 flex flex-wrap gap-2">
        {TABS.map((entry) => (
          <button
            key={entry.key}
            type="button"
            onClick={() => setTab(entry.key)}
            className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
              tab === entry.key
                ? "bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/30"
                : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
            }`}
          >
            {entry.label}
          </button>
        ))}
      </nav>

      {tab === "performance" ? (
        <div className="space-y-6">
          <Panel result={backtest}>
            {(data) => (
              <>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <Stat
                    label="CAGR"
                    value={formatPercent(data.metrics.cagr)}
                    hint={`${data.start_session} to ${data.end_session}`}
                    tone={data.metrics.cagr > 0 ? "good" : "bad"}
                  />
                  <Stat
                    label="Sharpe"
                    value={formatSigned(data.metrics.sharpe_ratio)}
                    hint={`vol ${formatPercent(data.metrics.annualized_volatility)}`}
                  />
                  <Stat
                    label="Max drawdown"
                    value={formatPercent(-Math.abs(data.metrics.max_drawdown))}
                    tone="bad"
                  />
                  <Stat
                    label="Turnover"
                    value={formatPercent(data.metrics.total_turnover, 0)}
                    hint={`${data.total_fills} fills`}
                  />
                </div>

                {data.benchmark ? (
                  <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
                    <Stat
                      label={`${data.benchmark.benchmark_symbol} CAGR`}
                      value={formatPercent(data.benchmark.benchmark_cagr)}
                      hint="buy and hold, total return"
                    />
                    <Stat label="Beta" value={formatNumber(data.benchmark.beta)} />
                    <Stat
                      label="Jensen alpha"
                      value={formatPercent(data.benchmark.annualized_alpha)}
                      tone={data.benchmark.annualized_alpha > 0 ? "good" : "bad"}
                    />
                    <Stat
                      label="Information ratio"
                      value={formatSigned(data.benchmark.information_ratio)}
                      hint={`TE ${formatPercent(data.benchmark.tracking_error)}`}
                    />
                  </div>
                ) : null}

                <div className="mt-6">
                  <Card
                    title="Cumulative equity"
                    subtitle={`${data.strategy_id} on ${data.dataset_id}`}
                  >
                    <EquityCurve
                      points={curve}
                      benchmarkSymbol={data.benchmark?.benchmark_symbol ?? null}
                    />
                    <Provenance artifact={data._artifact} />
                  </Card>
                </div>
              </>
            )}
          </Panel>
        </div>
      ) : null}

      {tab === "factors" ? (
        <Card title="Single-factor research" subtitle="Monthly cross-sections, next-open entry">
          <Panel result={factors}>
            {(data) => (
              <>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <Stat label="Factor" value={data.factor_id} />
                  <Stat
                    label="Rank IC"
                    value={formatSigned(data.rank_ic_mean, 4)}
                    hint={`${data.num_sessions} rebalances`}
                  />
                  <Stat
                    label="t-stat (Newey-West)"
                    value={formatSigned(data.rank_ic_tstat_newey_west)}
                    tone={Math.abs(data.rank_ic_tstat_newey_west) >= 2 ? "good" : "neutral"}
                    hint={Math.abs(data.rank_ic_tstat_newey_west) >= 2 ? "significant" : "not significant"}
                  />
                  <Stat
                    label="Breadth"
                    value={formatNumber(data.breadth_mean, 1)}
                    hint="names per cross-section"
                  />
                </div>

                <div className="mt-6 grid gap-6 md:grid-cols-2">
                  <div>
                    <h4 className="mb-2 text-xs uppercase tracking-wide text-slate-400">
                      Quantile portfolios (annualized, gross)
                    </h4>
                    <table className="w-full text-sm">
                      <tbody className="divide-y divide-slate-800">
                        {Object.entries(data.quantile_returns)
                          .sort()
                          .map(([bucket, value]) => (
                            <tr key={bucket}>
                              <td className="py-1.5 text-slate-400">{bucket}</td>
                              <td className="py-1.5 text-right font-mono text-slate-200">
                                {formatPercent(value)}
                              </td>
                            </tr>
                          ))}
                        <tr>
                          <td className="py-1.5 text-slate-400">Monotonicity</td>
                          <td className="py-1.5 text-right font-mono text-slate-200">
                            {formatSigned(data.quantile_monotonicity)}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div>
                    <h4 className="mb-2 text-xs uppercase tracking-wide text-slate-400">
                      Rank IC by forward horizon
                    </h4>
                    <table className="w-full text-sm">
                      <tbody className="divide-y divide-slate-800">
                        {Object.entries(data.decay_profile).map(([horizon, value]) => (
                          <tr key={horizon}>
                            <td className="py-1.5 text-slate-400">{horizon}</td>
                            <td className="py-1.5 text-right font-mono text-slate-200">
                              {formatSigned(value, 4)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <p className="mt-4 text-xs text-slate-500">
                  Status: <code className="text-slate-400">{data.diagnostic_label}</code>
                </p>
                <Provenance artifact={data._artifact} />
              </>
            )}
          </Panel>
        </Card>
      ) : null}

      {tab === "models" ? (
        <Card
          title="Purged walk-forward comparison"
          subtitle="Baseline keeps the slot unless a model clears it by more than the noise"
        >
          <Panel result={models}>
            {(data) => (
              <>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs uppercase text-slate-500">
                      <th className="py-2 text-left">Model</th>
                      <th className="py-2 text-right">OOS rank IC</th>
                      <th className="py-2 text-right">IC IR</th>
                      <th className="py-2 text-right">Q5 − Q1</th>
                      <th className="py-2 text-right">Monotonic</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {data.reports.map((report) => (
                      <tr
                        key={report.model_name}
                        className={
                          report.model_name === data.champion_model ? "bg-emerald-950/20" : ""
                        }
                      >
                        <td className="py-2 font-mono text-slate-200">{report.model_name}</td>
                        <td className="py-2 text-right font-mono">
                          {formatSigned(report.mean_ic, 4)}
                        </td>
                        <td className="py-2 text-right font-mono">
                          {formatSigned(report.ic_ir)}
                        </td>
                        <td className="py-2 text-right font-mono">
                          {formatSigned(report.top_bottom_spread, 4)}
                        </td>
                        <td className="py-2 text-right text-slate-400">
                          {report.is_monotonic ? "yes" : "no"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <p className="mt-4 text-sm text-slate-300">
                  Champion: <span className="font-mono text-emerald-300">{data.champion_model}</span>
                </p>
                <p className="mt-1 text-xs text-slate-500">{data.champion_reason}</p>
                {data.panel ? (
                  <p className="mt-3 text-xs text-slate-500">
                    {data.panel.monthly_cross_sections} monthly cross-sections,{" "}
                    {data.panel.labelled_rows.toLocaleString()} labelled rows,{" "}
                    {data.n_folds} folds, purge {data.panel.purge_periods} / embargo{" "}
                    {data.panel.embargo_periods} periods. Label: {data.panel.label}.
                  </p>
                ) : null}
                <Provenance artifact={data._artifact} />
              </>
            )}
          </Panel>
        </Card>
      ) : null}

      {tab === "validation" ? (
        <Card title="Falsification report" subtitle="Hard gates, robustness sweeps, and verdict">
          <Panel result={validation}>
            {(data) => {
              const failed = data.hard_gates.filter((gate) => !gate.passed);
              return (
                <>
                  <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    <Stat
                      label="Verdict"
                      value={data.verdict}
                      tone={failed.length === 0 ? "good" : "bad"}
                    />
                    <Stat
                      label="Deflated Sharpe p"
                      value={formatNumber(data.multiple_testing.deflated_sharpe_p_value, 4)}
                      hint={`${data.multiple_testing.n_trials} recorded trials`}
                      tone={data.multiple_testing.is_statistically_significant ? "good" : "bad"}
                    />
                    <Stat
                      label="Sharpe 95% CI"
                      value={`${formatNumber(data.bootstrap.ci_lower)} … ${formatNumber(
                        data.bootstrap.ci_upper,
                      )}`}
                      hint="stationary block bootstrap"
                      tone={data.bootstrap.ci_lower > 0 ? "good" : "bad"}
                    />
                    <Stat
                      label="Break-even cost"
                      value={`${formatNumber(data.robustness.break_even_cost_bps, 0)} bps`}
                      tone={data.robustness.is_cost_fragile ? "bad" : "good"}
                    />
                  </div>

                  <div className="mt-6 grid gap-6 md:grid-cols-2">
                    <div>
                      <h4 className="mb-2 text-xs uppercase tracking-wide text-slate-400">
                        Hard gates
                      </h4>
                      <ul className="space-y-1 text-sm">
                        {data.hard_gates.map((gate) => (
                          <li key={gate.gate_type} className="flex justify-between gap-4">
                            <span className="text-slate-400">{gate.gate_type}</span>
                            <span className={gate.passed ? "text-emerald-400" : "text-rose-400"}>
                              {gate.passed ? "pass" : gate.reason ?? "fail"}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="mb-2 text-xs uppercase tracking-wide text-slate-400">
                        Portfolio size sweep ({data.robustness.top_k_topology})
                      </h4>
                      <table className="w-full text-sm">
                        <tbody className="divide-y divide-slate-800">
                          {data.robustness.top_k_cells.map((cell) => (
                            <tr key={cell.top_k}>
                              <td className="py-1.5 text-slate-400">top {cell.top_k}</td>
                              <td className="py-1.5 text-right font-mono text-slate-200">
                                Sharpe {formatSigned(cell.sharpe_ratio)}
                              </td>
                              <td className="py-1.5 text-right font-mono text-slate-400">
                                {formatPercent(cell.cagr)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {data.robustness.ablations.length > 0 ? (
                    <div className="mt-6">
                      <h4 className="mb-2 text-xs uppercase tracking-wide text-slate-400">
                        Factor ablations
                      </h4>
                      <table className="w-full text-sm">
                        <tbody className="divide-y divide-slate-800">
                          {data.robustness.ablations.map((record) => (
                            <tr key={record.omitted_factor}>
                              <td className="py-1.5 text-slate-400">
                                without {record.omitted_factor}
                              </td>
                              <td className="py-1.5 text-right font-mono text-slate-200">
                                Sharpe {formatSigned(record.sharpe_ratio)}
                              </td>
                              <td className="py-1.5 text-right font-mono text-slate-400">
                                contribution {formatSigned(record.marginal_contribution_sharpe)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}

                  <ul className="mt-4 space-y-1 text-xs text-slate-500">
                    {data.reasons.map((reason) => (
                      <li key={reason}>• {reason}</li>
                    ))}
                  </ul>
                  <Provenance artifact={data._artifact} />
                </>
              );
            }}
          </Panel>
        </Card>
      ) : null}

      {tab === "data" ? (
        <div className="space-y-6">
          <Card
            title="Corporate action verification"
            subtitle="Engine adjustment replayed against the provider's own total-return series"
          >
            <Panel result={verification}>
              {(data) => (
                <>
                  <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    <Stat
                      label="Instruments in tolerance"
                      value={`${data.instruments_within_tolerance} / ${data.instruments}`}
                      tone={
                        data.instruments_within_tolerance === data.instruments ? "good" : "bad"
                      }
                    />
                    <Stat
                      label="Sessions compared"
                      value={data.sessions_compared.toLocaleString()}
                    />
                    <Stat
                      label="Actions replayed"
                      value={`${data.splits_replayed} / ${data.dividends_replayed.toLocaleString()}`}
                      hint="splits / dividends"
                    />
                    <Stat
                      label="Median error"
                      value={formatPercent(data.median_relative_error, 4)}
                      hint={`worst ${formatPercent(data.max_relative_error, 4)}`}
                    />
                  </div>
                  <Provenance artifact={data._artifact} />
                </>
              )}
            </Panel>
          </Card>

          <Card title="Built datasets" subtitle="Present in this working directory">
            <Panel result={datasets}>
              {(data) =>
                data.datasets.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No datasets built yet. Run{" "}
                    <code className="text-slate-400">quantlab dataset build</code>.
                  </p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-800 text-xs uppercase text-slate-500">
                        <th className="py-2 text-left">Dataset</th>
                        <th className="py-2 text-right">Equities</th>
                        <th className="py-2 text-right">ETFs</th>
                        <th className="py-2 text-right">Sectors</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {data.datasets.map((item) => (
                        <tr key={item.dataset_id}>
                          <td className="py-2 font-mono text-slate-200">{item.dataset_id}</td>
                          <td className="py-2 text-right font-mono">{item.equities_count}</td>
                          <td className="py-2 text-right font-mono">{item.etfs_count}</td>
                          <td className="py-2 text-right font-mono">{item.sectors.length}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )
              }
            </Panel>
          </Card>
        </div>
      ) : null}
    </main>
  );
}
