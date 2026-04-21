from __future__ import annotations

import json
import os
from typing import Any

import openai
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
        "type": "function",
        "function": {
            "name": "get_summary_stats",
            "description": "Obtiene estadísticas generales de disponibilidad de tiendas: fechas, promedios, máximos y mínimos. No requiere parámetros.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_availability_by_hour",
            "description": "Disponibilidad promedio de tiendas agrupada por hora del día (0-23). Opcionalmente filtra por fecha.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Fecha en formato YYYY-MM-DD. Si no se provee, usa todos los días."}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_availability_by_day",
            "description": "Disponibilidad promedio de tiendas por día calendario. No requiere parámetros.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_anomalies",
            "description": "Detecta caídas o picos anormales en disponibilidad de tiendas. Usa threshold_pct=10 por defecto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold_pct": {
                        "type": "number",
                        "description": "Porcentaje mínimo de cambio para considerar anomalía. Valor recomendado: 10.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_time_periods",
            "description": "Compara disponibilidad entre dos períodos de tiempo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period1_start": {"type": "string", "description": "Inicio período 1, formato YYYY-MM-DD HH:MM"},
                    "period1_end": {"type": "string", "description": "Fin período 1, formato YYYY-MM-DD HH:MM"},
                    "period2_start": {"type": "string", "description": "Inicio período 2, formato YYYY-MM-DD HH:MM"},
                    "period2_end": {"type": "string", "description": "Fin período 2, formato YYYY-MM-DD HH:MM"},
                },
                "required": ["period1_start", "period1_end", "period2_start", "period2_end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_peak_hours",
            "description": "Retorna las mejores y peores horas del día para disponibilidad de tiendas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "top_n": {"type": "integer", "description": "Cuántos resultados retornar. Por defecto 5."}
                },
                "required": [],
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


def chat(messages: list[dict[str, Any]], df: pd.DataFrame) -> tuple[str, list[dict[str, Any]]]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return "No encontré GROQ_API_KEY en el archivo .env.", []

    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    all_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=all_messages,
        tools=TOOLS,
        tool_choice="auto",
        parallel_tool_calls=False,
    )

    message = response.choices[0].message
    tool_calls: list[dict[str, Any]] = []

    if not message.tool_calls:
        return message.content or "", []

    for tc in message.tool_calls:
        tool_calls.append({"name": tc.function.name, "input": tc.function.arguments})

    all_messages.append(message)

    for tc in message.tool_calls:
        tool_input = json.loads(tc.function.arguments)
        tool_result = execute_tool(tc.function.name, tool_input, df)
        all_messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": tool_result,
        })

    final_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=all_messages,
        tools=TOOLS,
        tool_choice="auto",
        parallel_tool_calls=False,
    )

    return final_response.choices[0].message.content or "", tool_calls
