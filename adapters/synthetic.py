import sys
import os
import uuid
import random
import math
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schema.models import TelemetriaUnificada, FonteOrigem, QualityFlag, EstacaoMonitoramento
from db.database import get_connection

def generate_synthetic_telemetry(days: int = 3, station_id: str = "PCD_SINTETICA_001") -> list[TelemetriaUnificada]:
    """
    Gera uma série temporal sintética de sensores com padrão diário
    e injeção ocasional de chuva e anomalias operacionais.
    """
    records = []
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    current_time = start_time
    
    while current_time <= end_time:
        hour = current_time.hour
        
        # Padrão diário de temperatura do ar
        temp_ar = round(20 + 5 * math.sin(math.pi * (hour - 8) / 12) + random.uniform(-0.5, 0.5), 2)
        
        # Ocorrência de chuva (15% de probabilidade)
        is_raining = random.random() < 0.15
        precip = round(random.uniform(2.0, 25.0), 2) if is_raining else 0.0
        
        # Valores de base para qualidade da água
        ph = round(7.2 + random.uniform(-0.1, 0.1), 2)
        od = round(7.5 - (temp_ar - 20) * 0.1 + random.uniform(-0.2, 0.2), 2)
        condutividade = round(250 + random.uniform(-5, 5), 1)
        temp_agua = round(temp_ar - 2.0 + random.uniform(-0.3, 0.3), 2)
        
        # Turbidez aumenta com chuva (arraste de sedimentos)
        if is_raining:
            turbidez = round(random.uniform(25.0, 110.0), 2)
            ph = round(ph - 0.2, 2)
        else:
            turbidez = round(random.uniform(3.0, 10.0), 2)
            
        quality = QualityFlag.VALIDO
        
        # Injeção de anomalia (3% de probabilidade)
        if random.random() < 0.03:
            quality = QualityFlag.ANOMALIA
            condutividade = round(condutividade * 3.0, 1) # Pico de efluente
            ph = round(ph - 1.5, 2)

        rec = TelemetriaUnificada(
            observation_id=str(uuid.uuid4()),
            station_id=station_id,
            timestamp=current_time,
            ph=ph,
            turbidez_unt=turbidez,
            oxigenio_dissolvido_mg_l=od,
            condutividade_us_cm=condutividade,
            temperatura_agua_c=temp_agua,
            precipitacao_mm=precip,
            temperatura_ar_c=temp_ar,
            quality_flag=quality,
            ingestion_timestamp=datetime.now(timezone.utc)
        )
        records.append(rec)
        current_time += timedelta(minutes=15)
        
    return records

def save_synthetic_to_db(records: list[TelemetriaUnificada]):
    conn = get_connection()
    cursor = conn.cursor()
    
    if records:
        st_id = records[0].station_id
        cursor.execute('''
            INSERT OR IGNORE INTO estacoes (station_id, fonte_origem, nome)
            VALUES (?, ?, ?)
        ''', (st_id, FonteOrigem.SINTETICO.value, "Simulador de Sensores - Saneaclima"))
    
    for r in records:
        cursor.execute('''
            INSERT OR REPLACE INTO telemetria_unificada (
                observation_id, station_id, timestamp, ph, turbidez_unt,
                oxigenio_dissolvido_mg_l, condutividade_us_cm, temperatura_agua_c,
                precipitacao_mm, temperatura_ar_c, quality_flag, ingestion_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            r.observation_id, r.station_id, r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            r.ph, r.turbidez_unt, r.oxigenio_dissolvido_mg_l, r.condutividade_us_cm,
            r.temperatura_agua_c, r.precipitacao_mm, r.temperatura_ar_c,
            r.quality_flag.value, r.ingestion_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ))
        
    conn.commit()
    conn.close()
    print(f"[✓] {len(records)} registros sintéticos inseridos no banco com sucesso!")

if __name__ == "__main__":
    sinteticos = generate_synthetic_telemetry(days=3)
    save_synthetic_to_db(sinteticos)