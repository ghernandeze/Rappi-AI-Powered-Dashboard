from __future__ import annotations

import streamlit as st

from src.analytics import get_anomalies
from src.charts import build_heatmap, build_kpi_row, build_line_chart
from src.claude_agent import chat
from src.data_loader import load_all_data

st.set_page_config(
    page_title="Rappi Ops Intelligence Center",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
body { background-color: #0a0a0f !important; color: #e8e8f0; }
.stApp { background-color: #0a0a0f; }
[data-testid="metric-container"] {
    background: #12121a;
    border: 1px solid #2a2a3a;
    border-radius: 12px;
    padding: 16px;
    border-left: 3px solid #FF6B35;
}
.ops-header {
    background: linear-gradient(90deg, #0a0a0f, #1a1a2e);
    border-bottom: 1px solid #FF6B35;
    padding: 12px 18px;
    margin-bottom: 24px;
    border-radius: 14px;
}
.user-message {
    background: #1a1a2e;
    border-radius: 12px 12px 4px 12px;
    padding: 12px;
    margin: 8px 0;
    border-left: 3px solid #00d4ff;
}
.assistant-message {
    background: #12121a;
    border-radius: 12px 12px 12px 4px;
    padding: 12px;
    margin: 8px 0;
    border-left: 3px solid #FF6B35;
}
.tool-badge {
    background: #2a1a2e;
    border: 1px solid #8B5CF6;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
    color: #a78bfa;
    display: inline-block;
    margin: 2px;
}
.stButton button {
    background: #12121a !important;
    border: 1px solid #2a2a3a !important;
    color: #8888aa !important;
    border-radius: 20px !important;
    font-size: 12px !important;
}
.stButton button:hover {
    border-color: #FF6B35 !important;
    color: #FF6B35 !important;
}
"""

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)



def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "tool_calls_history" not in st.session_state:
        st.session_state.tool_calls_history = []
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None



def add_prompt(prompt: str, df) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    response_text, tool_calls = chat(st.session_state.messages, df)
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.session_state.tool_calls_history.append(tool_calls)



def render_chat(df) -> None:
    st.subheader("AI Analyst")
    st.caption("Haz preguntas sobre comportamiento operativo, anomalías y disponibilidad.")

    suggested_questions = [
        "¿Cuál fue el peor día de disponibilidad?",
        "¿A qué hora hay menos tiendas online?",
        "¿Hubo caídas importantes en la primera semana?",
        "Compara la primera y segunda semana de febrero",
    ]

    button_cols = st.columns(2)
    for idx, question in enumerate(suggested_questions):
        col = button_cols[idx % 2]
        if col.button(question, key=f"suggested_{idx}", use_container_width=True):
            st.session_state.pending_prompt = question

    with st.container(height=520):
        for idx, message in enumerate(st.session_state.messages):
            role = message["role"]
            css_class = "user-message" if role == "user" else "assistant-message"
            speaker = "Tú" if role == "user" else "Analista"
            st.markdown(
                f"<div class='{css_class}'><strong>{speaker}</strong><br>{message['content']}</div>",
                unsafe_allow_html=True,
            )
            if role == "assistant":
                tool_idx = len([m for m in st.session_state.messages[: idx + 1] if m["role"] == "assistant"]) - 1
                if 0 <= tool_idx < len(st.session_state.tool_calls_history):
                    calls = st.session_state.tool_calls_history[tool_idx]
                    if calls:
                        with st.expander("🔧 Herramientas usadas", expanded=False):
                            badges = []
                            for call in calls:
                                badges.append(
                                    f"<span class='tool-badge'>{call['name']}({call['input']})</span>"
                                )
                            st.markdown("".join(badges), unsafe_allow_html=True)

    prompt = st.chat_input("Pregunta sobre los datos...")
    final_prompt = prompt or st.session_state.pending_prompt
    if final_prompt:
        st.session_state.pending_prompt = None
        add_prompt(final_prompt, df)
        st.rerun()



def main() -> None:
    init_state()

    st.markdown(
        """
        <div class="ops-header">
            <h1 style="margin:0; color:#ffffff;">🛒 Rappi Ops Intelligence Center</h1>
            <p style="margin:6px 0 0 0; color:#bdbdd0;">Febrero 2026 · Colombia</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        df = load_all_data()
    except Exception as exc:
        st.error(f"Error cargando datos: {exc}")
        st.stop()

    kpis = build_kpi_row(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tiendas Promedio", kpis["avg_stores"], kpis["avg_delta"])
    c2.metric("Pico Máximo", kpis["peak_stores"], kpis["peak_delta"])
    c3.metric("Mínimo Histórico", kpis["min_stores"], kpis["min_delta"])
    c4.metric("Anomalías Detectadas", kpis["anomaly_count"], kpis["anomaly_delta"])

    st.plotly_chart(build_heatmap(df), use_container_width=True)

    left, right = st.columns([0.65, 0.35])
    all_dates = sorted(df["date"].unique())
    date_options = ["Todos los días"] + [str(d) for d in all_dates]

    with left:
        selected_date = st.selectbox("Fecha", date_options, index=0)
        show_anomalies = st.checkbox("Mostrar anomalías", value=True)
        anomalies = get_anomalies(df, threshold_pct=10) if show_anomalies else []
        st.plotly_chart(
            build_line_chart(df, date_filter=selected_date, anomalies=anomalies),
            use_container_width=True,
        )

    with right:
        render_chat(df)


if __name__ == "__main__":
    main()
