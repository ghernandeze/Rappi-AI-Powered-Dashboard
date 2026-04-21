from __future__ import annotations

from typing import Any

import pandas as pd


DATETIME_FMT = "%Y-%m-%d %H:%M"
DATE_FMT = "%Y-%m-%d"



def _empty_period_stats() -> dict[str, Any]:
    return {"avg": None, "min": None, "max": None, "records": 0}



def get_summary_stats(df: pd.DataFrame) -> dict[str, Any]:
    max_idx = df["stores"].idxmax()
    min_idx = df["stores"].idxmin()

    return {
        "total_records": int(len(df)),
        "date_range_start": df["timestamp"].min().strftime(DATE_FMT),
        "date_range_end": df["timestamp"].max().strftime(DATE_FMT),
        "avg_stores": round(float(df["stores"].mean()), 0),
        "max_stores": int(round(df.loc[max_idx, "stores"])),
        "min_stores": int(round(df.loc[min_idx, "stores"])),
        "max_stores_timestamp": df.loc[max_idx, "timestamp"].strftime(DATETIME_FMT),
        "min_stores_timestamp": df.loc[min_idx, "timestamp"].strftime(DATETIME_FMT),
        "total_days": int(df["date"].nunique()),
    }



def get_availability_by_hour(df: pd.DataFrame, date: str | None = None) -> list[dict[str, Any]]:
    working = df.copy()
    if date is not None:
        target_date = pd.to_datetime(date).date()
        working = working[working["date"] == target_date]

    grouped = (
        working.groupby("hour", as_index=False)["stores"]
        .agg(avg="mean", min="min", max="max")
        .round(0)
    )

    result_map = {
        int(row["hour"]): {
            "hour": int(row["hour"]),
            "avg": int(row["avg"]),
            "min": int(row["min"]),
            "max": int(row["max"]),
        }
        for _, row in grouped.iterrows()
    }

    result = []
    for hour in range(24):
        result.append(result_map.get(hour, {"hour": hour, "avg": None, "min": None, "max": None}))
    return result



def get_availability_by_day(df: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        df.groupby("date", as_index=False)["stores"]
        .agg(avg="mean", min="min", max="max", std="std")
        .round(0)
    )

    results: list[dict[str, Any]] = []
    for _, row in grouped.iterrows():
        std_value = None if pd.isna(row["std"]) else int(row["std"])
        results.append(
            {
                "date": pd.to_datetime(row["date"]).strftime(DATE_FMT),
                "avg": int(row["avg"]),
                "min": int(row["min"]),
                "max": int(row["max"]),
                "std": std_value,
            }
        )
    return results



def get_anomalies(df: pd.DataFrame, threshold_pct: float = 10) -> list[dict[str, Any]]:
    working = df[["timestamp", "stores"]].copy()
    working["rolling_avg"] = working["stores"].rolling(30, center=True, min_periods=10).mean()
    working["pct_change_vs_rolling"] = ((working["stores"] - working["rolling_avg"]) / working["rolling_avg"]) * 100
    mask = working["pct_change_vs_rolling"].abs() > threshold_pct
    anomaly_rows = working.loc[mask].copy()
    if anomaly_rows.empty:
        return []

    anomaly_rows = anomaly_rows.reset_index().rename(columns={"index": "original_index"})
    anomaly_rows["gap"] = anomaly_rows["original_index"].diff().fillna(1)
    anomaly_rows["event_id"] = (anomaly_rows["gap"] > 1).cumsum()

    events: list[dict[str, Any]] = []
    for _, group in anomaly_rows.groupby("event_id"):
        representative = group.loc[group["pct_change_vs_rolling"].abs().idxmax()]
        event_size = len(group)
        event_type = "drop" if representative["pct_change_vs_rolling"] < 0 else "spike"
        events.append(
            {
                "timestamp": representative["timestamp"].strftime(DATETIME_FMT),
                "stores": int(round(representative["stores"])),
                "pct_change": round(float(representative["pct_change_vs_rolling"]), 2),
                "type": event_type,
                "event_points": int(event_size),
            }
        )

    events.sort(key=lambda x: abs(x["pct_change"]), reverse=True)
    return events[:20]



def compare_time_periods(
    df: pd.DataFrame,
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
) -> dict[str, Any]:
    p1_start = pd.to_datetime(period1_start)
    p1_end = pd.to_datetime(period1_end)
    p2_start = pd.to_datetime(period2_start)
    p2_end = pd.to_datetime(period2_end)

    period1 = df[(df["timestamp"] >= p1_start) & (df["timestamp"] <= p1_end)]
    period2 = df[(df["timestamp"] >= p2_start) & (df["timestamp"] <= p2_end)]

    def stats(period_df: pd.DataFrame) -> dict[str, Any]:
        if period_df.empty:
            return _empty_period_stats()
        return {
            "avg": round(float(period_df["stores"].mean()), 2),
            "min": int(round(period_df["stores"].min())),
            "max": int(round(period_df["stores"].max())),
            "records": int(len(period_df)),
        }

    period1_stats = stats(period1)
    period2_stats = stats(period2)

    avg1 = period1_stats["avg"]
    avg2 = period2_stats["avg"]
    difference_pct = None
    better_period = None

    if avg1 not in (None, 0) and avg2 is not None:
        difference_pct = round(((avg2 - avg1) / avg1) * 100, 2)
        better_period = "2" if avg2 > avg1 else "1"
        if avg1 == avg2:
            better_period = "equal"

    return {
        "period1": period1_stats,
        "period2": period2_stats,
        "difference_pct": difference_pct,
        "better_period": better_period,
    }



def get_peak_hours(df: pd.DataFrame, top_n: int = 5) -> dict[str, Any]:
    grouped = df.groupby("hour", as_index=False)["stores"].mean().round(0)
    grouped["stores"] = grouped["stores"].astype(int)

    best = grouped.sort_values("stores", ascending=False).head(top_n)
    worst = grouped.sort_values("stores", ascending=True).head(top_n)

    return {
        "best_hours": [{"hour": int(row["hour"]), "avg": int(row["stores"])} for _, row in best.iterrows()],
        "worst_hours": [{"hour": int(row["hour"]), "avg": int(row["stores"])} for _, row in worst.iterrows()],
    }
