import subprocess
import os
import re

# ===========================
#   CONFIGURACIÓN
# ===========================

urls = [
    "https://www.livefutbol.com/competition/co97/espana-primera-division/se28562/2018-2019/all-matches/",
    "https://www.livefutbol.com/competition/co97/espana-primera-division/se31742/2019-2020/all-matches/",
    "https://www.livefutbol.com/competition/co97/espana-primera-division/se35880/2020-2021/all-matches/",
    "https://www.livefutbol.com/competition/co97/espana-primera-division/se39075/2021-2022/all-matches/",
    "https://www.livefutbol.com/competition/co97/espana-primera-division/se45808/2022-2023/all-matches/",
    "https://www.livefutbol.com/competition/co97/espana-primera-division/se52580/2023-2024/all-matches/",
    "https://www.livefutbol.com/competition/co97/espana-primera-division/se74771/2024-2025/all-matches/",
    "https://www.livefutbol.com/competition/co97/espana-primera-division/se96657/2025-2026/all-matches/"
]

temporadas = [
    "18-19",
    "19-20",
    "20-21",
    "21-22",
    "22-23",
    "23-24",
    "24-25",
    "25-26"
]

# Validación simple
if len(urls) != len(temporadas):
    raise ValueError("La cantidad de URLs debe coincidir con la cantidad de temporadas.")


# ===========================
#   FUNCIONES AUXILIARES
# ===========================

def replace_variable_in_file(file_path, variable_name, new_value):
    """
    Busca la línea variable_name = "..." y la reemplaza por una nueva.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # regex: variable = "cualquier cosa"
    new_content = re.sub(
        rf'{variable_name}\s*=\s*"(.*?)"',
        f'{variable_name} = "{new_value}"',
        content
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)


def ejecutar_script(script):
    print(f"\n▶ Ejecutando {script} ...")
    resultado = subprocess.run(["python", script])
    if resultado.returncode != 0:
        raise RuntimeError(f"❌ El script {script} falló.")


def borrar_csv_generados():
    csv_files = [
        "players_stats.csv", "resultados_partidos.csv", "team_stats.csv",
        "dfequipos.csv", "dfequiposracha.csv",
        "equipos_jornadas.csv", "equipos_jornadasracha.csv"
    ]

    for file in csv_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑 Se borró {file}")


# ===========================
#   BUCLE PRINCIPAL
# ===========================

for url, temporada in zip(urls, temporadas):

    print("\n===================================================")
    print(f"   🚀 PROCESANDO TEMPORADA {temporada}")
    print("===================================================\n")

    # 1) Cambiar la variable SEASON_URL en scrapper_final.py
    replace_variable_in_file("scrapper_final.py", "SEASON_URL", url)

    # 2) Ejecutar scrapper_final.py
    ejecutar_script("scrapper_final.py")

    # 3) Ejecutar convertidordatos.py
    ejecutar_script("convertidordatos.py")

    # 4) Cambiar TEMPORADA en mysql_impoter.py
    replace_variable_in_file("mysql_impoter.py", "TEMPORADA", temporada)

    # 5) Ejecutar mysql_impoter.py
    ejecutar_script("mysql_impoter.py")

    # 6) Borrar CSV generados
    borrar_csv_generados()

    print(f"\n🎉 TEMPORADA {temporada} COMPLETADA CORRECTAMENTE\n")


print("\n===================================================")
print("  ✅ TODAS LAS TEMPORADAS FUERON PROCESADAS")
print("===================================================\n")
