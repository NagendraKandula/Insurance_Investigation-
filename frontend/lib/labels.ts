// Human-readable names and explanations for detector signals.

export const INDICATORS: Record<string, { label: string; meaning: string }> = {
  MISSING_PHONE_RELATIONSHIP: {
    label: "Shared phone",
    meaning:
      "Claimants use the same phone number, but no relationship edge records the link.",
  },
  SHARED_PROVIDER_CLUSTER: {
    label: "Shared provider",
    meaning:
      "Several claimants bill through the same provider. Common in normal data, so weak on its own.",
  },
  DUPLICATE_INVOICE_ACROSS_CLAIMANTS: {
    label: "Duplicate invoice",
    meaning: "The same invoice number appears on claims filed by different claimants.",
  },
  PAYMENTS_EXCEED_APPROVED_AMOUNT: {
    label: "Overpaid claim",
    meaning: "Net payments on the claim are higher than the approved amount.",
  },
  INVOICES_EXCEED_CLAIM_AMOUNT: {
    label: "Invoices > claim",
    meaning: "The invoices on the claim add up to more than the amount claimed.",
  },
  PAYMENT_ON_REJECTED_INVOICE: {
    label: "Paid but rejected",
    meaning: "Money was paid against an invoice that was rejected.",
  },
  PAID_INVOICE_UNDERPAYMENT: {
    label: "Paid, not settled",
    meaning: "The invoice is marked PAID but net payments are below the invoice amount.",
  },
};

export function indicatorLabel(type: string): string {
  return INDICATORS[type]?.label ?? type.replaceAll("_", " ").toLowerCase();
}

export const RISK_STYLES = {
  HIGH: {
    badge: "bg-red-100 text-red-700 ring-red-200 dark:bg-red-950 dark:text-red-300 dark:ring-red-900",
    bar: "bg-red-500",
  },
  MEDIUM: {
    badge: "bg-amber-100 text-amber-800 ring-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:ring-amber-900",
    bar: "bg-amber-500",
  },
  LOW: {
    badge: "bg-slate-100 text-slate-600 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
    bar: "bg-slate-400",
  },
} as const;

export function humanize(key: string): string {
  const text = key.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}
