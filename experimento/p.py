import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

URL = "https://www.livefutbol.com/match-report/co97/primera-division/ma11222876/girona-fc_rayo-vallecano/lineup/"
DEBUG_FILE = "debug_livefutbol.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}

# ----------------------------------------------------
# 1. DESCARGAR HTML Y GUARDAR COMO debug_livefutbol.html
# ----------------------------------------------------
def descargar_debug_html():
    print("Intentando descargar HTML real...")
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=15)
        with open(DEBUG_FILE, "w", encoding="utf-8") as f:
            f.write(resp.text)
        print(f"✔ Archivo guardado como {DEBUG_FILE}")
        return True
    except Exception as e:
        print("❌ Error descargando HTML:", e)
        return False


# ----------------------------------------------------
# 2. LEER Y PARSEAR debug_livefutbol.html
# ----------------------------------------------------
def parsear_debug_html():
    if not os.path.exists(DEBUG_FILE):
        print("❌ No existe debug_livefutbol.html — primero ejecútalo para generarlo.")
        return []

    with open(DEBUG_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    modulo = soup.find("div", class_="module-gameplan")
    if modulo is None:
        print("❌ No encuentro 'module-gameplan' en debug_livefutbol.html")
        print("Revisa el archivo, puede que la web devolviera HTML vacío.")
        return []

    partidos_final = []

    # Todas las jornadas
    jornadas = modulo.find_all("div", class_="hs-head hs-head--round round-head")

    for jornada_tag in jornadas:
        jornada_texto = jornada_tag.get_text(strip=True)

        # Cursor: avanzar por los hermanos hasta encontrar partidos
        cursor = jornada_tag.find_next_sibling()

        while cursor and cursor.name == "div":

            clases = cursor.get("class") or []

            # ¿Es un partido terminado?
            if "finished" in clases and "match" in clases:

                # Equipo local
                local_tag = cursor.find("div", class_="team-name-home")
                local = local_tag.get_text(strip=True) if local_tag else ""

                # Equipo visitante
                visitante_tag = cursor.find("div", class_="team-name-away")
                visitante = visitante_tag.get_text(strip=True) if visitante_tag else ""

                # Resultado
                resultado_tag = cursor.find("div", class_="match-result")
                resultado = resultado_tag.get_text(strip=True) if resultado_tag else ""

                # Fecha (hermano anterior con clase date-head)
                fecha_tag = cursor.find_previous_sibling(
                    "div",
                    class_="hs-head hs-head--date hs-head--date date-head"
                )
                fecha = fecha_tag.get_text(strip=True) if fecha_tag else ""

                partidos_final.append({
                    "jornada": jornada_texto,
                    "fecha": fecha,
                    "local": local,
                    "visitante": visitante,
                    "resultado": resultado
                })

            cursor = cursor.find_next_sibling()

    return partidos_final


# ----------------------------------------------------
# 3. GUARDAR CSV
# ----------------------------------------------------
def guardar_csv(partidos):
    df = pd.DataFrame(partidos)
    df.to_csv("resultados_laliga.csv", index=False, encoding="utf-8")
    print("✔ CSV generado: resultados_laliga.csv")


# ----------------------------------------------------
# MAIN
# ----------------------------------------------------
def main():

    print("\n=== DESCARGANDO HTML PARA DEBUG ===")
    descargar_debug_html()

    print("\n=== LEYENDO debug_livefutbol.html ===")
    partidos = parsear_debug_html()

    if not partidos:
        print("❌ No se pudieron extraer partidos. Revisa debug_livefutbol.html.")
        return

    print(f"\n✔ Partidos extraídos: {len(partidos)}")
    guardar_csv(partidos)


if __name__ == "__main__":
    main()
