"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { indicatorLabel, RISK_STYLES } from "@/lib/labels";
import { useApi } from "@/lib/useApi";
import { Chip, ErrorBox, Loading, RiskBadge, card, num } from "./ui";

const PAGE_SIZE = 25;
const LEVELS = ["", "HIGH", "MEDIUM", "LOW"];
const TYPES = ["", "claimant", "claim", "invoice", "provider"];

const select =
  "rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900";

export function QueueTable({
  initialRisk = "",
  initialType = "",
  initialIndicator = "",
}: {
  initialRisk?: string;
  initialType?: string;
  initialIndicator?: string;
}) {
  const [risk, setRisk] = useState(LEVELS.includes(initialRisk) ? initialRisk : "");
  const [type, setType] = useState(TYPES.includes(initialType) ? initialType : "");
  const [indicator, setIndicator] = useState(initialIndicator);
  const [offset, setOffset] = useState(0);

  const summary = useApi("summary", api.summary);
  const page = useApi(`queue|${risk}|${type}|${indicator}|${offset}`, () =>
    api.riskScores({
      risk_level: risk,
      entity_type: type,
      indicator_type: indicator,
      limit: PAGE_SIZE,
      offset,
    }),
  );

  // Changing a filter always returns to the first page.
  const change = (setter: (value: string) => void) => (value: string) => {
    setter(value);
    setOffset(0);
  };

  const data = page.data;
  const from = data && data.total ? data.offset + 1 : 0;
  const to = data ? Math.min(data.offset + data.limit, data.total) : 0;
  const indicators = Object.keys(summary.data?.by_indicator_type ?? {});

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Analyst queue</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Entities ranked by risk score, highest first. Open one to see the evidence.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-md border border-slate-300 p-0.5 dark:border-slate-700" role="group" aria-label="Risk level">
          {LEVELS.map((level) => (
            <button
              key={level || "all"}
              onClick={() => change(setRisk)(level)}
              aria-pressed={risk === level}
              className={`rounded px-3 py-1 text-sm ${
                risk === level
                  ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              {level ? level.charAt(0) + level.slice(1).toLowerCase() : "All"}
            </button>
          ))}
        </div>

        <select
          aria-label="Entity type"
          className={select}
          value={type}
          onChange={(e) => change(setType)(e.target.value)}
        >
          <option value="">All types</option>
          {TYPES.slice(1).map((t) => (
            <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
          ))}
        </select>

        <select
          aria-label="Signal"
          className={select}
          value={indicator}
          onChange={(e) => change(setIndicator)(e.target.value)}
        >
          <option value="">All signals</option>
          {indicators.map((i) => (
            <option key={i} value={i}>{indicatorLabel(i)}</option>
          ))}
        </select>

        {(risk || type || indicator) && (
          <button
            className="text-sm text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200"
            onClick={() => {
              setRisk("");
              setType("");
              setIndicator("");
              setOffset(0);
            }}
          >
            Clear filters
          </button>
        )}
      </div>

      {page.error && <ErrorBox message={page.error.message} />}
      {!data && !page.error && <Loading />}

      {data && (
        <div className={`${card} overflow-hidden p-0 ${page.loading ? "opacity-60" : ""}`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-900/50">
                  <th className="px-4 py-3 font-medium">Entity ID</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Risk score</th>
                  <th className="px-4 py-3 font-medium">Level</th>
                  <th className="px-4 py-3 font-medium">Signals</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => {
                  const href = `/entities/${item.entity_type}/${encodeURIComponent(item.entity_id)}`;
                  const bar = RISK_STYLES[item.risk_level]?.bar ?? "bg-slate-400";
                  return (
                    <tr
                      key={`${item.entity_type}:${item.entity_id}`}
                      className="border-b border-slate-100 last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40"
                    >
                      <td className="px-4 py-3">
                        <Link href={href} className="font-mono font-medium text-indigo-600 hover:underline dark:text-indigo-400">
                          {item.entity_id}
                        </Link>
                      </td>
                      <td className="px-4 py-3 capitalize">{item.entity_type}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="w-9 tabular-nums">{item.risk_score}</span>
                          <div className="h-1.5 w-20 rounded-full bg-slate-100 dark:bg-slate-800">
                            <div className={`h-1.5 rounded-full ${bar}`} style={{ width: `${item.risk_score}%` }} />
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3"><RiskBadge level={item.risk_level} /></td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {item.indicator_types.map((t) => (
                            <Chip key={t}>{indicatorLabel(t)}</Chip>
                          ))}
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-slate-500">
                      No entities match these filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm dark:border-slate-800">
            <span className="text-slate-500">
              {num(from)}–{num(to)} of {num(data.total)}
            </span>
            <div className="flex gap-2">
              <button
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                className="rounded-md border border-slate-300 px-3 py-1 enabled:hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:enabled:hover:bg-slate-800"
              >
                Previous
              </button>
              <button
                disabled={offset + PAGE_SIZE >= data.total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                className="rounded-md border border-slate-300 px-3 py-1 enabled:hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:enabled:hover:bg-slate-800"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
