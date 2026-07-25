import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="CCD Saneaclima - Telemetria", layout="wide")

st.title("🌊 CCD Saneaclima — Monitoramento Unificado")
st.markdown("Visão consolidada de dados de telemetria hídrica e atmosférica (SIMQUA + Sintético)")

# Conexão com o banco SQLite
conn = sqlite3.connect("db/saneaclima.db")

# Carrega estações
df_estacoes = pd.read_sql_query("SELECT * FROM estacoes", conn)

# Sidebar para filtros
st.sidebar.header("Filtros")
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
    
    # Gráfico de pH e Turbidez
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
    # Sintaxe atualizada para evitar warnings
    st.plotly_chart(fig, use_container_width="stretch")

    # Tabela com os dados brutos padronizados
    st.subheader("📋 Tabela Canônica Padronizada")
    st.dataframe(df_telemetria, use_container_width="stretch")

conn.close()