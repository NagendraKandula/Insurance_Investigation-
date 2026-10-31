"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { indicatorLabel, RISK_STYLES } from "@/lib/labels";
import { useApi } from "@/lib/useApi";
import { Bar, Card, ErrorBox, Kpi, Loading, num, pct } from "./ui";

const LEVELS = ["HIGH", "MEDIUM", "LOW"] as const;
const LEVEL_TEXT = {
  HIGH: "text-red-600 dark:text-red-400",
  MEDIUM: "text-amber-600 dark:text-amber-400",
  LOW: "text-slate-600 dark:text-slate-300",
};

const ratio = (done: number, total: number, fallback = "n/a") =>
  total ? pct(done / total) : fallback;

export function Dashboard() {
  const summary = useApi("summary", api.summary);
  const evaluation = useApi("evaluation", api.evaluation);

  const error = summary.error ?? evaluation.error;
  if (error) {
    return (
      <ErrorBox
        message={error.message}
        hint="If the files are missing, run: python -m detection.main"
      />
    );
  }
  if (!summary.data || !evaluation.data) return <Loading label="Loading summary…" />;

  const s = summary.data;
  const e = evaluation.data;
  const total = s.total_entities;
  const maxFindings = Math.max(...Object.values(s.detector_findings), 1);
  const maxIndicator = Math.max(...Object.values(s.by_indicator_type), 1);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Executive summary</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          What the detectors found, and how well it matches the planted answer key.
        </p>
      </div>

      {/* Entities and risk levels */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Entities scored" value={num(total)} hint="claims, claimants, invoices, providers" />
        {LEVELS.map((level) => (
          <Kpi
            key={level}
            label={`${level} risk`}
            value={num(s.by_risk_level[level] ?? 0)}
            hint={`${ratio(s.by_risk_level[level] ?? 0, total)} of scored entities`}
            href={`/queue?risk=${level}`}
            accent={LEVEL_TEXT[level]}
          />
        ))}
      </div>

      <Card title="Risk distribution">
        <div className="flex h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
          {LEVELS.map((level) => (
            <div
              key={level}
              className={RISK_STYLES[level].bar}
              style={{ width: `${((s.by_risk_level[level] ?? 0) / Math.max(total, 1)) * 100}%` }}
              title={`${level}: ${s.by_risk_level[level] ?? 0}`}
            />
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
          {Object.entries(s.by_entity_type).map(([type, count]) => (
            <span key={type}>
              {num(count)} {type}s
            </span>
          ))}
        </div>
      </Card>

      {/* Accuracy metrics */}
      <div>
        <h2 className="mb-3 text-lg font-semibold">Detection accuracy</h2>

        {s.coverage.flagged_outside_labelled_set > 0 && (
          <div className="mb-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            <p className="font-medium">
              These figures only cover entities in the answer key.
            </p>
            <p className="mt-1">
              At threshold {s.coverage.threshold}, {num(s.coverage.flagged_total)} entities are
              flagged, but {num(s.coverage.flagged_outside_labelled_set)} of them are not in the
              answer key. They are never counted as false positives, so real precision is lower
              than the figure below.
            </p>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Kpi label="Precision" value={pct(e.metrics.precision)} hint="of labelled entities flagged" />
          <Kpi label="Recall" value={pct(e.metrics.recall)} hint="of planted entities found" />
          <Kpi label="F1 score" value={pct(e.metrics.f1_score)} />
          <Kpi label="Accuracy" value={pct(e.metrics.accuracy)} hint={`threshold ${e.threshold}`} />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Findings per detector">
          <ul className="space-y-3">
            {Object.entries(s.detector_findings).map(([name, count]) => (
              <li key={name}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{name.replaceAll("_", " ")}</span>
                  <span className="tabular-nums text-slate-500">{num(count)}</span>
                </div>
                <Bar value={count} max={maxFindings} color="bg-slate-500" />
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Signals on scored entities">
          <ul className="space-y-3">
            {Object.entries(s.by_indicator_type).map(([type, count]) => (
              <li key={type}>
                <div className="mb-1 flex justify-between text-sm">
                  <Link
                    href={`/queue?indicator=${type}`}
                    className="hover:underline"
                  >
                    {indicatorLabel(type)}
                  </Link>
                  <span className="tabular-nums text-slate-500">{num(count)}</span>
                </div>
                <Bar value={count} max={maxIndicator} color="bg-indigo-500" />
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Evaluation by planted pattern">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-500 dark:border-slate-800">
                <th className="py-2 pr-4 font-medium">Pattern</th>
                {["TP", "FP", "FN", "TN"].map((h) => (
                  <th key={h} className="px-3 py-2 text-right font-medium">{h}</th>
                ))}
                <th className="px-3 py-2 text-right font-medium">Precision</th>
                <th className="px-3 py-2 text-right font-medium">Recall</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(e.pattern_metrics).map(([pattern, m]) => (
                <tr key={pattern} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                  <td className="py-2 pr-4 font-medium">{pattern.replaceAll("_", " ")}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{m.TP}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{m.FP}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{m.FN}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{m.TN}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{ratio(m.TP, m.TP + m.FP)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{ratio(m.TP, m.TP + m.FN)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          TP/FP/FN/TN = true positives, false positives, false negatives, true negatives. n/a
          means the pattern has no entities of that kind.
        </p>
      </Card>
    </div>
  );
}
