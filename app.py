import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
# Importa o agente criado
from agents.anomaly_agent import analisar_estacao_com_agente

st.set_page_config(page_title="CCD Saneaclima - Telemetria", layout="wide")

st.title("🌊 CCD Saneaclima — Monitoramento Unificado")
st.markdown("Visão consolidada de dados de telemetria hídrica e atmosférica com suporte a IA Agêntica.")

# Conexão com o banco SQLite
conn = sqlite3.connect("db/saneaclima.db")
df_estacoes = pd.read_sql_query("SELECT * FROM estacoes", conn)

# Sidebar para filtros
st.sidebar.header("Filtros e Configurações")
estacao_selecionada = st.sidebar.selectbox(
    "Selecione a Estação / PCD:",
    options=df_estacoes["station_id"].unique()
)

# Carrega dados da estação selecionada
query = """
    SELECT * FROM telemetria_unificada 
    WHERE station_id = ? 
    ORDER BY timestamp ASC
"""
df_telemetria = pd.read_sql_query(query, conn, params=(estacao_selecionada,))

if df_telemetria.empty:
    st.warning("Nenhum dado encontrado para a estação selecionada.")
else:
    # Métricas de topo
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Leituras", len(df_telemetria))
    
    ultimo_ph = df_telemetria["ph"].dropna().iloc[-1] if not df_telemetria["ph"].dropna().empty else "N/A"
    col2.metric("Último pH", ultimo_ph)
    
    ultima_turb = df_telemetria["turbidez_unt"].dropna().iloc[-1] if not df_telemetria["turbidez_unt"].dropna().empty else "N/A"
    col3.metric("Última Turbidez (NTU)", ultima_turb)
    
    anomalias = len(df_telemetria[df_telemetria["quality_flag"] == "ANOMALIA"])
    col4.metric("Anomalias Injetadas", anomalias)

    st.subheader("📈 Séries Temporais dos Sensores")
    
    fig = go.Figure()
    if "ph" in df_telemetria.columns and df_telemetria["ph"].notnull().any():
        fig.add_trace(go.Scatter(x=df_telemetria["timestamp"], y=df_telemetria["ph"], name="pH", mode="lines+markers"))
    
    if "turbidez_unt" in df_telemetria.columns and df_telemetria["turbidez_unt"].notnull().any():
        fig.add_trace(go.Scatter(x=df_telemetria["timestamp"], y=df_telemetria["turbidez_unt"], name="Turbidez (NTU)", yaxis="y2", mode="lines"))

    fig.update_layout(
        title="Variação de pH e Turbidez ao longo do tempo",
        xaxis_title="Timestamp",
        yaxis=dict(title="pH"),
        yaxis2=dict(title="Turbidez (NTU)", overlaying="y", side="right"),
        legend=dict(x=0, y=1.1, orientation="h")
    )
    st.plotly_chart(fig, width="stretch")

    # --- NOVO BLOCO: DIAGNÓSTICO AGÊNTICO ---
    st.markdown("---")
    st.subheader("🤖 Diagnóstico Agêntico em Tempo Real (ReAct Framework)")
    
    if st.button("🔎 Executar Diagnóstico com IA", type="primary"):
        with st.spinner(f"O agente está analisando o histórico da estação {estacao_selecionada}..."):
            try:
                parecer = analisar_estacao_com_agente(estacao_selecionada)
                st.success("Análise concluída!")
                st.info(parecer)
            except Exception as e:
                st.error(f"Erro ao executar o agente: {e}")

    st.markdown("---")
    st.subheader("📋 Tabela Canônica Padronizada")
    st.dataframe(df_telemetria, width="stretch")

conn.close()