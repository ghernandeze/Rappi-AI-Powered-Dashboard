from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from src.analytics import get_anomalies

BG = "#0a0a0f"
PANEL = "#12121a"
TEXT = "#e8e8f0"
GRID = "#2a2a3a"
ACCENT = "#FF6B35"
GREEN = "#00FF88"
RED = "#FF4D4F"
GRAY = "#8b8b99"



def build_heatmap(df: pd.DataFrame) -> go.Figure:
    pivot = pd.pivot_table(
        df,
        index="date",
        columns="hour",
        values="stores",
        aggfunc="mean",
    ).sort_index()

    x_values = list(range(24))
    pivot = pivot.reindex(columns=x_values)

    fig = go.Figure(
        data=go.Heatmap(
            x=x_values,
            y=[str(d) for d in pivot.index],
            z=pivot.values,
            colorscale=[
                [0, "#1a0a0a"],
                [0.3, "#8B0000"],
                [0.6, "#FF6B35"],
                [1.0, "#00FF88"],
            ],
            hovertemplate="Hora: %{x}h<br>Fecha: %{y}<br>Tiendas: %{z:,.0f}<extra></extra>",
            colorbar=dict(title="Tiendas", tickfont=dict(color=TEXT), titlefont=dict(color=TEXT)),
        )
    )

    fig.update_layout(
        title="Disponibilidad por Hora y Día",
        plot_bgcolor=BG,
        paper_bgcolor=BG,
        font=dict(color=TEXT),
        xaxis=dict(title="Hora", tickmode="array", tickvals=x_values, gridcolor=GRID),
        yaxis=dict(title="Fecha", gridcolor=GRID),
        margin=dict(l=20, r=20, t=50, b=20),
        height=350,
    )
    return fig



def build_line_chart(
    df: pd.DataFrame,
    date_filter: str | None = None,
    anomalies: list[dict[str, Any]] | None = None,
) -> go.Figure:
    working = df.copy()
    title = "Serie temporal de disponibilidad"

    if date_filter and date_filter != "Todos los días":
        selected_date = pd.to_datetime(date_filter).date()
        working = working[working["date"] == selected_date].copy()
        title = f"Serie temporal · {selected_date}"

    working["rolling_avg"] = working["stores"].rolling(30, center=True, min_periods=10).mean()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=working["timestamp"],
            y=working["stores"],
            mode="lines",
            name="Tiendas online",
            line=dict(color=ACCENT, width=2),
            hovertemplate="%{x}<br>Tiendas: %{y:,.0f}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=working["timestamp"],
            y=working["rolling_avg"],
            mode="lines",
            name="Rolling average",
            line=dict(color=GRAY, width=2, dash="dash"),
            hovertemplate="%{x}<br>Rolling avg: %{y:,.0f}<extra></extra>",
        )
    )

    if anomalies:
        anomaly_df = pd.DataFrame(anomalies)
        if not anomaly_df.empty:
            anomaly_df["timestamp"] = pd.to_datetime(anomaly_df["timestamp"])
            if date_filter and date_filter != "Todos los días":
                selected_date = pd.to_datetime(date_filter).date()
                anomaly_df = anomaly_df[anomaly_df["timestamp"].dt.date == selected_date]
            if not anomaly_df.empty:
                fig.add_trace(
                    go.Scatter(
                        x=anomaly_df["timestamp"],
                        y=anomaly_df["stores"],
                        mode="markers",
                        name="Anomalías",
                        marker=dict(color=RED, size=8),
                        hovertemplate="%{x}<br>Tiendas: %{y:,.0f}<br>Cambio: %{text}%<extra></extra>",
                        text=anomaly_df["pct_change"],
                    )
                )

    fig.update_layout(
        title=title,
        plot_bgcolor=BG,
        paper_bgcolor=BG,
        font=dict(color=TEXT),
        xaxis=dict(title="Timestamp", gridcolor=GRID),
        yaxis=dict(title="Tiendas", gridcolor=GRID),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=20),
        height=420,
    )
    return fig



def build_kpi_row(df: pd.DataFrame) -> dict[str, Any]:
    anomalies = get_anomalies(df, threshold_pct=10)
    avg = int(round(df["stores"].mean()))
    peak = int(round(df["stores"].max()))
    low = int(round(df["stores"].min()))

    peak_row = df.loc[df["stores"].idxmax()]
    low_row = df.loc[df["stores"].idxmin()]

    first_day = min(df["date"])
    first_day_avg = df.loc[df["date"] == first_day, "stores"].mean()
    delta_pct = ((avg - first_day_avg) / first_day_avg) * 100 if first_day_avg else 0

    return {
        "avg_stores": f"{avg:,}",
        "avg_delta": f"{delta_pct:+.1f}% vs primer día",
        "peak_stores": f"{peak:,}",
        "peak_delta": peak_row["timestamp"].strftime("%Y-%m-%d %H:%M"),
        "min_stores": f"{low:,}",
        "min_delta": low_row["timestamp"].strftime("%Y-%m-%d %H:%M"),
        "anomaly_count": str(len(anomalies)),
        "anomaly_delta": "+ ver detalle",
    }
