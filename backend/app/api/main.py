"""Minimal FastAPI app: health/status only (milestone M0).

Dashboard-facing routes (overview, symbol detail, tape, alerts feed) arrive
with milestone M5 — see docs/PLAN.md §15/§19.
"""

from fastapi import FastAPI

app = FastAPI(title="Dark Pool Intelligence Engine", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
