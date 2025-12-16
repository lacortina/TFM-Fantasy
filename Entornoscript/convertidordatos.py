import pandas as pd
import numpy as np
import os


# =========================================
#   FUNCIONES AUXILIARES
# =========================================
def limpiar_jornada(x):
    """Convierte 'Jornada X' → X (int)"""
    if isinstance(x, str):
        return int(x.replace("Jornada", "").replace(".", "").strip())
    return int(x)


def resultado_partido(row):
    if row["goles_marcados"] > row["goles_encajados"]:
        return "V"
    elif row["goles_marcados"] < row["goles_encajados"]:
        return "D"
    else:
        return "E"


def agregar_rachas(df, stats_cols, N=3):
    """
    Añade columnas de racha (media de los últimos N partidos) para cada estadística.
    """
    df = df.copy()

    for col in stats_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

        df[f"{col}_racha"] = (
            df.groupby("equipo")[col]
            .transform(lambda x: x.shift().rolling(window=N, min_periods=1).mean())
        )

    return df


# =========================================
#   MAIN SCRIPT
# =========================================
def main():

    ruta = "./"
    os.makedirs(ruta, exist_ok=True)

    # ============================
    # 1. Cargar data
    # ============================
    players = pd.read_csv(ruta + "players_stats.csv")
    resultados = pd.read_csv(ruta + "resultados_partidos.csv")
    stats = pd.read_csv(ruta + "team_stats.csv")

    # ============================
    # 1.5 Eliminar partidos no jugados
    # ============================
    mask_jugados = resultados["resultado"].str.match(
        r"^\s*\d+\s*:\s*\d+\s*$", na=False
    )

    resultados = resultados[mask_jugados].copy()


    # ============================
    # 2. Normalizar jornadas
    # ============================
    resultados["jornada"] = resultados["jornada"].apply(limpiar_jornada)
    stats["jornada"] = stats["jornada"].apply(limpiar_jornada)

    stats = stats.merge(
    resultados[["jornada", "local", "visitante"]],
    on=["jornada", "local", "visitante"],
    how="inner"
    )


    # ============================
    # 3. Dividir resultado 'x:y'
    # ============================
    resultados[["goles_local", "goles_visitante"]] = (
        resultados["resultado"].str.split(":", expand=True).astype(int)
    )

    # ============================
    # 4. Pivotar stats
    # ============================
    stats_local = stats.pivot_table(
        index=["jornada", "local", "visitante"],
        columns="stat",
        values="valor_local",
    ).add_suffix("_local")

    stats_visit = stats.pivot_table(
        index=["jornada", "local", "visitante"],
        columns="stat",
        values="valor_visitante",
    ).add_suffix("_visitante")

    stats_pivot = pd.concat([stats_local, stats_visit], axis=1).reset_index()

    # ============================
    # 5. Crear df por equipo–jornada
    # ============================
    local_df = resultados.assign(
        equipo=resultados["local"],
        es_visitante=0,
        goles_marcados=resultados["goles_local"],
        goles_encajados=resultados["goles_visitante"],
    )[
        [
            "jornada",
            "equipo",
            "es_visitante",
            "goles_marcados",
            "goles_encajados",
        ]
    ]

    visit_df = resultados.assign(
        equipo=resultados["visitante"],
        es_visitante=1,
        goles_marcados=resultados["goles_visitante"],
        goles_encajados=resultados["goles_local"],
    )[
        [
            "jornada",
            "equipo",
            "es_visitante",
            "goles_marcados",
            "goles_encajados",
        ]
    ]

    equipos_jornadas = pd.concat([local_df, visit_df], ignore_index=True)

    # Resultado y marcas binarias
    equipos_jornadas["resultado"] = equipos_jornadas.apply(
        resultado_partido, axis=1
    )
    equipos_jornadas["victoria"] = (equipos_jornadas["resultado"] == "V").astype(
        int
    )
    equipos_jornadas["empate"] = (equipos_jornadas["resultado"] == "E").astype(int)
    equipos_jornadas["derrota"] = (equipos_jornadas["resultado"] == "D").astype(
        int
    )

    # Ordenar antes de acumulados
    equipos_jornadas = equipos_jornadas.sort_values(["equipo", "jornada"])

    # Acumulados
    equipos_jornadas["goles_marcados_tot"] = equipos_jornadas.groupby("equipo")[
        "goles_marcados"
    ].cumsum()
    equipos_jornadas["goles_encajados_tot"] = equipos_jornadas.groupby("equipo")[
        "goles_encajados"
    ].cumsum()
    equipos_jornadas["victorias_tot"] = equipos_jornadas.groupby("equipo")[
        "victoria"
    ].cumsum()
    equipos_jornadas["empates_tot"] = equipos_jornadas.groupby("equipo")[
        "empate"
    ].cumsum()
    equipos_jornadas["derrotas_tot"] = equipos_jornadas.groupby("equipo")[
        "derrota"
    ].cumsum()

    # Partidos jugados
    equipos_jornadas["partidos_jugados"] = (
        equipos_jornadas.groupby("equipo").cumcount() + 1
    )

    # Promedios básicos
    equipos_jornadas["goles_marcados_pp"] = (
        equipos_jornadas["goles_marcados_tot"]
        / equipos_jornadas["partidos_jugados"]
    )
    equipos_jornadas["goles_encajados_pp"] = (
        equipos_jornadas["goles_encajados_tot"]
        / equipos_jornadas["partidos_jugados"]
    )
    equipos_jornadas["victorias_pp"] = (
        equipos_jornadas["victorias_tot"] / equipos_jornadas["partidos_jugados"]
    )
    equipos_jornadas["empates_pp"] = (
        equipos_jornadas["empates_tot"] / equipos_jornadas["partidos_jugados"]
    )
    equipos_jornadas["derrotas_pp"] = (
        equipos_jornadas["derrotas_tot"] / equipos_jornadas["partidos_jugados"]
    )

    # ============================
    # 6. Añadir stats partido a partido
    # ============================
    stats_cols_local = [
        "Amarillo_local",
        "Amarillo-Rojo_local",
        "Córners_local",
        "Duelos_local",
        "Faltas cometidas_local",
        "Fuera de juego_local",
        "Pases exitosos_local",
        "Pases ges._local",
        "Posesión de balón en %_local",
        "Rojo_local",
        "Tiros a puerta_local",
    ]

    stats_cols_visitante = [
        c.replace("_local", "_visitante") for c in stats_cols_local
    ]

    def obtener_stats(row):
        jornada = row["jornada"]
        equipo = row["equipo"]
        es_visitante = row["es_visitante"]

        partido = stats_pivot[
            (stats_pivot["jornada"] == jornada)
            & (
                (stats_pivot["local"] == equipo)
                | (stats_pivot["visitante"] == equipo)
            )
        ]

        if partido.empty:
            return pd.Series({col: None for col in stats_cols_local})

        partido = partido.iloc[0]

        if es_visitante == 1:
            datos = partido[stats_cols_visitante]
            datos.index = stats_cols_local
        else:
            datos = partido[stats_cols_local]

        return datos

    equipos_stats = equipos_jornadas.apply(obtener_stats, axis=1)
    equipos_jornadas = pd.concat([equipos_jornadas, equipos_stats], axis=1)

    # ============================
    # 7. Promedios acumulados de stats
    # ============================
    cols_promedio = stats_cols_local

    for col in cols_promedio:
        equipos_jornadas[col] = pd.to_numeric(
            equipos_jornadas[col], errors="coerce"
        )

    for col in cols_promedio:
        equipos_jornadas[f"{col}_pp"] = (
            equipos_jornadas.groupby("equipo")[col]
            .transform(lambda s: s.shift().expanding().mean())
        )

    # ============================
    # 8. Renombrar columnas
    # ============================
    equipos_jornadas = equipos_jornadas.rename(
        columns={"es_visitante": "Localía"}
    )

    cols = stats_cols_local + [c + "_pp" for c in stats_cols_local]
    nuevas = [c.replace("_local_pp", "_pp").replace("_local", "") for c in cols]
    equipos_jornadas.rename(columns=dict(zip(cols, nuevas)), inplace=True)

    # ============================
    # 9. dfequipos
    # ============================
    dfequipos = equipos_jornadas.iloc[
        :, [0, 1, 2, 14, 15, 16, 17, 18, 19, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41]
    ].copy()

    # ============================
    # 10. RACHAS
    # ============================
    stats_cols_racha = [
        "goles_marcados",
        "goles_encajados",
        "victoria",
        "empate",
        "derrota",
        "Amarillo",
        "Amarillo-Rojo",
        "Córners",
        "Duelos",
        "Faltas cometidas",
        "Fuera de juego",
        "Pases exitosos",
        "Pases ges.",
        "Posesión de balón en %",
        "Rojo",
        "Tiros a puerta",
    ]

    equipos_jornadasracha = agregar_rachas(
        equipos_jornadas, stats_cols_racha, N=5
    )

    columnas_seleccionadas = np.r_[0:2, 14:19, 31:58]
    dfequiposracha = equipos_jornadasracha.iloc[
        :, columnas_seleccionadas
    ].copy()
    #s
    # ============================
    # 11. GUARDAR CSV
    # ============================
    dfequipos.to_csv(ruta + "dfequipos.csv", index=False)
    equipos_jornadas.to_csv(ruta + "equipos_jornadas.csv", index=False)

    equipos_jornadasracha.to_csv(ruta + "equipos_jornadasracha.csv", index=False)
    dfequiposracha.to_csv(ruta + "dfequiposracha.csv", index=False)

    print("Archivos generados correctamente en ./24-25/")


if __name__ == "__main__":
    main()
