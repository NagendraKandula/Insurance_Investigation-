"""
REST API for the detection results.

Serves the files written by `python -m detection.main`:
    output/risk_scores.json
    output/evaluation_report.json
    output/detector_counts.json   (optional)

Run from the project root:

    uvicorn api.main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs

The API only reads files. It never touches the database, and it notices when
the files change (a new detection run), so no restart is needed.

Settings (environment variables):
    OUTPUT_DIR     where the JSON files are (default: <project>/output)
    CORS_ORIGINS   comma-separated allowed frontend origins
                   (default: localhost:3000 and localhost:5173)
"""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output"))

DEFAULT_ORIGINS = "http://localhost:3000,http://localhost:5173"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

RISK_LEVELS = ("HIGH", "MEDIUM", "LOW")


# ----------------------------------------------------------------------
# Response models (these also drive the /docs page)
# ----------------------------------------------------------------------

class EntityScore(BaseModel):
    entity_type: str
    entity_id: str
    risk_score: float
    risk_level: str
    signal_count: int
    indicator_types: list[str]


class Signal(BaseModel):
    indicator_type: str
    weight: float
    evidence: dict[str, Any]


class EntityDetail(EntityScore):
    signals: list[Signal]


class EntityPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[EntityScore]


# ----------------------------------------------------------------------
# File-backed store that reloads itself when a file changes
# ----------------------------------------------------------------------

class ResultsNotReady(Exception):
    pass


class ResultStore:

    def __init__(self, directory: Path):
        self.directory = directory
        self._lock = Lock()
        self._mtimes: dict[str, float] = {}

        self.entities: list[dict] = []
        self.index: dict[tuple[str, str], dict] = {}
        self.evaluation: dict = {}
        self.detector_counts: dict = {}
        self.stats: dict = {}
        self.coverage: dict = {}

    def _path(self, name: str) -> Path:
        return self.directory / name

    def file_status(self) -> dict:
        status = {}
        for name in ("risk_scores.json", "evaluation_report.json", "detector_counts.json"):
            path = self._path(name)
            if path.exists():
                modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                status[name] = {"found": True, "modified": modified.isoformat()}
            else:
                status[name] = {"found": False, "modified": None}
        return status

    def refresh(self) -> None:
        """Load (or reload) the files if they are new or have changed."""
        required = ("risk_scores.json", "evaluation_report.json")
        missing = [name for name in required if not self._path(name).exists()]
        if missing:
            raise ResultsNotReady(
                f"Missing {', '.join(missing)} in {self.directory}. "
                "Run `python -m detection.main` first."
            )

        names = required + ("detector_counts.json",)
        current = {
            name: self._path(name).stat().st_mtime
            for name in names if self._path(name).exists()
        }

        with self._lock:
            if current == self._mtimes:
                return

            with open(self._path("risk_scores.json"), encoding="utf-8") as handle:
                risk_results = json.load(handle)
            with open(self._path("evaluation_report.json"), encoding="utf-8") as handle:
                evaluation = json.load(handle)

            counts = {}
            if "detector_counts.json" in current:
                with open(self._path("detector_counts.json"), encoding="utf-8") as handle:
                    counts = json.load(handle)

            self._build(risk_results, evaluation, counts)
            self._mtimes = current

    def _build(self, risk_results: list[dict], evaluation: dict, counts: dict) -> None:
        entities = []
        for result in risk_results:
            entities.append({
                **result,
                "entity_type": str(result["entity_type"]).lower(),
                "entity_id": str(result["entity_id"]),
                "indicator_types": sorted({s["indicator_type"] for s in result["signals"]}),
            })

        self.entities = entities
        self.index = {(e["entity_type"], e["entity_id"]): e for e in entities}
        self.evaluation = evaluation
        self.detector_counts = counts

        indicator_counts = Counter(
            indicator for e in entities for indicator in e["indicator_types"]
        )
        self.stats = {
            "total_entities": len(entities),
            "by_risk_level": {
                level: sum(e["risk_level"] == level for e in entities)
                for level in RISK_LEVELS
            },
            "by_entity_type": dict(sorted(Counter(e["entity_type"] for e in entities).items())),
            "by_indicator_type": dict(indicator_counts.most_common()),
        }

        # How many flagged entities are outside the set the answer key covers?
        # The evaluator only scores entities that appear in the answer key,
        # so these never count as false positives in its precision figure.
        threshold = evaluation.get("threshold", 40)
        labelled = {
            (str(r["entity_type"]).lower(), str(r["entity_id"]))
            for r in evaluation.get("detailed_results", [])
        }
        flagged = {key for key, e in self.index.items() if e["risk_score"] >= threshold}
        self.coverage = {
            "threshold": threshold,
            "flagged_total": len(flagged),
            "flagged_in_labelled_set": len(flagged & labelled),
            "flagged_outside_labelled_set": len(flagged - labelled),
            "note": (
                "The reported precision only covers entities present in the "
                "answer key. Entities flagged outside it are not counted as "
                "false positives, so true precision is lower than reported."
            ),
        }


store = ResultStore(OUTPUT_DIR)


def ready_store() -> ResultStore:
    try:
        store.refresh()
    except ResultsNotReady as error:
        raise HTTPException(status_code=503, detail=str(error))
    return store


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------

app = FastAPI(
    title="Insurance Fraud Investigation API",
    description="Read-only access to fraud detection results and evaluation.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root():
    return {
        "name": app.title,
        "docs": "/docs",
        "endpoints": ["/health", "/summary", "/risk-scores",
                      "/risk-scores/{entity_type}/{entity_id}", "/evaluation"],
    }


@app.get("/health")
def health():
    """Always responds, and says whether the result files are available."""
    status = store.file_status()
    ready = all(status[n]["found"] for n in ("risk_scores.json", "evaluation_report.json"))
    return {"status": "ok", "results_ready": ready, "output_dir": str(store.directory),
            "files": status}


@app.get("/summary")
def summary():
    """Headline numbers for a dashboard."""
    s = ready_store()
    report = s.evaluation
    return {
        **s.stats,
        "detector_findings": s.detector_counts,
        "evaluation": {
            "threshold": report.get("threshold"),
            "metrics": report.get("metrics"),
            "confusion_matrix": report.get("confusion_matrix"),
        },
        "coverage": s.coverage,
    }


@app.get("/risk-scores", response_model=EntityPage)
def list_risk_scores(
    entity_type: str | None = Query(None, description="claimant, claim, invoice or provider"),
    risk_level: str | None = Query(None, description="HIGH, MEDIUM or LOW"),
    min_score: float | None = Query(None, ge=0, le=100),
    indicator_type: str | None = Query(None, description="Only entities with this signal"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Scored entities, highest risk first. Signals are left out of the list view."""
    s = ready_store()

    if risk_level is not None:
        risk_level = risk_level.upper()
        if risk_level not in RISK_LEVELS:
            raise HTTPException(422, f"risk_level must be one of {', '.join(RISK_LEVELS)}")

    matches = s.entities
    if entity_type:
        matches = [e for e in matches if e["entity_type"] == entity_type.lower()]
    if risk_level:
        matches = [e for e in matches if e["risk_level"] == risk_level]
    if min_score is not None:
        matches = [e for e in matches if e["risk_score"] >= min_score]
    if indicator_type:
        matches = [e for e in matches if indicator_type in e["indicator_types"]]

    page = matches[offset: offset + limit]
    return EntityPage(
        total=len(matches), limit=limit, offset=offset,
        items=[EntityScore(**e) for e in page],
    )


@app.get("/risk-scores/{entity_type}/{entity_id}", response_model=EntityDetail)
def get_risk_score(entity_type: str, entity_id: str):
    """One entity with every signal and the evidence behind its score."""
    s = ready_store()
    entity = s.index.get((entity_type.lower(), entity_id))
    if entity is None:
        raise HTTPException(404, f"No scored {entity_type} with id {entity_id}")
    return EntityDetail(**entity)


@app.get("/evaluation")
def get_evaluation(
    include_details: bool = Query(
        False, description="Also return the per-entity results (large)"),
):
    """Precision, recall and F1 against the answer key, plus a coverage warning."""
    s = ready_store()
    report = {k: v for k, v in s.evaluation.items() if k != "detailed_results"}
    report["coverage"] = s.coverage
    if include_details:
        report["detailed_results"] = s.evaluation.get("detailed_results", [])
    return report