"""
elexon.py - Data ingestion from the Elexon BMRS API.

Fetches national wind actuals (FUELHH, fuelType=WIND) and wind forecasts
(WINDFOR) for the January 2026 study window. Raw responses are chunked
(the stream endpoints limit the query window), cleaned, and cached on disk
as gzipped CSV in backend/data/. January 2026 is historical, so the cache
never goes stale and the deployed app does not depend on Elexon at runtime.
"""
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pandas as pd

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
DATA_DIR = Path(__file__).parent / "data"

# Study window: purchase decisions for target days in January 2026.
WINDOW_START = date(2026, 1, 1)
WINDOW_END = date(2026, 1, 31)  # inclusive
# Forecasts for 1 Jan are published on 31 Dec (D-1), and some earlier,
# so fetch publications from a couple of days before the window.
PUBLISH_FROM = datetime(2025, 12, 29, tzinfo=timezone.utc)
PUBLISH_TO = datetime(2026, 2, 1, tzinfo=timezone.utc)

ACTUALS_CHUNK_DAYS = 7
FORECAST_CHUNK_DAYS = 2


def _get_json(client: httpx.Client, path: str, params: dict) -> list:
    """GET with simple retry/backoff; returns the parsed JSON list."""
    for attempt in range(4):
        try:
            resp = client.get(f"{BASE_URL}{path}", params=params, timeout=90)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    return []


def fetch_actuals() -> pd.DataFrame:
    """Half-hourly national wind generation (MW). Columns: startTime, actual."""
    rows = []
    with httpx.Client() as client:
        cur = WINDOW_START
        while cur <= WINDOW_END:
            end = min(cur + timedelta(days=ACTUALS_CHUNK_DAYS - 1), WINDOW_END)
            rows += _get_json(client, "/datasets/FUELHH/stream", {
                "settlementDateFrom": cur.isoformat(),
                "settlementDateTo": end.isoformat(),
                "fuelType": "WIND",
            })
            cur = end + timedelta(days=1)
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = df.rename(columns={"generation": "actual"})[["startTime", "actual"]]
    return df.drop_duplicates("startTime").sort_values("startTime").reset_index(drop=True)


def fetch_forecasts() -> pd.DataFrame:
    """All wind forecast publications. Columns: startTime, publishTime, forecast."""
    rows = []
    with httpx.Client() as client:
        cur = PUBLISH_FROM
        while cur < PUBLISH_TO:
            end = min(cur + timedelta(days=FORECAST_CHUNK_DAYS), PUBLISH_TO)
            rows += _get_json(client, "/datasets/WINDFOR/stream", {
                "publishDateTimeFrom": cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "publishDateTimeTo": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            cur = end
    df = pd.DataFrame(rows)
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.rename(columns={"generation": "forecast"})[["startTime", "publishTime", "forecast"]]
    # Keep only targets inside the window.
    lo = pd.Timestamp(WINDOW_START, tz="UTC")
    hi = pd.Timestamp(WINDOW_END + timedelta(days=1), tz="UTC")
    df = df[(df["startTime"] >= lo) & (df["startTime"] < hi)]
    return df.drop_duplicates(["startTime", "publishTime"]).reset_index(drop=True)


def _load_or_fetch(name: str, fetcher) -> pd.DataFrame:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{name}.csv.gz"
    if path.exists():
        df = pd.read_csv(path)
        for col in ("startTime", "publishTime"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], utc=True)
        return df
    df = fetcher()
    df.to_csv(path, index=False, compression="gzip")
    return df


def get_actuals() -> pd.DataFrame:
    return _load_or_fetch("actuals_wind_jan2026", fetch_actuals)


def get_forecasts() -> pd.DataFrame:
    return _load_or_fetch("forecasts_wind_jan2026", fetch_forecasts)
