from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class FonteOrigem(str, Enum):
    SINTETICO = "SINTETICO"
    SIMQUA = "SIMQUA_CETESB"
    CEMADEN = "CEMADEN"
    INMET = "INMET"
    CETESB = "CETESB"

class QualityFlag(str, Enum):
    VALIDO = "VALIDO"
    SUSPEITO = "SUSPEITO"
    ANOMALIA = "ANOMALIA"
    FALHA_SENSOR = "FALHA_SENSOR"

@dataclass
class EstacaoMonitoramento:
    """Representa a localização/ponto de medição."""
    station_id: str             # ex: "BR-SP-CETESB-TETE0200" ou "PCD_SIMU_001"
    fonte_origem: FonteOrigem
    nome: str                   # ex: "Rio Tietê - Ponte dos Remédios"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    corpo_hidrico: Optional[str] = None # ex: "Rio Tietê"

@dataclass
class TelemetriaUnificada:
    """Modelo canônico padronizado para qualquer leitura de sensor."""
    observation_id: str         # UUID / Hash do registro
    station_id: str             # Chave estrangeira para a estação
    timestamp: datetime         # UTC
    
    # Parâmetros Hídricos (SIMQUA / Sensores de Água)
    ph: Optional[float] = None                  # Adimensional (0-14)
    turbidez_unt: Optional[float] = None        # UNT
    oxigenio_dissolvido_mg_l: Optional[float] = None # mg/L
    condutividade_us_cm: Optional[float] = None  # µS/cm
    temperatura_agua_c: Optional[float] = None  # °C
    
    # Parâmetros Atmosféricos (CEMADEN / INMET / Chuva)
    precipitacao_mm: Optional[float] = None     # mm
    temperatura_ar_c: Optional[float] = None    # °C
    umidade_relativa: Optional[float] = None    # %
    
    # Metadados de Ingestão e Diagnóstico
    quality_flag: QualityFlag = QualityFlag.VALIDO
    ingestion_timestamp: datetime = datetime.utcnow()