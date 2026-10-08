# SolarBI Trabajo BI

**Asignatura:** Inteligencia de Negocios - Grupo 50

**Integrantes:** Isabella Aristizabal Diaz y Valentina Alejandra Pérez Cardona

**Universidad:** Institución Universitaria Pascual Bravo

**Semestre:** 2026-2 

**Docente:** Ramiro Grisales Montoya

Pipeline Bronze → Silver → Gold sobre telemetría solar simulada (lecturas cada 5 min), cargado de forma constante en PostgreSQL y consumido por Grafana (operación) y Power BI (negocio).

## Estructura

```
solarbi-aristizabal-perez/
├── README.md
├── .gitignore
├── docs/
│   └── informe_consulta.md
├── data/
│   ├── bronze/telemetria.csv
│   └── silver/telemetria_limpia.csv
├── etl/
│   ├── simulador.py
│   └── run_etl.py
├── sql/
│   └── init.sql
├── powerbi/
│   └── dashboard.pbip
└── grafana/
    └── dashboard.json
```

## Pasos de reproducción

Requisitos: Python 3.10+, PostgreSQL, Grafana y Power BI Desktop. Todos los comandos se ejecutan desde la raíz del repositorio.

1. Entorno Python:

   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install pandas sqlalchemy "psycopg[binary]" python-dotenv
   ```

2. Base de datos y esquemas:

   ```bash
   createdb -U postgres solarbi
   psql -U postgres -d solarbi -f sql/init.sql
   ```

3. Credenciales: crear un archivo `.env` en la raíz (no se versiona) con `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT` y `DB_NAME`. Sin `.env` se usan los valores por defecto `postgres` / `localhost` / `5432` / `solarbi`.

4. Generar la capa Bronze (`data/bronze/telemetria.csv`):

   ```bash
   python etl/simulador.py
   ```

5. Ejecutar el pipeline ETL (Silver + Gold, idempotente por `ON CONFLICT`):

   ```bash
   python etl/run_etl.py
   ```

6. Automatización (opcional, cron):

   ```
   0 0 * * * /usr/bin/python3 /ruta/al/proyecto/etl/run_etl.py >> /ruta/al/proyecto/etl/etl.log 2>&1
   ```

7. Grafana: crear el data source PostgreSQL (`localhost:5432`, base `solarbi`) e importar `grafana/dashboard.json` (Dashboards → Import). El rango de tiempo debe cubrir del 2026-10-05 al 2026-10-07.

8. Power BI: conectar Power BI Desktop a PostgreSQL (`localhost:5432/solarbi`) en modo Import, crear el parámetro `TarifaCOP = 800` y las medidas:

   ```DAX
   Total_Energia_kWh = SUM(fact_energia_dia[energia_kwh])
   Yield_kWh_kWp = DIVIDE([Total_Energia_kWh], 5.0, 0)
   Ahorro_COP = [Total_Energia_kWh] * TarifaCOP
   ```

   Guardar como `powerbi/dashboard.pbip`.

## Aportes por integrante

| Integrante | Rol | Aportes |
|---|---|---|
| Pérez | Data Engineer | Estructura inicial del repositorio y README base; esquemas `silver` y `dwh` en `sql/init.sql`; simulador de telemetría y capa Bronze; pipeline ETL idempotente con carga a Silver y Gold. |
| Aristizábal | BI Analyst / Data Modeler | Modelo, medidas DAX y visuales en Power BI; dashboard operativo en Grafana con la variable `$dispositivo`; informe de consulta (Partes A y B); documentación final del README. |

## Documentación

El informe completo 
