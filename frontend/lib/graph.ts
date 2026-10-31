// Turn an entity's evidence into nodes and links for the network view.
// Pure function: no React, no browser, easy to test.

import type { EntityDetail } from "./api";

export type NodeKind =
  | "claimant"
  | "claim"
  | "invoice"
  | "provider"
  | "payment"
  | "phone"
  | "invoice_number"
  | "more";

export interface GraphNode {
  id: string; // "<kind>:<value>", unique across kinds
  kind: NodeKind;
  value: string;
  label: string;
  isCenter: boolean;
}

export interface GraphLink {
  source: string;
  target: string;
  label: string;
}

export interface GraphModel {
  nodes: GraphNode[];
  links: GraphLink[];
  notes: string[];
}

// Colour and display name per node kind (shared by the canvas and the legend).
export const KIND_STYLE: Record<NodeKind, { color: string; name: string }> = {
  claimant: { color: "#3b82f6", name: "Claimant" },
  claim: { color: "#f59e0b", name: "Claim" },
  invoice: { color: "#10b981", name: "Invoice" },
  provider: { color: "#8b5cf6", name: "Provider" },
  payment: { color: "#94a3b8", name: "Payment" },
  phone: { color: "#14b8a6", name: "Shared phone" },
  invoice_number: { color: "#ec4899", name: "Invoice number" },
  more: { color: "#cbd5e1", name: "More" },
};

// Entities that have their own investigation page.
export const NAVIGABLE: NodeKind[] = ["claimant", "claim", "invoice", "provider"];

const MAX_PER_GROUP = 20;
// Shared-provider evidence fires on nearly every provider, so keep it small
// enough that stronger evidence stays readable.
const MAX_SHARED_PROVIDER = 8;

type Evidence = Record<string, unknown>;

const asString = (value: unknown): string | undefined =>
  typeof value === "string" || typeof value === "number" ? String(value) : undefined;

const asStrings = (value: unknown): string[] =>
  Array.isArray(value) ? value.map(asString).filter((v): v is string => !!v) : [];

const asRecords = (value: unknown): Evidence[] =>
  Array.isArray(value)
    ? value.filter((v): v is Evidence => typeof v === "object" && v !== null)
    : [];

export function buildGraph(entity: EntityDetail): GraphModel {
  const nodes = new Map<string, GraphNode>();
  const links = new Map<string, GraphLink>();
  const notes: string[] = [];

  const add = (kind: NodeKind, value: string, label?: string): GraphNode => {
    const id = `${kind}:${value}`;
    let node = nodes.get(id);
    if (!node) {
      node = { id, kind, value, label: label ?? value, isCenter: false };
      nodes.set(id, node);
    }
    return node;
  };

  const link = (a: GraphNode, b: GraphNode, label: string) => {
    if (a.id === b.id) return;
    const key = [a.id, b.id].sort().join("|") + "|" + label;
    if (!links.has(key)) links.set(key, { source: a.id, target: b.id, label });
  };

  // Add up to MAX_PER_GROUP items, then one "+N more" node.
  const addGroup = (
    hub: GraphNode,
    kind: NodeKind,
    values: string[],
    label: string,
    what: string,
    max = MAX_PER_GROUP,
  ) => {
    const unique = [...new Set(values)];
    for (const value of unique.slice(0, max)) {
      link(hub, add(kind, value), label);
    }
    const hidden = unique.length - max;
    if (hidden > 0) {
      link(hub, add("more", `${hub.id}:${kind}`, `+${hidden} more ${what}`), label);
      notes.push(`Showing ${max} of ${unique.length} ${what} for ${hub.value}.`);
    }
  };

  const center = add(entity.entity_type as NodeKind, entity.entity_id);
  center.isCenter = true;

  for (const signal of entity.signals) {
    const e: Evidence = signal.evidence ?? {};

    switch (signal.indicator_type) {
      case "SHARED_PROVIDER_CLUSTER": {
        const providerId = asString(e.provider_id);
        if (!providerId) break;
        const provider = add("provider", providerId);
        link(center, provider, "billed via");
        const others = asStrings(e.claimant_ids).filter(
          (id) => !(center.kind === "claimant" && id === center.value),
        );
        addGroup(provider, "claimant", others, "serves", "claimants", MAX_SHARED_PROVIDER);
        addGroup(provider, "invoice", asStrings(e.invoice_ids), "issued", "invoices", MAX_SHARED_PROVIDER);
        break;
      }

      case "DUPLICATE_INVOICE_ACROSS_CLAIMANTS": {
        const number = asString(e.invoice_number);
        if (!number) break;
        const hub = add("invoice_number", number, `# ${number}`);
        const detail = (e.invoice_details ?? {}) as Evidence;

        const invoiceId = asString(detail.invoice_id);
        const claimId = asString(detail.claim_id);
        const claimantId = asString(detail.claimant_id);
        const providerId = asString(detail.provider_id);

        if (invoiceId) {
          const invoice = add("invoice", invoiceId);
          link(hub, invoice, "same number");
          if (claimId) {
            const claim = add("claim", claimId);
            link(invoice, claim, "billed on");
            if (claimantId) link(claim, add("claimant", claimantId), "filed by");
          }
          if (providerId) link(add("provider", providerId), invoice, "issued");
        }

        const rest = asStrings(e.claimant_ids).filter((id) => id !== claimantId);
        addGroup(hub, "claimant", rest, "same number", "claimants");
        break;
      }

      case "MISSING_PHONE_RELATIONSHIP": {
        const phone = asString(e.shared_phone);
        if (!phone) break;
        const hub = add("phone", phone, phone);
        link(center, hub, "uses phone");
        const total = Number(e.claimant_count ?? 0);
        if (total > 1) {
          link(hub, add("more", `${hub.id}:others`, `+${total - 1} other claimants`), "uses phone");
          notes.push(
            `${total} claimants share phone ${phone}. The API only returns the count, not who they are.`,
          );
        }
        break;
      }

      case "PAYMENTS_EXCEED_APPROVED_AMOUNT":
      case "INVOICES_EXCEED_CLAIM_AMOUNT": {
        const ids = asRecords(e.invoices).map((i) => asString(i.invoice_id) ?? "");
        addGroup(center, "invoice", ids.filter(Boolean), "invoiced", "invoices");
        break;
      }

      case "PAYMENT_ON_REJECTED_INVOICE":
      case "PAID_INVOICE_UNDERPAYMENT": {
        const ids = asRecords(e.payments).map((p) => asString(p.payment_id) ?? "");
        addGroup(center, "payment", ids.filter(Boolean), "paid by", "payments");
        break;
      }
    }
  }

  return { nodes: [...nodes.values()], links: [...links.values()], notes };
}
