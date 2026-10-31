# Fraud Investigation Portal

Next.js + Tailwind frontend for the detection API.

## Run

```bash
# 1. Detection results and API (from the project root)
python -m detection.main
uvicorn api.main:app --port 8000

# 2. Frontend (from this folder)
npm install
npm run dev          # http://localhost:3000
```

The API address is `NEXT_PUBLIC_API_URL` in `.env.local` (default `http://localhost:8000`).
The API allows `localhost:3000` and `localhost:5173` by default; set `CORS_ORIGINS` there for others.

## Pages

| Route | Shows |
|---|---|
| `/` | Executive summary: entities scored, risk levels, precision / recall / F1, per-pattern evaluation |
| `/queue` | Paginated analyst queue. Filters: risk level, entity type, signal. Deep links: `/queue?risk=HIGH` |
| `/entities/{type}/{id}` | Score, every signal with its evidence, and the network graph |

## Layout

```
lib/api.ts        typed API client
lib/graph.ts      evidence -> graph nodes and links (pure, no React)
lib/labels.ts     signal names and explanations
components/      Dashboard, QueueTable, EntityView, EntityGraph, GraphCanvas
app/             routes
```

`GraphCanvas` is loaded in the browser only (`next/dynamic`, `ssr: false`) because the graph library needs `window`.
Keep other modules from importing it directly, or the library is bundled for the server and breaks.
