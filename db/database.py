import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "saneaclima.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabela de Estações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estacoes (
            station_id TEXT PRIMARY KEY,
            fonte_origem TEXT NOT NULL,
            nome TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            corpo_hidrico TEXT
        )
    ''')
    
    # Tabela Unificada de Medições de Telemetria
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetria_unificada (
            observation_id TEXT PRIMARY KEY,
            station_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            ph REAL,
            turbidez_unt REAL,
            oxigenio_dissolvido_mg_l REAL,
            condutividade_us_cm REAL,
            temperatura_agua_c REAL,
            precipitacao_mm REAL,
            temperatura_ar_c REAL,
            umidade_relativa REAL,
            quality_flag TEXT NOT NULL,
            ingestion_timestamp DATETIME NOT NULL,
            FOREIGN KEY(station_id) REFERENCES estacoes(station_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

if __name__ == "__main__":
    init_db()
    print("Banco de dados SQLite inicializado com sucesso no esquema canônico!")