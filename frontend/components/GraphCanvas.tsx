"use client";

// Canvas renderer. Loaded only in the browser (see EntityGraph) because the
// graph library needs `window`.

import { useEffect, useMemo, useRef } from "react";
import ForceGraph2D, { type ForceGraphMethods } from "react-force-graph-2d";
import { KIND_STYLE, type GraphLink, type GraphNode, type NodeKind } from "@/lib/graph";


interface Props {
  nodes: GraphNode[];
  links: GraphLink[];
  width: number;
  height: number;
  onNodeClick: (node: GraphNode) => void;
}

export default function GraphCanvas({ nodes, links, width, height, onNodeClick }: Props) {
  const ref = useRef<ForceGraphMethods | undefined>(undefined);

  // The library mutates what it is given, so hand it copies.
  const data = useMemo(
    () => ({
      nodes: nodes.map((n) => ({ ...n })),
      links: links.map((l) => ({ ...l })),
    }),
    [nodes, links],
  );

  useEffect(() => {
    ref.current?.d3Force("charge")?.strength(-140);
    ref.current?.d3Force("link")?.distance(55);
  }, [data]);

  return (
    <ForceGraph2D
      ref={ref}
      graphData={data}
      width={width}
      height={height}
      cooldownTicks={120}
      onEngineStop={() => ref.current?.zoomToFit(400, 50)}
      linkColor={() => "rgba(148,163,184,0.6)"}
      linkLabel="label"
      nodeLabel={(n) => `${KIND_STYLE[n.kind as NodeKind].name}: ${n.value}`}
      onNodeClick={(n) => onNodeClick(n as unknown as GraphNode)}
      nodeCanvasObject={(n, ctx, scale) => {
        const node = n as unknown as GraphNode & { x: number; y: number };
        const style = KIND_STYLE[node.kind];
        const radius = node.isCenter ? 9 : node.kind === "more" ? 4 : 6;

        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
        ctx.fillStyle = style.color;
        ctx.fill();

        if (node.isCenter) {
          ctx.lineWidth = 2.5 / scale;
          ctx.strokeStyle = "#ef4444";
          ctx.stroke();
        }

        // Label the important nodes always, the rest once zoomed in.
        const hub = node.isCenter || node.kind === "provider" || node.kind === "phone" || node.kind === "invoice_number";
        if (hub || node.kind === "more" || scale > 2) {
          const size = Math.max(10 / scale, 3);
          ctx.font = `${node.isCenter ? "600 " : ""}${size}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillStyle = "#64748b";
          ctx.fillText(node.label, node.x, node.y + radius + 2);
        }
      }}
      nodePointerAreaPaint={(n, color, ctx) => {
        const node = n as unknown as GraphNode & { x: number; y: number };
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI);
        ctx.fill();
      }}
    />
  );
}
