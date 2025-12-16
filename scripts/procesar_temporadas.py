import os
import subprocess
import pandas as pd
from scriptssql.mysql_utils import save_df_to_mysql

# ============================
# LISTA DE TEMPORADAS A SCRAPEAR
# ============================
TEMPORADAS = {
    "22_23": "https://www.livefutbol.com/competition/co97/espana-primera-division/se45808/2022-2023/all-matches/",
    "23_24": "https://www.livefutbol.com/competition/co97/espana-primera-division/se52580/2023-2024/all-matches/",
    "24_25": "https://www.livefutbol.com/competition/co97/espana-primera-division/se74771/2024-2025/all-matches/"
}

# ============================
# RUTAS DE SCRIPTS
# ============================
SCRAPER = "scrapper_final.py"
CONVERTIDOR = "convertidordatos.py"

# ============================
# PROCESAR TODAS LAS TEMPORADAS
# ============================
for temporada, url in TEMPORADAS.items():
    print("\n" + "="*80)
    print(f"   📌 INICIANDO TEMPORADA {temporada}")
    print("="*80)

    # 1) Exportar URL para scraper
    os.environ["SEASON_URL"] = url
    os.environ["TEMPORADA"] = temporada

    print("\n▶ Ejecutando scraper_final...")
    subprocess.run(["python", SCRAPER])

    print("\n▶ Ejecutando convertidordatos...")
    subprocess.run(["python", CONVERTIDOR])

    # ============================
    # 2) Guardar CSV en MySQL
    # ============================
    ruta = f"./{temporada}/"

    CSV_LIST = [
        ("players_stats.csv", "players_stats"),
        ("resultados_partidos.csv", "resultados_partidos"),
        ("team_stats.csv", "team_stats"),
        ("dfequipos.csv", "dfequipos"),
        ("equipos_jornadas.csv", "equipos_jornadas"),
        ("equipos_jornadasracha.csv", "equipos_jornadasracha"),
        ("dfequiposracha.csv", "dfequiposracha")
    ]

    print("\n📌 Guardando CSVs en MySQL...")

    for filename, base_name in CSV_LIST:
        csv_path = ruta + filename

        if not os.path.exists(csv_path):
            print(f"⚠ No encontrado → {csv_path}")
            continue

        df = pd.read_csv(csv_path)
        tabla = f"{base_name}_{temporada}"

        save_df_to_mysql(df, tabla)

    print(f"\n✔ TEMPORADA {temporada} COMPLETADA.\n")
