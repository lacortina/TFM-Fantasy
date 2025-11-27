import pandas as pd

# Cargar CSVs
df_partidos = pd.read_csv("./24-25/resultados_partidos.csv")
df_stats = pd.read_csv("./24-25/team_stats.csv")

# --------------------------
# 1) Normalizar resultados
# --------------------------
def obtener_resultado(goles_local, goles_visitante, es_local):
    if goles_local > goles_visitante:
        return 1 if es_local else 0  # victoria o derrota
    elif goles_local < goles_visitante:
        return 0 if es_local else 1  # derrota o victoria
    else:
        return 2  # empate

# --------------------------
# 2) Obtener lista de equipos
# --------------------------
equipos_unicos = sorted(
    set(df_partidos["local"].unique()).union(
        df_partidos["visitante"].unique()
    )
)

equipos = {}  # dict final donde guardamos DF por equipo

# --------------------------
# 3) Procesar cada equipo
# --------------------------
for equipo in equipos_unicos:

    registros_equipo = []

    df_local = df_partidos[df_partidos["local"] == equipo]
    df_visitante = df_partidos[df_partidos["visitante"] == equipo]

    df_equipo_partidos = pd.concat([df_local, df_visitante])

    for _, row in df_equipo_partidos.iterrows():

        jornada = row["jornada"]
        es_local = 0 if row["local"] == equipo else 1

        goles_local, goles_visitante = map(int, row["resultado"].split(":"))
        if es_local == 0:
            gm, ge = goles_local, goles_visitante
        else:
            gm, ge = goles_visitante, goles_local

        # Calcular V/E/D
        res = obtener_resultado(goles_local, goles_visitante, es_local)

        victoria = 1 if res == 1 else 0
        derrota = 1 if res == 0 else 0
        empate = 1 if res == 2 else 0

        # ---- TEAM STATISTICS ----
        df_stats_partido = df_stats[
            (df_stats["jornada"] == jornada) &
            ((df_stats["local"] == equipo) | (df_stats["visitante"] == equipo))
        ]

        def obtener_stat(nombre_stat):
            fila = df_stats_partido[df_stats_partido["stat"] == nombre_stat]
            if fila.empty:
                return None
            return (
                fila["valor_local"].iloc[0] if es_local == 0 else fila["valor_visitante"].iloc[0]
            )

        # Extraer estadísticas clave
        duelos = obtener_stat("Duelos ganados")
        posesion = obtener_stat("Posesión del balón")
        tiros_puerta = obtener_stat("Tiros a puerta")
        pases = obtener_stat("Pases")
        pases_ex = obtener_stat("Pases exitosos")
        corners = obtener_stat("Córners")
        faltas = obtener_stat("Faltas cometidas")
        fuera_juego = obtener_stat("Fuera de juego")
        amarillo = obtener_stat("Tarjetas amarillas")
        amar_roj = obtener_stat("Tarjetas amarillas-rojas")
        rojo = obtener_stat("Tarjetas rojas")

        registros_equipo.append({
            "jornada": jornada,
            "partidos": 1,
            "victorias": victoria,
            "empates": empate,
            "derrotas": derrota,
            "goles_marcados": gm,
            "goles_encajados": ge,
            "duelos_ganados": duelos,
            "posesion": posesion,
            "tiros_puerta": tiros_puerta,
            "pases": pases,
            "pases_exitosos": pases_ex,
            "corners": corners,
            "faltas": faltas,
            "fuera_juego": fuera_juego,
            "amarillos": amarillo,
            "amarillo_rojo": amar_roj,
            "rojo": rojo,
            "local_visitante": es_local
        })

    equipos[equipo] = pd.DataFrame(registros_equipo).sort_values("jornada")
