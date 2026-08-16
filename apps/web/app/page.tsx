"use client";

import React, { useState } from "react";
import {
  Activity,
  AlertTriangle,
  Award,
  Bot,
  Brain,
  CheckCircle2,
  DollarSign,
  Layers,
  LineChart,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from "lucide-react";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "factors" | "ml" | "validation" | "paper" | "campaigns"
  >("overview");

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900/50 flex flex-col justify-between p-4">
        <div>
          <div className="flex items-center gap-2 mb-8 px-2">
            <div className="h-8 w-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 font-bold">
              QL
            </div>
            <div>
              <h1 className="font-bold text-base leading-none">QuantLab V1</h1>
              <span className="text-xs text-slate-400">Institutional Quant OS</span>
            </div>
          </div>

          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab("overview")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "overview"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <Activity className="h-4 w-4" />
              Overview
            </button>
            <button
              onClick={() => setActiveTab("factors")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "factors"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <Layers className="h-4 w-4" />
              Factor Research
            </button>
            <button
              onClick={() => setActiveTab("ml")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "ml"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <Brain className="h-4 w-4" />
              Walk-Forward ML
            </button>
            <button
              onClick={() => setActiveTab("validation")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "validation"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <ShieldAlert className="h-4 w-4" />
              Validation & Defense
            </button>
            <button
              onClick={() => setActiveTab("paper")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "paper"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <DollarSign className="h-4 w-4" />
              Paper Operations
            </button>
            <button
              onClick={() => setActiveTab("campaigns")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "campaigns"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <Bot className="h-4 w-4" />
              AI Agent Research
            </button>
          </nav>
        </div>

        <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 text-xs text-slate-400">
          <div className="flex items-center gap-2 mb-1">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="font-semibold text-slate-300">System Ready</span>
          </div>
          <div>Point-in-Time DuckDB active</div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        {/* Header */}
        <header className="h-16 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/30 backdrop-blur">
          <div className="flex items-center gap-4">
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-500">
              Active Strategy
            </span>
            <span className="text-sm font-semibold bg-slate-800 px-2.5 py-1 rounded-md text-emerald-400 border border-slate-700">
              composite-top30-v1
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>Dataset: <strong className="text-slate-200">DATASET-v001</strong></span>
            <span>•</span>
            <span>Clock: <strong className="text-slate-200">2026-01-05 (PIT)</strong></span>
          </div>
        </header>

        {/* Dynamic Tab Body */}
        <div className="p-6 space-y-6 max-w-7xl">
          {/* Top Metrics Cards */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
              <span className="text-xs text-slate-400 font-medium">Sharpe Ratio</span>
              <div className="text-2xl font-bold text-slate-100 mt-1 flex items-center gap-2">
                1.42
                <span className="text-xs font-normal text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  +18.2% Ann.
                </span>
              </div>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
              <span className="text-xs text-slate-400 font-medium">Mean Rank IC</span>
              <div className="text-2xl font-bold text-slate-100 mt-1 flex items-center gap-2">
                0.058
                <span className="text-xs font-normal text-slate-400">IR 2.14</span>
              </div>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
              <span className="text-xs text-slate-400 font-medium">Deflated Sharpe (DSR)</span>
              <div className="text-2xl font-bold text-emerald-400 mt-1 flex items-center gap-2">
                0.91
                <span className="text-xs font-normal text-slate-400">Passes &gt;0.80</span>
              </div>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
              <span className="text-xs text-slate-400 font-medium">Max Drawdown</span>
              <div className="text-2xl font-bold text-slate-100 mt-1">
                8.2%
              </div>
            </div>
          </div>

          {/* Tab 1: Overview */}
          {activeTab === "overview" && (
            <div className="grid grid-cols-3 gap-6">
              <div className="col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                <h3 className="font-semibold text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-400" />
                  Strategy Cumulative Equity Performance
                </h3>
                <div className="h-64 bg-slate-950/80 rounded-lg border border-slate-800/80 p-4 flex flex-col justify-end">
                  {/* Mock Sparkline/Equity visualization */}
                  <div className="h-full flex items-end gap-1.5 pt-8">
                    {[10, 15, 12, 22, 25, 20, 32, 40, 38, 48, 55, 52, 60, 68, 75, 72, 85, 94, 92, 100].map(
                      (h, i) => (
                        <div
                          key={i}
                          style={{ height: `${h}%` }}
                          className="flex-1 bg-gradient-to-t from-emerald-600/30 to-emerald-400 rounded-t-sm"
                        />
                      )
                    )}
                  </div>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                <h3 className="font-semibold text-base">Key Alpha Attributes</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-400">Rebalance Frequency</span>
                    <span className="font-medium text-slate-200">Monthly</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-400">Universe Size</span>
                    <span className="font-medium text-slate-200">Top 30 Equal Weight</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-400">Execution Friction</span>
                    <span className="font-medium text-slate-200">5 bps slippage + $1 fee</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-800">
                    <span className="text-slate-400">Break-Even Cost</span>
                    <span className="font-medium text-emerald-400">42 bps</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: Walk-Forward ML */}
          {activeTab === "ml" && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-base flex items-center gap-2">
                  <Brain className="h-4 w-4 text-emerald-400" />
                  Purged Walk-Forward Model Comparison (5 Folds)
                </h3>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Award className="h-3.5 w-3.5" />
                  Champion: RIDGE RANKER
                </span>
              </div>
              <table className="w-full text-sm text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 text-xs uppercase">
                    <th className="py-2.5 px-3">Model Paradigm</th>
                    <th className="py-2.5 px-3">Mean Out-of-Sample Rank IC</th>
                    <th className="py-2.5 px-3">IC Information Ratio (IR)</th>
                    <th className="py-2.5 px-3">Q5 - Q1 Spread</th>
                    <th className="py-2.5 px-3">Monotonicity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  <tr className="hover:bg-slate-800/30">
                    <td className="py-3 px-3 font-semibold text-slate-200">1. Heuristic Composite (Baseline)</td>
                    <td className="py-3 px-3 text-slate-300">0.0521</td>
                    <td className="py-3 px-3 text-slate-300">1.85</td>
                    <td className="py-3 px-3 text-slate-300">+4.00%</td>
                    <td className="py-3 px-3 text-emerald-400">Strict Monotonic</td>
                  </tr>
                  <tr className="bg-emerald-950/20 hover:bg-emerald-950/30">
                    <td className="py-3 px-3 font-semibold text-emerald-400 flex items-center gap-1.5">
                      2. Ridge Linear Ranker
                      <span className="text-[10px] bg-emerald-500/20 px-1 rounded">CHAMPION</span>
                    </td>
                    <td className="py-3 px-3 font-bold text-emerald-400">0.0614</td>
                    <td className="py-3 px-3 text-emerald-400 font-bold">2.45</td>
                    <td className="py-3 px-3 text-emerald-400">+4.00%</td>
                    <td className="py-3 px-3 text-emerald-400">Strict Monotonic</td>
                  </tr>
                  <tr className="hover:bg-slate-800/30">
                    <td className="py-3 px-3 font-semibold text-slate-200">3. LightGBM Boosted Tree</td>
                    <td className="py-3 px-3 text-slate-300">0.0582</td>
                    <td className="py-3 px-3 text-slate-300">2.01</td>
                    <td className="py-3 px-3 text-slate-300">+4.00%</td>
                    <td className="py-3 px-3 text-emerald-400">Strict Monotonic</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Tab 3: Validation */}
          {activeTab === "validation" && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="font-semibold text-base flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                Hard Correctness &amp; Anti-Overfitting Defense Gates
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-950/60 rounded-lg border border-slate-800">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm">Lookahead Leakage Gate</span>
                    <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                      PASS (0 Leaks)
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Verified strictly causal point-in-time boundary. Features at date t use only data known at or before t.
                  </p>
                </div>
                <div className="p-4 bg-slate-950/60 rounded-lg border border-slate-800">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm">Sensitivity Surface Topology</span>
                    <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                      PLATEAU (Robust)
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Broad parameter plateau detected across lookback window sweep [6M..12M]. No isolated overfit spikes.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Tab 4: AI Campaigns */}
          {activeTab === "campaigns" && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="font-semibold text-base flex items-center gap-2">
                <Bot className="h-4 w-4 text-emerald-400" />
                Autonomous Research Campaign: Quality Filtering on Momentum
              </h3>
              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-sky-400 font-bold">[IDEA_GENERATOR]</span>: High ROE Quality stocks filter out low-quality momentum traps, yielding superior Information Ratio.
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-amber-400 font-bold">[FACTOR_ENGINEER]</span>: Formulated composite: 0.60 * momentum_12_1 + 0.40 * quality_roe. OOS Sharpe = 1.45.
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-rose-400 font-bold">[VALIDATION_CRITIC]</span>: 4-vector falsification passed. DSR = 0.91 &gt; 0.80 threshold. No fragility.
                </div>
                <div className="p-3 bg-emerald-950/30 rounded-lg border border-emerald-500/30 text-emerald-300">
                  <span className="text-emerald-400 font-bold">[LEAD_STRATEGIST]</span>: Authoritative Verdict: VALIDATED. Promoted to PAPER_CANDIDATE.
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
