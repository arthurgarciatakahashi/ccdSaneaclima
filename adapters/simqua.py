import sys
import os
import io
import uuid
import pandas as pd
from datetime import datetime, timezone

# Garante a importação dos módulos do projeto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schema.models import TelemetriaUnificada, FonteOrigem, QualityFlag, EstacaoMonitoramento
from db.database import get_connection

def parse_simqua_raw_text(raw_text: str, station_id: str = "BR-SP-CETESB-SIMQUA_001") -> list[TelemetriaUnificada]:
    """
    Recebe o texto bruto copiado do SIMQUA/CETESB ou lido de arquivo
    e converte para a lista de objetos do Modelo Canônico.
    """
    # 1. Encontra o início dos dados ignorando cabeçalhos de texto livre
    lines = [line.strip() for line in raw_text.strip().split('\n') if line.strip()]
    data_lines = []
    
    for line in lines:
        if line.startswith("Entidade responsável:"):
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
                return float(str(val).replace(',', '.'))
            except ValueError:
                return None

        # Converte DataHora (DD/MM/YYYY HH:MM)
        dt_str = str(row.get('Data hora', '')).strip()
        try:
            timestamp = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
        except ValueError:
            continue # Pula se a data não for válida
            
        ph_val = clean_float(row.get('pH'))
        od_val = clean_float(row.get('Oxigênio Dissolvido (mg/L)'))
        cond_val = clean_float(row.get('Condutividade Elétrica (µS/cm)'))
        turb_val = clean_float(row.get('Turbidez (NTU)'))
        temp_val = clean_float(row.get('Temperatura (°C)'))
        
        # Qualifica o registro
        flag = QualityFlag.VALIDO
        if od_val is None or ph_val is None:
            flag = QualityFlag.SUSPEITO # Dado incompleto vindo da estação
            
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
        ''', (st_id, FonteOrigem.SIMQUA.value, "Estação Automática CETESB - SIMQUA"))
    
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
    print(f"[✓] {len(records)} registros do SIMQUA ingeridos e padronizados com sucesso!")


# TESTE RÁPIDO DO ADAPTER COM A TABELA QUE VOCÊ MANDOU:
if __name__ == "__main__":
    raw_simqua_sample = """
Entidade responsável: CETESB | Dados validados até 21/07/2026 00:55					
Data hora	pH	Oxigênio Dissolvido (mg/L)	Condutividade Elétrica (µS/cm)	Turbidez (NTU)	Temperatura (°C)
24/07/2026 11:00	6,23	0	37,1	6,73	17,61
24/07/2026 12:00	6,25	0	37,48	6,6	17,64
24/07/2026 13:00	6,25		37,51	7,49	17,63
24/07/2026 14:00	6,25		37,28	7,9	17,61
24/07/2026 15:00	6,27		36,95	7,91	17,59
"""
    registros = parse_simqua_raw_text(raw_simqua_sample)
    save_telemetry_to_db(registros)