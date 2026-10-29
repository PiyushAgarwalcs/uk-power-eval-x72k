"""
analysis.py - Forecast selection and error metrics (pure functions, no I/O).

Core idea: a day-ahead buyer must decide on day D-1 before gate closure, so
for each target half-hour on day D we may only use forecasts published at or
before the cutoff time on D-1. Among those we take the LATEST publication.
We then compare that forecast with the actual generation.

Sign convention: error = forecast - actual.
  error > 0  -> wind over-forecast -> buyer under-procures thermal power.
"""
import numpy as np
import pandas as pd


def select_latest_forecasts(forecasts: pd.DataFrame, cutoff_hour: float) -> pd.DataFrame:
    """For each startTime, pick the newest forecast published <= (D-1 at cutoff_hour UTC).

    January is GMT, so UTC == UK local time.
    """
    fc = forecasts.copy()
    target_day = fc["startTime"].dt.normalize()
    fc["decisionTime"] = target_day - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour)
    eligible = fc[fc["publishTime"] <= fc["decisionTime"]]
    if eligible.empty:
        return eligible[["startTime", "publishTime", "forecast"]]
    idx = eligible.groupby("startTime")["publishTime"].idxmax()
    return eligible.loc[idx, ["startTime", "publishTime", "forecast"]].reset_index(drop=True)


def build_comparison(actuals, forecasts, start, end, cutoff_hour) -> pd.DataFrame:
    """Join the chosen forecast to actuals for target days start..end (inclusive)."""
    chosen = select_latest_forecasts(forecasts, cutoff_hour)
    df = chosen.merge(actuals, on="startTime", how="inner")
    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    df = df[(df["startTime"] >= lo) & (df["startTime"] < hi)].sort_values("startTime")
    df["error"] = df["forecast"] - df["actual"]
    df["leadHours"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    return df.reset_index(drop=True)


def compute_metrics(df: pd.DataFrame) -> dict:
    """Headline accuracy metrics over the comparison frame."""
    if df.empty:
        return {"n": 0}
    err = df["error"].to_numpy()
    abs_err = np.abs(err)
    total_actual = df["actual"].sum()
    return {
        "n": int(len(df)),
        "mae_mw": float(abs_err.mean()),
        "rmse_mw": float(np.sqrt((err ** 2).mean())),
        "bias_mw": float(err.mean()),
        "wape_pct": float(abs_err.sum() / total_actual * 100) if total_actual else None,
        "p90_abs_error_mw": float(np.quantile(abs_err, 0.90)),
        # 90% of the time the over-forecast is below this -> a sensible MW buffer
        "p90_overforecast_mw": float(np.quantile(err, 0.90)),
        "p10_error_mw": float(np.quantile(err, 0.10)),
        "mean_actual_mw": float(df["actual"].mean()),
    }


def metrics_by_hour(df: pd.DataFrame) -> list:
    """MAE and bias grouped by hour of day of the target time."""
    if df.empty:
        return []
    g = df.assign(hour=df["startTime"].dt.hour).groupby("hour")
    out = g.agg(mae_mw=("error", lambda s: float(np.abs(s).mean())),
                bias_mw=("error", "mean")).reset_index()
    return out.to_dict(orient="records")
