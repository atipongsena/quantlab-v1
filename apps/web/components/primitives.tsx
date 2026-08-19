"use client";

import type { ReactNode } from "react";
import type { Loaded } from "../lib/api";
import type { ArtifactProvenance } from "../types/api";

export function Card({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
      <header className="mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">{title}</h3>
        {subtitle ? <p className="mt-1 text-xs text-slate-500">{subtitle}</p> : null}
      </header>
      {children}
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "good" | "bad";
}) {
  const toneClass =
    tone === "good" ? "text-emerald-400" : tone === "bad" ? "text-rose-400" : "text-slate-100";
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`mt-1 font-mono text-xl ${toneClass}`}>{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
}

export function Provenance({ artifact }: { artifact?: ArtifactProvenance }) {
  if (!artifact) return null;
  return (
    <p className="mt-4 border-t border-slate-800 pt-3 text-xs text-slate-500">
      From <code className="text-slate-400">{artifact.path}</code>, generated{" "}
      {new Date(artifact.generated_at).toLocaleString()} by{" "}
      <code className="text-slate-400">{artifact.produced_by}</code>
    </p>
  );
}

/**
 * Renders a panel only when its evidence exists.
 *
 * "Not produced yet" is shown as the command that would produce it rather than as an
 * empty chart, because a dashboard that renders zeros for missing data is how a broken
 * pipeline goes unnoticed.
 */
export function Panel<T>({
  result,
  children,
}: {
  result: Loaded<T> | null;
  children: (data: T) => ReactNode;
}) {
  if (result === null) {
    return <p className="text-sm text-slate-500">Loading…</p>;
  }
  if (result.state === "missing") {
    return (
      <div className="rounded-lg border border-amber-900/60 bg-amber-950/20 p-4">
        <p className="text-sm text-amber-200">Not produced yet in this working directory.</p>
        <p className="mt-2 text-xs text-slate-400">Run:</p>
        <pre className="mt-1 overflow-x-auto rounded bg-slate-950 p-3 text-xs text-slate-300">
          {result.detail.produce_with}
        </pre>
      </div>
    );
  }
  if (result.state === "error") {
    return (
      <div className="rounded-lg border border-rose-900/60 bg-rose-950/20 p-4 text-sm text-rose-200">
        {result.message}
      </div>
    );
  }
  return <>{children(result.data)}</>;
}
