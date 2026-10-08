import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")  # Sin valor por defecto: se define en .env (ver .env.example)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "solarbi")

if not DB_PASS:
    raise RuntimeError("Falta DB_PASS: crea un archivo .env en la raíz a partir de .env.example")

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def run_pipeline():
    print("--- INICIANDO PIPELINE ETL ---")
    bronze_path = "data/bronze/telemetria.csv"
    if not os.path.exists(bronze_path):
        raise FileNotFoundError("Ejecuta primero simulador.py")

    df = pd.read_csv(bronze_path)
    total_filas = len(df)

    # Reglas de Calidad (cada regla reporta cuántas filas rechaza)
    rechazos = {}

    # R1: duplicados exactos
    n_antes = len(df)
    df_clean = df.drop_duplicates()
    rechazos["duplicados"] = n_antes - len(df_clean)

    # R2: datos faltantes en irradiancia
    n_antes = len(df_clean)
    df_clean = df_clean.dropna(subset=['irradiancia_wm2'])
    rechazos["faltantes"] = n_antes - len(df_clean)

    # R3: rango físico de potencia (>= 0 kW) e irradiancia (0 a 1500 W/m2)
    n_antes = len(df_clean)
    mascara_fisica = (df_clean['p_ac_kw'] >= 0) & (df_clean['irradiancia_wm2'].between(0, 1500))
    df_clean = df_clean[mascara_fisica]
    rechazos["fuera_de_rango"] = n_antes - len(df_clean)

    filas_validas = len(df_clean)
    pct_validos = round((filas_validas / total_filas) * 100, 2)

    print(f"Filas Leídas: {total_filas} | Válidas: {filas_validas} ({pct_validos}%)")
    for regla, n in rechazos.items():
        print(f"  Rechazadas por {regla}: {n}")

    # Guardar en Silver local
    os.makedirs("data/silver", exist_ok=True)
    df_clean.to_csv("data/silver/telemetria_limpia.csv", index=False)

    # Carga Idempotente a PostgreSQL - Silver (lectura_5min)
    with engine.begin() as conn:
        for _, row in df_clean.iterrows():
            stmt = text("""
                INSERT INTO silver.lectura_5min (ts, dispositivo_id, p_ac_kw, irradiancia_wm2, temp_modulo_c)
                VALUES (:ts, :disp, :pac, :irr, :temp)
                ON CONFLICT (ts) DO UPDATE SET
                    p_ac_kw = EXCLUDED.p_ac_kw,
                    irradiancia_wm2 = EXCLUDED.irradiancia_wm2,
                    temp_modulo_c = EXCLUDED.temp_modulo_c;
            """)
            conn.execute(stmt, {
                "ts": row['ts'], "disp": int(row['dispositivo_id']),
                "pac": float(row['p_ac_kw']), "irr": float(row['irradiancia_wm2']),
                "temp": float(row['temp_modulo_c'])
            })

    # Transformación a Gold (Cálculo diario)
    df_clean['fecha'] = pd.to_datetime(df_clean['ts']).dt.date
    df_clean['energia_intervalo_kwh'] = df_clean['p_ac_kw'] * (5.0 / 60.0)

    gold_df = df_clean.groupby(['fecha', 'dispositivo_id']).agg(
        energia_kwh=('energia_intervalo_kwh', 'sum')
    ).reset_index()
    gold_df['pct_datos_validos'] = pct_validos

    # Carga Idempotente a PostgreSQL - Gold (fact_energia_dia)
    with engine.begin() as conn:
        for _, row in gold_df.iterrows():
            stmt = text("""
                INSERT INTO dwh.fact_energia_dia (fecha, dispositivo_key, energia_kwh, pct_datos_validos)
                VALUES (:fecha, :disp, :energia, :pct)
                ON CONFLICT (fecha, dispositivo_key) DO UPDATE SET
                    energia_kwh = EXCLUDED.energia_kwh,
                    pct_datos_validos = EXCLUDED.pct_datos_validos;
            """)
            conn.execute(stmt, {
                "fecha": row['fecha'], "disp": int(row['dispositivo_id']),
                "energia": float(row['energia_kwh']), "pct": float(row['pct_datos_validos'])
            })

    print("--- PIPELINE COMPLETADO EXITOSAMENTE ---")

if __name__ == "__main__":
    run_pipeline()
