"""
main.py - FastAPI application exposing wind forecast accuracy analysis.

Endpoints:
  GET /api/health
  GET /api/wind-analysis?start=YYYY-MM-DD&end=YYYY-MM-DD&cutoff_hour=9
Data is loaded once (disk cache, else Elexon) and analysis runs in memory.
"""
import os
from datetime import date
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import analysis
import elexon

app = FastAPI(title="UK Wind Forecast Evaluation API")

raw_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
origins = []
for o in raw_origins:
    origins.append(o)
    origins.append(o.rstrip("/"))
origins = list(set(origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in origins else origins,
    allow_origin_regex=r"https://.*\.vercel\.app" if "*" not in origins else None,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def _data():
    return elexon.get_actuals(), elexon.get_forecasts()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/wind-analysis")
def wind_analysis(
    start: date = Query(date(2026, 1, 1)),
    end: date = Query(date(2026, 1, 31)),
    cutoff_hour: float = Query(9.0, ge=0, le=23.5,
                               description="Decision cutoff on D-1, hours UTC"),
):
    if start > end:
        raise HTTPException(400, "start must be <= end")
    if start < elexon.WINDOW_START or end > elexon.WINDOW_END:
        raise HTTPException(400, "Dates must be within January 2026")
    actuals, forecasts = _data()
    df = analysis.build_comparison(actuals, forecasts, start, end, cutoff_hour)
    series = [{
        "t": r.startTime.isoformat(),
        "actual": float(r.actual),
        "forecast": float(r.forecast),
        "error": float(r.error),
        "publish_time": r.publishTime.isoformat(),
        "lead_hours": round(float(r.leadHours), 1),
    } for r in df.itertuples()]
    return {
        "assumptions": {"cutoff_hour_utc": cutoff_hour,
                        "rule": "latest forecast published on or before D-1 cutoff",
                        "error_sign": "forecast - actual"},
        "metrics": analysis.compute_metrics(df),
        "by_hour": analysis.metrics_by_hour(df),
        "series": series,
    }
