from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


TIMESTAMP_PATTERN = "%a %b %d %Y %H:%M:%S %z"


def parse_timestamp(col_name: str) -> pd.Timestamp:
    """Parsea timestamps tipo: Sun Feb 01 2026 06:59:40 GMT-0500."""
    cleaned = re.sub(r"\s*\(.*?\)", "", str(col_name)).strip()
    cleaned = cleaned.replace("GMT", "")  # %z no acepta prefijo GMT, solo ±HHMM
    return pd.to_datetime(cleaned, format=TIMESTAMP_PATTERN)



def _coerce_store_value(value: object) -> float:
    if pd.isna(value):
        return float("nan")
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if cleaned == "":
            return float("nan")
        return float(cleaned)
    return float(value)



def load_single_csv(filepath: str | Path) -> pd.DataFrame:
    """Lee un CSV wide y lo transforma a formato largo con timestamp y stores."""
    raw = pd.read_csv(filepath, header=0)
    if raw.empty:
        return pd.DataFrame(columns=["timestamp", "stores"])

    row = raw.iloc[0]
    timestamp_columns = raw.columns[4:]
    store_values = row.iloc[4:]

    records = []
    for ts_raw, stores_raw in zip(timestamp_columns, store_values):
        try:
            timestamp = parse_timestamp(ts_raw)
            stores = _coerce_store_value(stores_raw)
            records.append({"timestamp": timestamp, "stores": stores})
        except Exception:
            continue

    return pd.DataFrame(records)



def _resolve_csv_files(base_path: str) -> list[str]:
    patterns: Iterable[str] = (
        os.path.join(base_path, "AVAILABILITY-data*.csv"),
        os.path.join(base_path, "*AVAILABILITY-data*.csv"),
        os.path.join(base_path, "*.csv"),
    )

    files: list[str] = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            files = matches
            break
    return files


@st.cache_data(show_spinner="Cargando datos históricos...")
def load_all_data() -> pd.DataFrame:
    """Carga todos los CSVs, deduplica timestamps y agrega variables derivadas."""
    data_path = os.getenv("DATA_PATH", "").strip()
    if not data_path:
        raise ValueError("DATA_PATH no está configurado en el archivo .env")
    if not os.path.isdir(data_path):
        raise FileNotFoundError(f"La ruta DATA_PATH no existe o no es carpeta: {data_path}")

    files = _resolve_csv_files(data_path)
    if not files:
        raise FileNotFoundError(f"No se encontraron CSVs en: {data_path}")

    frames = [load_single_csv(file) for file in files]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise ValueError("No se pudo extraer información válida desde los CSVs.")

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["timestamp", "stores"])
    df = df.drop_duplicates(subset="timestamp")
    df = df.sort_values("timestamp").reset_index(drop=True)

    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.day_name()
    df["stores_int"] = df["stores"].round().astype(int)
    return df
