import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import sys

# --- Selenium fallback ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

URL = "https://www.livefutbol.com/competition/co97/espana-primera-division/se74771/2024-2025/all-matches/"
DEBUG_FILE = "debug_livefutbol.html"

#https://www.livefutbol.com/competition/co97/espana-primera-division/se74771/2024-2025/all-matches/
#https://www.livefutbol.com/competition/co97/espana-primera-division/se96657/2025-2026/all-matches/
#https://www.livefutbol.com/competition/co97/espana-primera-division/se23902/2017-2018/all-matches/

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120 Safari/537.36"
}

# --------------------------------------------------------------------
# 1. INTENTAR DESCARGAR HTML CON REQUESTS
# --------------------------------------------------------------------
def fetch_with_requests(url):
    try:
        s = requests.Session()
        resp = s.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        print("[requests] ✔ HTML descargado correctamente.")
        return resp.text
    except Exception as e:
        print(f"[requests] ❌ Fallo: {e}")
        return None

# --------------------------------------------------------------------
# 2. SI REQUESTS FALLA → USAR SELENIUM
# --------------------------------------------------------------------
def fetch_with_selenium(url, headless=True):
    print("[selenium] Intentando obtener HTML real...")

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(url)
        time.sleep(3)
        html = driver.page_source
        print("[selenium] ✔ HTML capturado correctamente.")
        return html
    finally:
        driver.quit()

# --------------------------------------------------------------------
# 3. GUARDAR DEBUG HTML
# --------------------------------------------------------------------
def guardar_debug(html):
    with open(DEBUG_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[debug] ✔ Guardado en {DEBUG_FILE}")

# --------------------------------------------------------------------
# 4. PARSEAR MODULE-GAMEPLAN
# --------------------------------------------------------------------
def parsear_partidos(html):

    soup = BeautifulSoup(html, "html.parser")

    modulo = soup.find("div", class_="module-gameplan")
    if modulo is None:
        print("❌ No se encontró el módulo 'module-gameplan'.")
        return []

    datos_finales = []

    jornadas = modulo.find_all("div", class_="hs-head hs-head--round round-head")

    for jornada_tag in jornadas:
        jornada_texto = jornada_tag.get_text(strip=True)

        cursor = jornada_tag.find_next_sibling()

        while cursor and cursor.get("class") != ["hs-head", "hs-head--round", "round-head"]:

            clases = cursor.get("class") or []

            if "finished" in clases and "match" in clases:

                local_tag = cursor.find("div", class_="team-name-home")
                visitante_tag = cursor.find("div", class_="team-name-away")
                resultado_tag = cursor.find("div", class_="match-result")

                local = local_tag.get_text(strip=True) if local_tag else ""
                visitante = visitante_tag.get_text(strip=True) if visitante_tag else ""
                resultado = resultado_tag.get_text(strip=True) if resultado_tag else ""

                fecha_tag = cursor.find_previous_sibling(
                    "div",
                    class_="hs-head hs-head--date hs-head--date date-head"
                )
                fecha = fecha_tag.get_text(strip=True) if fecha_tag else ""

                datos_finales.append({
                    "jornada": jornada_texto,
                    "fecha": fecha,
                    "local": local,
                    "visitante": visitante,
                    "resultado": resultado
                })

            cursor = cursor.find_next_sibling()

    return datos_finales

# --------------------------------------------------------------------
# 5. GUARDAR CSV
# --------------------------------------------------------------------
def guardar_csv(partidos):
    df = pd.DataFrame(partidos)
    df.to_csv("resultados_laliga.csv", index=False, encoding="utf-8")
    print("✔ CSV generado: resultados_laliga.csv")

# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------
def main():

    print("\n=== Intentando descargar con requests ===")
    html = fetch_with_requests(URL)

    if html is None or "module-gameplan" not in html:
        print("\n=== Requests falló o devolvió HTML vacío → usando Selenium ===")
        html = fetch_with_selenium(URL)

    if not html:
        print("❌ No se pudo obtener HTML ni con Selenium.")
        sys.exit(1)

    guardar_debug(html)

    print("\n=== Parseando partidos... ===")
    partidos = parsear_partidos(html)

    if not partidos:
        print("❌ No se pudieron extraer partidos. Revisa debug_livefutbol.html.")
        sys.exit(1)

    print(f"✔ Partidos extraídos: {len(partidos)}")
    guardar_csv(partidos)

    # -----------------------------
    # 6. BORRAR EL DEBUG HTML
    # -----------------------------
    if os.path.exists(DEBUG_FILE):
        os.remove(DEBUG_FILE)
        print(f"✔ Archivo {DEBUG_FILE} borrado después de procesar.")

if __name__ == "__main__":
    main()
