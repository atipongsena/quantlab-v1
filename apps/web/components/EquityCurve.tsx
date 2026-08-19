"use client";

/**
 * Strategy equity against its benchmark, drawn from the recorded daily series.
 *
 * The curve is downsampled for rendering only; the axis labels come from the real first
 * and last sessions so the shape cannot be mistaken for a longer or shorter run than it
 * is. Both series are indexed to 1.0 at the start, which is the only way a comparison
 * between a portfolio and a benchmark of a different size means anything.
 */

export interface CurvePoint {
  session: string;
  strategy: number;
  benchmark: number | null;
}

const WIDTH = 900;
const HEIGHT = 260;
const PAD = 8;

function path(points: CurvePoint[], pick: (p: CurvePoint) => number | null): string {
  const values = points
    .map((p, i) => ({ i, v: pick(p) }))
    .filter((p): p is { i: number; v: number } => p.v !== null && Number.isFinite(p.v));
  if (values.length < 2) return "";

  const all = points.flatMap((p) => [p.strategy, p.benchmark].filter((v): v is number => v !== null));
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min || 1;

  return values
    .map(({ i, v }, idx) => {
      const x = PAD + (i / (points.length - 1)) * (WIDTH - 2 * PAD);
      const y = HEIGHT - PAD - ((v - min) / span) * (HEIGHT - 2 * PAD);
      return `${idx === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function EquityCurve({
  points,
  benchmarkSymbol,
}: {
  points: CurvePoint[];
  benchmarkSymbol: string | null;
}) {
  if (points.length < 2) {
    return <p className="text-sm text-slate-500">Not enough sessions to draw a curve.</p>;
  }

  const last = points[points.length - 1];
  const hasBenchmark = points.some((p) => p.benchmark !== null);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs">
        <span className="flex items-center gap-2 text-slate-300">
          <span className="h-2 w-4 rounded bg-emerald-400" />
          Strategy ({((last.strategy - 1) * 100).toFixed(1)}%)
        </span>
        {hasBenchmark && last.benchmark !== null ? (
          <span className="flex items-center gap-2 text-slate-400">
            <span className="h-2 w-4 rounded bg-slate-500" />
            {benchmarkSymbol ?? "Benchmark"} ({((last.benchmark - 1) * 100).toFixed(1)}%)
          </span>
        ) : null}
        <span className="text-slate-600">growth of 1.0, log-free linear scale</span>
      </div>
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-64 w-full min-w-[600px]"
          role="img"
          aria-label="Cumulative equity curve"
        >
          {hasBenchmark ? (
            <path
              d={path(points, (p) => p.benchmark)}
              fill="none"
              stroke="#64748b"
              strokeWidth="1.5"
            />
          ) : null}
          <path d={path(points, (p) => p.strategy)} fill="none" stroke="#34d399" strokeWidth="2" />
        </svg>
      </div>
      <div className="mt-2 flex justify-between font-mono text-xs text-slate-500">
        <span>{points[0].session}</span>
        <span>{last.session}</span>
      </div>
    </div>
  );
}
