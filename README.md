##🚀 AI-Powered Dashboard – Disponibilidad de Tiendas
📌 Descripción

Este proyecto consiste en una aplicación web que analiza datos históricos de disponibilidad de tiendas (online/offline) y los transforma en información útil para toma de decisiones.

La aplicación tiene dos componentes principales:

📊 Dashboard interactivo con métricas y visualizaciones
🤖 Chatbot inteligente que responde preguntas sobre los datos y genera insights
🎯 Objetivo

Convertir datos crudos (archivos CSV) en:

métricas claras (uptime, downtime, fallos)
visualizaciones entendibles
recomendaciones accionables usando AI
🛠 Tecnologías utilizadas
Python
Pandas → procesamiento de datos
Streamlit → interfaz web
Plotly → gráficos interactivos
OpenAI API → chatbot semántico
⚙️ Cómo funciona
1. Procesamiento de datos

Se cargan múltiples archivos CSV con información de disponibilidad y se transforman en un dataset unificado.

Se realizan pasos como:

limpieza de datos
normalización de fechas
consolidación de archivos
cálculo de métricas por tienda
2. Dashboard

La app muestra:

uptime (%) por tienda
tiendas con más fallos
duración promedio offline
patrones por hora o día
filtros por fecha y tienda
3. Chatbot

El chatbot permite hacer preguntas como:

¿Qué tiendas tienen peor disponibilidad?
¿En qué horas hay más fallos?
¿Qué tiendas requieren atención urgente?

Además, responde con:

insights
recomendaciones
priorización de problemas

