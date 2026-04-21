# Rappi Ops Intelligence Center

Dashboard interactivo con chatbot de AI para análisis de disponibilidad de tiendas Rappi — Febrero 2026.

## Requisitos

- Python 3.10+
- Cuenta en [Groq](https://console.groq.com) (gratuita) para obtener una API key

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd Rappi-AI-Powered-Dashboard

# 2. Crear entorno virtual
python -m venv .venv

# 3. Instalar dependencias
pip install -r requirements.txt
```

## Configuración

Crear un archivo `.env` en la raíz del proyecto:

```
GROQ_API_KEY=tu_api_key_de_groq
DATA_PATH=data
```

La API key se obtiene gratis en [console.groq.com](https://console.groq.com) → API Keys → Create API Key

## Correr la app

```bash
streamlit run app.py
```

Se abre automáticamente en `http://localhost:8501`


## Estructura del proyecto

```
rappi-dashboard/
├── app.py                  # App principal Streamlit
├── data/                   # 202 CSVs de disponibilidad (Feb 2026)
├── src/
│   ├── data_loader.py      # Carga y procesa los CSVs
│   ├── analytics.py        # Funciones de análisis (tools del chatbot)
│   ├── charts.py           # Visualizaciones Plotly
│   └── claude_agent.py     # Chatbot con tool use (Groq + Llama 3.3)
├── requirements.txt
└── .env                    # No incluido en el repo — crear manualmente
```


## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend + Backend | Streamlit |
| Visualizaciones | Plotly |
| Procesamiento de datos | Pandas |
| Chatbot AI | Groq API + Llama 3.3 70B |
| Tool use | OpenAI SDK (compatible con Groq) |
