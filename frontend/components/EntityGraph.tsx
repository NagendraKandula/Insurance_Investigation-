"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { EntityDetail } from "@/lib/api";
import { buildGraph, KIND_STYLE, NAVIGABLE, type GraphNode } from "@/lib/graph";
import { Loading } from "./ui";

// The canvas library needs `window`, so it only loads in the browser.
const GraphCanvas = dynamic(() => import("./GraphCanvas"), {
  ssr: false,
  loading: () => <Loading label="Drawing network…" />,
});

const HEIGHT = 460;

export function EntityGraph({ entity }: { entity: EntityDetail }) {
  const router = useRouter();
  const model = useMemo(() => buildGraph(entity), [entity]);

  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const element = box.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const kinds = [...new Set(model.nodes.map((n) => n.kind))];

  const open = (node: GraphNode) => {
    if (NAVIGABLE.includes(node.kind) && !node.isCenter) {
      router.push(`/entities/${node.kind}/${encodeURIComponent(node.value)}`);
    }
  };

  if (model.nodes.length < 2) {
    return (
      <p className="text-sm text-slate-500">
        This entity has no related entities in its evidence, so there is no network to draw.
      </p>
    );
  }

  return (
    <div>
      <div
        ref={box}
        className="overflow-hidden rounded-lg border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950"
        style={{ height: HEIGHT }}
      >
        {width > 0 && (
          <GraphCanvas
            nodes={model.nodes}
            links={model.links}
            width={width}
            height={HEIGHT}
            onNodeClick={open}
          />
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-slate-600 dark:text-slate-300">
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full border-2 border-red-500 bg-slate-200" />
          This entity
        </span>
        {kinds
          .filter((k) => k !== "more")
          .map((kind) => (
            <span key={kind} className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full" style={{ background: KIND_STYLE[kind].color }} />
              {KIND_STYLE[kind].name}
            </span>
          ))}
        <span className="text-slate-400">Click a node to open it. Scroll to zoom, drag to move.</span>
      </div>

      {model.notes.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs text-slate-500">
          {model.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
