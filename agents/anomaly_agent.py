import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

# 1. Carregar variáveis de ambiente (.env)
load_dotenv()

# Caminho da base de dados SQLite do Saneaclima
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "saneaclima.db")


# 2. Definir a Ferramenta (Tool) para o Agente
@tool
def consultar_telemetria_recente(estacao_id: str = None) -> str:
    """
    Consulta os últimos registros da tabela 'telemetria_unificada' na base de dados SQLite.
    Pode receber o ID de uma estação específica ou consultar os dados gerais.
    Retorna os dados de vazão, pressão, turbidez, nível e chuva.
    """
    try:
        db_real_path = os.path.abspath(DB_PATH)
        if not os.path.exists(db_real_path):
            return f"Erro: Base de dados não encontrada no caminho '{db_real_path}'."

        conn = sqlite3.connect(db_real_path)
        
        if estacao_id:
            query = """
                SELECT timestamp, estacao_id, vazao_lps, pressao_mca, turbidez_unt, nivel_m, chuva_mm 
                FROM telemetria_unificada 
                WHERE estacao_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 10
            """
            df = pd.read_sql_query(query, conn, params=(estacao_id,))
        else:
            query = """
                SELECT timestamp, estacao_id, vazao_lps, pressao_mca, turbidez_unt, nivel_m, chuva_mm 
                FROM telemetria_unificada 
                ORDER BY timestamp DESC 
                LIMIT 15
            """
            df = pd.read_sql_query(query, conn)
            
        conn.close()

        if df.empty:
            return "Nenhum dado de telemetria foi encontrado na base de dados."

        return df.to_string(index=False)

    except Exception as e:
        return f"Erro ao consultar a base de dados: {str(e)}"


# 3. Função Principal de Análise
def analisar_estacao_com_agente(estacao_id: str = None) -> str:
    """
    Orquestra a análise agêntica de anomalias na telemetria usando Tool Calling nativo da OpenAI.
    """
    if not os.getenv("OPENAI_API_KEY"):
        return "⚠️ Erro: A variável 'OPENAI_API_KEY' não foi encontrada no arquivo .env."

    # Mapeamento de ferramentas disponíveis
    tools_map = {"consultar_telemetria_recente": consultar_telemetria_recente}

    # Inicializa LLM com suporte nativo a ferramentas
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    llm_with_tools = llm.bind_tools([consultar_telemetria_recente])

    # Prompt do Sistema
    sys_prompt = SystemMessage(
        content="""Você é o Agente Especialista em Análise de Anomalias do ecossistema Saneaclima (CCD Saneamento e Resiliência Climática).
Sua função é monitorar dados de telemetria IoT (vazão, pressão, turbidez, nível de reservatório e chuva) e identificar potenciais falhas operacionais ou eventos climáticos extremos.

Instruções:
1. Sempre consulte os dados mais recentes usando a ferramenta 'consultar_telemetria_recente'.
2. Analise os dados retornados em busca de anomalias (picos de turbidez, quedas bruscas de pressão, variações fora do padrão ou chuva intensa).
3. Forneça um relatório diagnóstico detalhado em linguagem natural para o operador, identificando a causa provável e sugerindo ações corretivas."""
    )

    if estacao_id:
        user_input = f"Execute uma análise diagnóstica completa nos últimos dados da estação '{estacao_id}' e verifique se há anomalias."
    else:
        user_input = "Execute uma análise diagnóstica completa nos últimos dados de telemetria recebidos e verifique se há anomalias nas estações."

    messages = [sys_prompt, HumanMessage(content=user_input)]

    try:
        # 1ª Rodada: LLM decide chamar a tool
        ai_msg = llm_with_tools.invoke(messages)
        messages.append(ai_msg)

        # Se o modelo decidiu chamar uma ferramenta
        if ai_msg.tool_calls:
            for tool_call in ai_msg.tool_calls:
                selected_tool = tools_map.get(tool_call["name"])
                if selected_tool:
                    # Executa a tool
                    tool_output = selected_tool.invoke(tool_call["args"])
                    # Adiciona a resposta da tool na conversa
                    messages.append(
                        ToolMessage(
                            content=str(tool_output),
                            tool_call_id=tool_call["id"]
                        )
                    )

            # 2ª Rodada: LLM analisa o resultado da tool e dá o parecer final
            final_response = llm_with_tools.invoke(messages)
            return final_response.content
        else:
            return ai_msg.content

    except Exception as e:
        return f"Erro durante a execução do agente: {str(e)}"


if __name__ == "__main__":
    print("🤖 Testando a execução direta do Agente de Anomalias...")
    resultado = analisar_estacao_com_agente()
    print("\n--- Resultado do Diagnóstico ---")
    print(resultado)