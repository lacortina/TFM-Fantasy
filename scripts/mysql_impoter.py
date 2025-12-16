import pandas as pd
from sqlalchemy import create_engine
import unicodedata
import re
import sys

#Control de temporada

TEMPORADA = '24-25'

# ============================================================
# 1. CONFIG MYSQL — AJUSTA ESTO
# ============================================================

USER = "root"
PASSWORD = "Perr0d3is"
HOST = "localhost"
DB = "futbol"

engine = create_engine(
    f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}/{DB}?charset=utf8mb4"
)

# ============================================================
# 2. NORMALIZADOR DE COLUMNAS — A PRUEBA DE BOMBA
# ============================================================

def normalize(col):
    if not isinstance(col, str):
        col = str(col)

    col = col.strip()
    col = unicodedata.normalize("NFKD", col)
    col = ''.join(c for c in col if not unicodedata.combining(c))

    col = col.replace("%", "pct")
    col = col.replace("-", "_").replace(".", "_").replace("/", "_")
    col = re.sub(r"\s+", "_", col)
    col = re.sub(r"__+", "_", col)

    return col.lower()

def normalize_df(df):
    df.columns = [normalize(c) for c in df.columns]
    return df

# ============================================================
# 3. CARGA DE CSV + NORMALIZACIÓN
# ============================================================

def load_csv(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    return normalize_df(df)

print("📂 Leyendo CSV...")

players = load_csv("../24-25/players_stats.csv")
team_stats = load_csv("../24-25/team_stats.csv")
resultados = load_csv("../24-25/resultados_partidos.csv")
dfequipos = load_csv("../24-25/dfequipos.csv")
dfequiposracha = load_csv("../24-25/dfequiposracha.csv")

# ============================================================
# 4. NORMALIZAR JORNADAS ("1. Jornada" → 1)
# ============================================================

def limpiar_jornada(x):
    if pd.isna(x):
        return None
    if isinstance(x, str):
        x = re.sub(r"[^\d]", "", x)
    return int(x)

if "jornada" in resultados.columns:
    resultados["jornada"] = resultados["jornada"].apply(limpiar_jornada)

if "jornada" in team_stats.columns:
    team_stats["jornada"] = team_stats["jornada"].apply(limpiar_jornada)

# ============================================================
# 5. RENOMBRADO SEGURO DE COLUMNAS
# ============================================================

rename_common = {
    "amarillo_pp": "amarillo_pp",
    "amarillo_rojo_pp": "amarillo_rojo_pp",
    "corners_pp": "corners_pp",
    "duelos_pp": "duelos_pp",
    "faltas_cometidas_pp": "faltas_cometidas_pp",
    "fuera_de_juego_pp": "fuera_de_juego_pp",
    "pases_exitosos_pp": "pases_exitosos_pp",
    "pases_ges__pp": "pases_ges_pp",
    "posesion_de_balon_en_pct_pp": "posesion_pp",
    "posesion_de_balon_en_pct_racha": "posesion_racha",
    "rojo_pp": "rojo_pp",
    "tiros_a_puerta_pp": "tiros_a_puerta_pp",
}

rename_dfequipos_extra = {"localia": "localia"}

# aplicar renombres
dfequipos.rename(columns=rename_common | rename_dfequipos_extra, inplace=True)

rename_racha = {
    c: normalize(c) for c in dfequiposracha.columns
}

dfequiposracha.rename(columns=rename_common, inplace=True)

# ============================================================
# 6. INSERTAR EQUIPOS
# ============================================================

print("🏷 Insertando equipos...")

equipos_set = (
    set(players["equipo"]) |
    set(resultados["local"]) | set(resultados["visitante"]) |
    set(team_stats["local"]) | set(team_stats["visitante"]) |
    set(dfequipos["equipo"]) | set(dfequiposracha["equipo"])
)

df_equipos = pd.DataFrame({"nombre": sorted(equipos_set)})

try:
    existentes = pd.read_sql("SELECT nombre FROM equipos", engine)
    existentes_set = set(existentes["nombre"])
except:
    existentes_set = set()

nuevos = df_equipos[~df_equipos["nombre"].isin(existentes_set)]

if not nuevos.empty:
    nuevos.to_sql("equipos", engine, if_exists="append", index=False)

equipos_sql = pd.read_sql("SELECT id_equipo, nombre FROM equipos", engine)
map_equipos = dict(zip(equipos_sql["nombre"], equipos_sql["id_equipo"]))

# ============================================================
# 7. INSERTAR STATS DE JUGADORES
# ============================================================

print("👤 Insertando stats_jugador...")

players["id_equipo"] = players["equipo"].map(map_equipos)

stats_jugador = players[[
    "nombre", "id_equipo", "minutos_totales",
    "goles_totales", "partidos_jugados"
]]


stats_jugador.loc[:,"temporada"] = TEMPORADA
stats_jugador.to_sql("stats_jugador", engine, if_exists="append", index=False)

# ============================================================
# 8. INSERTAR PARTIDOS
# ============================================================

print("⚽ Insertando partidos...")

resultados["id_local"] = resultados["local"].map(map_equipos)
resultados["id_visitante"] = resultados["visitante"].map(map_equipos)

# separar goles "x:y"
g = resultados["resultado"].str.split(":", expand=True)
resultados["goles_local"] = g[0].astype(int)
resultados["goles_visitante"] = g[1].astype(int)

# FECHA
resultados["fecha"] = resultados["fecha"].replace("", pd.NA)

partidos = resultados[[
    "jornada", "fecha", "id_local", "id_visitante",
    "goles_local", "goles_visitante", "lineup_url"
]]

partidos.loc[:,"temporada"] = TEMPORADA
partidos.to_sql("partidos", engine, if_exists="append", index=False)

# ============================================================
# 9. INSERTAR STATS DE EQUIPOS POR PARTIDO
# ============================================================

print("📊 Insertando stats_partido_equipo...")

team_stats["id_local"] = team_stats["local"].map(map_equipos)
team_stats["id_visitante"] = team_stats["visitante"].map(map_equipos)

stats_equipo = team_stats[[
    "jornada", "id_local", "id_visitante",
    "stat", "valor_local", "valor_visitante"
]]

stats_equipo.loc[:,"temporada"] = TEMPORADA
stats_equipo.to_sql("stats_partido_equipo", engine, if_exists="append", index=False)

# ============================================================
# 10. INSERTAR DFEQUIPOS
# ============================================================

print("📈 Insertando dfequipos...")

dfequipos["id_equipo"] = dfequipos["equipo"].map(map_equipos)

# columnas reales disponibles
#print(dfequipos.columns)
cols_real = set(dfequipos.columns)

cols_dfequipos = [
    "jornada", "id_equipo", "localia", "partidos_jugados",
    "goles_marcados_pp", "goles_encajados_pp", "victorias_pp",
    "empates_pp", "derrotas_pp", "amarillo_pp", "amarillo_rojo_pp",
    "corners_pp", "duelos_pp", "faltas_cometidas_pp", "fuera_de_juego_pp",
    "pases_exitosos_pp", "pases_ges_pp", "posesion_pp",
    "rojo_pp", "tiros_a_puerta_pp",
]

faltan = [c for c in cols_dfequipos if c not in cols_real]
if faltan:
    print("❌ ERROR: Faltan columnas en dfequipos:", faltan)
    print("Columnas reales:", dfequipos.columns.tolist())
    sys.exit(1)

dfequipos_out = dfequipos[cols_dfequipos]

dfequipos_out.loc[:,"temporada"] = TEMPORADA
dfequipos_out.to_sql("dfequipos", engine, if_exists="append", index=False)

# ============================================================
# 11. INSERTAR DFEQUIPOS_RACHA
# ============================================================

print("🔥 Insertando dfequipos_racha...")

dfequiposracha["id_equipo"] = dfequiposracha["equipo"].map(map_equipos)

cols_real = set(dfequiposracha.columns)

cols_dfequipos_racha = [
    "jornada", "id_equipo", "partidos_jugados",
    "goles_marcados_pp", "goles_encajados_pp", "victorias_pp",
    "empates_pp", "amarillo_pp", "amarillo_rojo_pp", "corners_pp",
    "duelos_pp", "faltas_cometidas_pp", "fuera_de_juego_pp",
    "pases_exitosos_pp", "pases_ges_pp", "posesion_pp",
    "rojo_pp", "tiros_a_puerta_pp",
    "goles_marcados_racha", "goles_encajados_racha",
    "victoria_racha", "empate_racha", "derrota_racha",
    "amarillo_racha", "amarillo_rojo_racha",
    "corners_racha", "duelos_racha", "faltas_cometidas_racha",
    "fuera_de_juego_racha", "pases_exitosos_racha",
    "pases_ges_racha", "posesion_racha",
    "rojo_racha", "tiros_a_puerta_racha",
]

faltan = [c for c in cols_dfequipos_racha if c not in cols_real]
if faltan:
    print("❌ ERROR: Faltan columnas en dfequiposracha:", faltan)
    print("Columnas reales:", dfequiposracha.columns.tolist())
    sys.exit(1)

dfequiposracha_out = dfequiposracha[cols_dfequipos_racha]

dfequiposracha_out.loc[:,"temporada"] = TEMPORADA
dfequiposracha_out.to_sql("dfequiposracha", engine, if_exists="append", index=False)

print("\n✅ IMPORTACIÓN COMPLETADA SIN ERRORES 🎉")
