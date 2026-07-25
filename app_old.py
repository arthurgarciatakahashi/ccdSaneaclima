import streamlit as st
import requests

st.set_page_config(page_title="Saneaclima Dashboard", page_icon="💧", layout="wide")

st.title("💧 CCD Saneaclima - Painel de Controle e Telemetria")
st.markdown("---")

# --- 1. SIMULAÇÃO DOS DADOS DOS MANANCIAIS (Vem das suas funções do Passo 3) ---
# Em produção, você faria uma requisição para a API buscar esses dados do banco
status_sul = "Crítico"  # Mude para "Normal" para testar o cenário estável
nivel_sul = 18
clima_previsao = "Estiagem Severa (5 dias)"

# --- 2. CONSTRUÇÃO DO DASHBOARD VISUAL (Linha Superior) ---
st.subheader("📊 Status Atual dos Mananciais")
col1, col2, col3 = st.columns(3)

with col1:
    if status_sul == "Crítico":
        # Alerta Vermelho dinâmico
        st.error(f"🔴 Reservatório Sul: {nivel_sul}% (Crítico)")
    else:
        st.success(f"🟢 Reservatório Sul: {nivel_sul}% (Normal)")
    st.metric(label="Capacidade Sul", value=f"{nivel_sul}%", delta="-5% desde ontem" if status_sul == "Crítico" else "Estável")

with col2:
    st.success("🟢 Reservatório Norte: 75% (Normal)")
    st.metric(label="Capacidade Norte", value="75%", delta="0% (Estável)")

with col3:
    if "Severa" in clima_previsao or "Tempestade" in clima_previsao:
        st.warning(f"⚠️ Clima: {clima_previsao}")
    else:
        st.info(f"☀️ Clima: {clima_previsao}")

st.markdown("---")

# --- 3. INTERFACE DE COMPLEMENTARIDADE: O AGENTE DE IA (Linha Inferior) ---
st.subheader("🤖 Assistente de Engenharia e Tomada de Decisão")
st.caption("Faça perguntas ao agente para analisar os dados acima e sugerir planos de ação.")

# Inicializa o histórico do chat interno se não existir
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe o chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de texto para o operador conversar com o agente
if pergunta := st.chat_input("Ex: Baseado nas anomalias acima, qual o plano de contingência imediato?"):
    st.session_state.messages.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        with st.spinner("Llama 3.3 analisando telemetria e gerando parecer..."):
            try:
                # Envia a pergunta para o seu backend FastAPI
                response = requests.post("http://localhost:8000/perguntar", json={"pergunta": pergunta})
                resposta_agente = response.json()["resposta"]
                st.markdown(resposta_agente)
                st.session_state.messages.append({"role": "assistant", "content": resposta_agente})
            except Exception as e:
                st.error("Erro ao conectar ao agente orquestrador.")