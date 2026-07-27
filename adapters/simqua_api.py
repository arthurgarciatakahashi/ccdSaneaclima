import sys
import os
import io
import uuid
import requests
import pandas as pd
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schema.models import TelemetriaUnificada, FonteOrigem, QualityFlag
from db.database import get_connection

# Reaproveitamos sua função de parsing exata!
def parse_simqua_raw_text(raw_text: str, station_id: str = "BR-SP-CETESB-SIMQUA_001") -> list[TelemetriaUnificada]:
    lines = [line.strip() for line in raw_text.strip().split('\n') if line.strip()]
    data_lines = [line for line in lines if not line.startswith("Entidade responsável:")]
    
    cleaned_data = "\n".join(data_lines)
    df = pd.read_csv(io.StringIO(cleaned_data), sep=r'\t+|\s{2,}', engine='python')
    df.columns = [c.strip() for c in df.columns]
    
    records = []
    for _, row in df.iterrows():
        def clean_float(val):
            if pd.isna(val) or val == "" or str(val).strip() == "":
                return None
            try:
                return float(str(val).replace(',', '.'))
            except ValueError:
                return None

        dt_str = str(row.get('Data hora', '')).strip()
        try:
            timestamp = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
        except ValueError:
            continue
            
        ph_val = clean_float(row.get('pH'))
        od_val = clean_float(row.get('Oxigênio Dissolvido (mg/L)'))
        cond_val = clean_float(row.get('Condutividade Elétrica (µS/cm)'))
        turb_val = clean_float(row.get('Turbidez (NTU)'))
        temp_val = clean_float(row.get('Temperatura (°C)'))
        
        flag = QualityFlag.VALIDO
        if od_val is None or ph_val is None:
            flag = QualityFlag.SUSPEITO
            
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


def fetch_simqua_data_api(codigo_estacao: str = "BR-SP-CETESB-SIMQUA_001") -> list[TelemetriaUnificada]:
    """Busca os dados mais recentes via requisição HTTP/API do portal SIMQUA."""
    # Endpoint interno/consulta REST do SIMQUA (Ajuste a URL exata da estação do seu teste)
    url = "https://simqua.cetesb.sp.gov.br/api/dados_recentes" # Exemplo de rota REST
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Se o endpoint retornar JSON direto:
        # data = response.json()
        # return parse_simqua_json(data)
        
        # Se o endpoint retornar texto/HTML formatado:
        return parse_simqua_raw_text(response.text, station_id=codigo_estacao)
        
    except Exception as e:
        print(f"[!] Erro ao buscar dados na API do SIMQUA: {e}")
        return []


def save_telemetry_to_db(records: list[TelemetriaUnificada]):
    conn = get_connection()
    cursor = conn.cursor()
    
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


if __name__ == "__main__":
    # Teste consumindo via HTTP/API
    registros = fetch_simqua_data_api()
    if registros:
        save_telemetry_to_db(registros)