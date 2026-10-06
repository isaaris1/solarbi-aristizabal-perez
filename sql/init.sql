CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS dwh;

CREATE TABLE IF NOT EXISTS silver.lectura_5min (
    ts TIMESTAMP PRIMARY KEY,
    dispositivo_id INT,
    p_ac_kw NUMERIC,
    irradiancia_wm2 NUMERIC,
    temp_modulo_c NUMERIC
);

CREATE TABLE IF NOT EXISTS dwh.fact_energia_dia (
    fecha DATE,
    dispositivo_key INT,
    energia_kwh NUMERIC,
    pct_datos_validos NUMERIC,
    PRIMARY KEY (fecha, dispositivo_key)
);
