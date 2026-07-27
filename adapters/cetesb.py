import sys
import os
import io
import uuid
import pandas as pd
from datetime import datetime, timezone

# Garante a importação dos módulos do projeto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schema.models import TelemetriaUnificada, FonteOrigem, QualityFlag
from db.database import get_connection

def parse_cetesb_raw_text(raw_text: str, station_id: str = "BR-SP-CETESB_001") -> list[TelemetriaUnificada]:
    """
    Recebe o texto bruto/tabulado da CETESB (InfoÁguas) e converte 
    para a lista de objetos do Modelo Canônico.
    """
    # 1. Limpa linhas e remove cabeçalhos de texto livre
    lines = [line.strip() for line in raw_text.strip().split('\n') if line.strip()]
    data_lines = []
    
    for line in lines:
        if line.startswith("Entidade responsável:") or line.startswith("Relatório"):
            continue
        data_lines.append(line)
        
    cleaned_data = "\n".join(data_lines)
    
    # 2. Carrega no Pandas usando Tabulação/Múltiplos espaços como separador
    df = pd.read_csv(io.StringIO(cleaned_data), sep=r'\t+|\s{2,}', engine='python')
    
    # Normaliza nomes de colunas removendo espaços extras
    df.columns = [c.strip() for c in df.columns]
    
    records = []
    
    for _, row in df.iterrows():
        # Função auxiliar para converter strings numéricas com vírgula para float
        def clean_float(val):
            if pd.isna(val) or val == "" or str(val).strip() == "":
                return None
            try:
                # Trata casos em que o valor vem com sinal de igual ou limite de detecção ex: "= 27,02" ou "< 0,5"
                v_str = str(val).replace('=', '').replace('<', '').replace('>', '').strip()
                return float(v_str.replace(',', '.'))
            except ValueError:
                return None

        # Converte DataHora (tentando diferentes formatos de data comuns nos exportáveis)
        dt_str = str(row.get('Data hora', row.get('DataHora', row.get('DataColeta', '')))).strip()
        timestamp = None
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                timestamp = datetime.strptime(dt_str, fmt)
                break
            except ValueError:
                continue
                
        if timestamp is None:
            continue  # Pula se a data não for válida ou estiver ausente
            
        ph_val = clean_float(row.get('pH', row.get('pH (pH)', None)))
        od_val = clean_float(row.get('Oxigênio Dissolvido (mg/L)', row.get('OD (mg/L)', None)))
        cond_val = clean_float(row.get('Condutividade Elétrica (µS/cm)', row.get('Condutividade (µS/cm)', None)))
        turb_val = clean_float(row.get('Turbidez (NTU)', row.get('Turbidez (UNT)', None)))
        temp_val = clean_float(row.get('Temperatura (°C)', row.get('Temperatura da Água (°C)', None)))
        
        # Qualifica o registro
        flag = QualityFlag.VALIDO
        if od_val is None or ph_val is None:
            flag = QualityFlag.SUSPEITO  # Dado incompleto vindo da estação
            
        rec = TelemetriaUnificada(
            observation_id=str(uuid.uuid4()),
            station_id=station_id,
            timestamp=timestamp,
            ph=ph_val,
            oxigenio_dissolvido_mg_l=od_val,
            condutividade_us_cm=cond_val,
            turbidez_unt=turb_val,
            temperatura_agua_c=temp_val,
            quality_flag=flag,
            ingestion_timestamp=datetime.now(timezone.utc)
        )
        records.append(rec)
        
    return records


def save_telemetry_to_db(records: list[TelemetriaUnificada]):
    """Insere os registros convertidos na tabela telemetria_unificada do SQLite."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Garante que a estação exista na tabela de estações
    if records:
        st_id = records[0].station_id
        cursor.execute('''
            INSERT OR IGNORE INTO estacoes (station_id, fonte_origem, nome)
            VALUES (?, ?, ?)
        ''', (st_id, FonteOrigem.CETESB.value, "Estação de Monitoramento CETESB"))
    
    for r in records:
        cursor.execute('''
            INSERT OR REPLACE INTO telemetria_unificada (
                observation_id, station_id, timestamp, ph, turbidez_unt,
                oxigenio_dissolvido_mg_l, condutividade_us_cm, temperatura_agua_c,
                quality_flag, ingestion_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            r.observation_id, r.station_id, r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            r.ph, r.turbidez_unt, r.oxigenio_dissolvido_mg_l, r.condutividade_us_cm,
            r.temperatura_agua_c, r.quality_flag.value, r.ingestion_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ))
        
    conn.commit()
    conn.close()
    print(f"[✓] {len(records)} registros da CETESB ingeridos e padronizados com sucesso!")


# TESTE RÁPIDO DO ADAPTER COM EXEMPLO DE TEXTO BRUTO:
if __name__ == "__main__":
    raw_cetesb_sample = """
Entidade responsável: CETESB | Dados do Ponto de Amostragem
Data hora   pH  Oxigênio Dissolvido (mg/L)  Condutividade Elétrica (µS/cm)  Turbidez (NTU)  Temperatura (°C)
24/07/2026 11:00    7,10    4,88    320,5   12,4    21,2
24/07/2026 12:00    7,05    4,75    322,0   13,1    21,5
24/07/2026 13:00    6,98    4,60    325,1   15,0    21,8
"""
    registros = parse_cetesb_raw_text(raw_cetesb_sample)
    save_telemetry_to_db(registros)