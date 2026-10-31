"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { api, ApiError, type Signal } from "@/lib/api";
import { humanize, INDICATORS, indicatorLabel, RISK_STYLES } from "@/lib/labels";
import { useApi } from "@/lib/useApi";
import { EntityGraph } from "./EntityGraph";
import { Card, Chip, ErrorBox, Loading, RiskBadge } from "./ui";

const MAX_CHIPS = 12;

function Value({ value }: { value: unknown }): ReactNode {
  if (Array.isArray(value)) {
    if (value.every((v) => typeof v !== "object" || v === null)) {
      const shown = value.slice(0, MAX_CHIPS);
      return (
        <span className="flex flex-wrap gap-1">
          {shown.map((v, i) => (
            <Chip key={i}>{String(v)}</Chip>
          ))}
          {value.length > MAX_CHIPS && <span className="text-xs text-slate-500">+{value.length - MAX_CHIPS} more</span>}
        </span>
      );
    }
    return <span className="text-slate-500">{value.length} items (see raw data)</span>;
  }
  if (typeof value === "number") return <span className="tabular-nums">{value.toLocaleString("en-US")}</span>;
  if (typeof value === "object" && value !== null) return <span className="text-slate-500">(see raw data)</span>;
  return <span>{String(value)}</span>;
}

function SignalCard({ signal }: { signal: Signal }) {
  const info = INDICATORS[signal.indicator_type];
  return (
    <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-800">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-medium">{indicatorLabel(signal.indicator_type)}</h3>
          {info && <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{info.meaning}</p>}
        </div>
        <span className="shrink-0 rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold tabular-nums dark:bg-slate-800">
          +{signal.weight} pts
        </span>
      </div>

      <dl className="mt-3 grid gap-x-4 gap-y-1.5 text-sm sm:grid-cols-[max-content_1fr]">
        {Object.entries(signal.evidence).map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-slate-500">{humanize(key)}</dt>
            <dd className="min-w-0"><Value value={value} /></dd>
          </div>
        ))}
      </dl>

      <details className="mt-3 text-xs">
        <summary className="cursor-pointer text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
          Raw evidence
        </summary>
        <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-slate-100 p-3 dark:bg-slate-950">
          {JSON.stringify(signal.evidence, null, 2)}
        </pre>
      </details>
    </div>
  );
}

export function EntityView({ type, id }: { type: string; id: string }) {
  const { data, error } = useApi(`entity|${type}|${id}`, () => api.entity(type, id));

  const back = (
    <Link href="/queue" className="text-sm text-slate-500 hover:underline">
      ← Back to queue
    </Link>
  );

  if (error) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <div className="space-y-4">
        {back}
        <ErrorBox
          message={notFound ? `No risk score for ${type} ${id}` : error.message}
          hint={notFound ? "No detector flagged this entity, so it has no score or evidence." : undefined}
        />
      </div>
    );
  }
  if (!data) return <Loading />;

  const bar = RISK_STYLES[data.risk_level]?.bar ?? "bg-slate-400";

  return (
    <div className="space-y-6">
      {back}

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{data.entity_type}</p>
          <h1 className="font-mono text-2xl font-semibold tracking-tight">{data.entity_id}</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-40">
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-xs text-slate-500">Risk score</span>
              <span className="text-2xl font-semibold tabular-nums">{data.risk_score}</span>
            </div>
            <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-800">
              <div className={`h-2 rounded-full ${bar}`} style={{ width: `${data.risk_score}%` }} />
            </div>
          </div>
          <RiskBadge level={data.risk_level} />
        </div>
      </div>

      <Card title="Network">
        <EntityGraph entity={data} />
      </Card>

      <Card title={`Why it was flagged (${data.signal_count} signal${data.signal_count === 1 ? "" : "s"})`}>
        <div className="space-y-3">
          {data.signals.map((signal) => (
            <SignalCard key={signal.indicator_type} signal={signal} />
          ))}
        </div>
      </Card>
    </div>
  );
}
