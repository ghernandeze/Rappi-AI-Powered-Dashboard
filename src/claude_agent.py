from __future__ import annotations

import json
import os
from typing import Any

import anthropic
import pandas as pd
from dotenv import load_dotenv

from src.analytics import (
    compare_time_periods,
    get_anomalies,
    get_availability_by_day,
    get_availability_by_hour,
    get_peak_hours,
    get_summary_stats,
)

load_dotenv()

TOOLS = [
    {
        "name": "get_summary_stats",
        "description": "Obtiene estadísticas generales de disponibilidad de tiendas: fechas, promedios, máximos y mínimos.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_availability_by_hour",
        "description": "Disponibilidad promedio de tiendas agrupada por hora del día (0-23).",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Fecha opcional en formato YYYY-MM-DD para filtrar"}
            },
        },
    },
    {
        "name": "get_availability_by_day",
        "description": "Disponibilidad promedio de tiendas por día calendario.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_anomalies",
        "description": "Detecta caídas o picos anormales en disponibilidad de tiendas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "threshold_pct": {
                    "type": "number",
                    "description": "Porcentaje mínimo de cambio para considerar anomalía (default: 10)",
                }
            },
        },
    },
    {
        "name": "compare_time_periods",
        "description": "Compara disponibilidad entre dos períodos de tiempo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period1_start": {"type": "string"},
                "period1_end": {"type": "string"},
                "period2_start": {"type": "string"},
                "period2_end": {"type": "string"},
            },
            "required": ["period1_start", "period1_end", "period2_start", "period2_end"],
        },
    },
    {
        "name": "get_peak_hours",
        "description": "Retorna las mejores y peores horas del día para disponibilidad.",
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "description": "Cuántos resultados retornar (default: 5)"}
            },
        },
    },
]

SYSTEM_PROMPT = """
Eres un analista de operaciones de Rappi especializado en disponibilidad de tiendas.
Tienes acceso a datos históricos de febrero 2026 de Colombia.
Cuando el usuario haga preguntas sobre los datos, usa las herramientas disponibles para consultar los datos reales.
Responde siempre en español, de forma concisa y con insights accionables.
Cuando encuentres anomalías o patrones interesantes, explica su posible impacto operacional.
""".strip()



def execute_tool(tool_name: str, tool_input: dict[str, Any], df: pd.DataFrame) -> str:
    if tool_name == "get_summary_stats":
        result = get_summary_stats(df)
    elif tool_name == "get_availability_by_hour":
        result = get_availability_by_hour(df, date=tool_input.get("date"))
    elif tool_name == "get_availability_by_day":
        result = get_availability_by_day(df)
    elif tool_name == "get_anomalies":
        result = get_anomalies(df, threshold_pct=tool_input.get("threshold_pct", 10))
    elif tool_name == "compare_time_periods":
        result = compare_time_periods(
            df,
            period1_start=tool_input["period1_start"],
            period1_end=tool_input["period1_end"],
            period2_start=tool_input["period2_start"],
            period2_end=tool_input["period2_end"],
        )
    elif tool_name == "get_peak_hours":
        result = get_peak_hours(df, top_n=tool_input.get("top_n", 5))
    else:
        result = {"error": f"Tool desconocida: {tool_name}"}

    return json.dumps(result, ensure_ascii=False, default=str)



def _extract_text_from_response(response: Any) -> str:
    text_blocks: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_blocks.append(block.text)
    return "\n".join(text_blocks).strip()



def chat(messages: list[dict[str, Any]], df: pd.DataFrame) -> tuple[str, list[dict[str, Any]]]:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return "No encontré ANTHROPIC_API_KEY en el archivo .env.", []

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
    )

    if response.stop_reason != "tool_use":
        return _extract_text_from_response(response), []

    assistant_content = []
    tool_calls: list[dict[str, Any]] = []
    tool_result_blocks = []

    for block in response.content:
        if getattr(block, "type", None) == "text":
            assistant_content.append({"type": "text", "text": block.text})
        elif getattr(block, "type", None) == "tool_use":
            assistant_content.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }
            )
            tool_calls.append({"name": block.name, "input": block.input})
            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": execute_tool(block.name, block.input, df),
                }
            )

    second_pass_messages = messages + [
        {"role": "assistant", "content": assistant_content},
        {"role": "user", "content": tool_result_blocks},
    ]

    final_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=second_pass_messages,
    )

    return _extract_text_from_response(final_response), tool_calls
