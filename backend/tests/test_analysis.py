import pandas as pd
import analysis


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_selects_latest_before_cutoff():
    fc = pd.DataFrame({
        "startTime": [ts("2026-01-02 12:00")] * 3,
        "publishTime": [ts("2026-01-01 06:00"), ts("2026-01-01 08:00"), ts("2026-01-01 10:00")],
        "forecast": [100.0, 200.0, 300.0],
    })
    out = analysis.select_latest_forecasts(fc, cutoff_hour=9)
    assert len(out) == 1 and out.iloc[0]["forecast"] == 200.0  # 10:00 is after cutoff


def test_metrics():
    df = pd.DataFrame({"actual": [100.0, 200.0], "forecast": [110.0, 180.0]})
    df["error"] = df["forecast"] - df["actual"]
    m = analysis.compute_metrics(df)
    assert m["mae_mw"] == 15.0
    assert m["bias_mw"] == -5.0
    assert round(m["rmse_mw"], 4) == round(((100 + 400) / 2) ** 0.5, 4)
