import Link from "next/link";
import type { ReactNode } from "react";
import { RISK_STYLES } from "@/lib/labels";

export const card =
  "rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900";

export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`${card} ${className}`}>
      {title && (
        <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">
          {title}
        </h2>
      )}
      {children}
    </section>
  );
}

export function Kpi({
  label,
  value,
  hint,
  href,
  accent,
}: {
  label: string;
  value: string;
  hint?: string;
  href?: string;
  accent?: string;
}) {
  const body = (
    <div
      className={`${card} h-full transition ${href ? "hover:border-slate-400 dark:hover:border-slate-600" : ""}`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className={`mt-2 text-3xl font-semibold tabular-nums ${accent ?? ""}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  );
  return href ? (
    <Link href={href} className="block">
      {body}
    </Link>
  ) : (
    body
  );
}

export function RiskBadge({ level }: { level: string }) {
  const style = RISK_STYLES[level as keyof typeof RISK_STYLES] ?? RISK_STYLES.LOW;
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${style.badge}`}
    >
      {level}
    </span>
  );
}

export function Chip({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
      {children}
    </span>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-sm text-slate-500" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
      {label}
    </div>
  );
}

export function ErrorBox({ message, hint }: { message: string; hint?: string }) {
  return (
    <div
      className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200"
      role="alert"
    >
      <p className="font-medium">{message}</p>
      {hint && <p className="mt-1 opacity-80">{hint}</p>}
    </div>
  );
}

export function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const width = max > 0 ? Math.max(2, (value / max) * 100) : 0;
  return (
    <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800">
      <div className={`h-2 rounded-full ${color}`} style={{ width: `${width}%` }} />
    </div>
  );
}

export const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
export const num = (value: number) => value.toLocaleString("en-US");
