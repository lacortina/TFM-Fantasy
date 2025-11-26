import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

URL = "https://www.futbolfantasy.com/jugadores/antony/laliga-24-25"

#https://www.futbolfantasy.com/jugadores/antony/laliga-24-25
#https://www.futbolfantasy.com/jugadores/antony/laliga-25-26

def obtener_datos(url):

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=options
    )

    driver.get(url)
    time.sleep(2)   # esperar carga JS

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")

    # -----------------------------------------
    # Buscar SOLO la tabla que contiene puntos
    # -----------------------------------------

    tabla = soup.find("span", class_="columna_puntos")
    if not tabla:
        print("No se encontró tabla de puntos.")
        return []

    # Subir hasta la tabla
    tabla = tabla.find_parent("table")
    filas = tabla.find_all("tr")

    resultados = []

    for fila in filas:

        td_bold = fila.find("td", class_="bold")
        if not td_bold:
            continue

        texto = td_bold.get_text(strip=True)
        if not texto.isdigit():
            continue

        jornada = int(texto)

        # Equipos
        imgs = fila.find_all("img", alt=True)
        if len(imgs) < 2:
            continue

        equipo1 = imgs[0]["alt"].strip()
        equipo2 = imgs[1]["alt"].strip()

        # Determinar equipo del jugador
        # Este dato lo sacamos del título
        titulo = soup.find("h2", class_="title").get_text(strip=True)
        equipo_jugador = titulo.split(" en ")[-1].replace("Puntos ", "").strip()

        if equipo1 == equipo_jugador:
            sitio = "local"
            rival = equipo2
        elif equipo2 == equipo_jugador:
            sitio = "visitante"
            rival = equipo1
        else:
            continue

        # PUNTOS reales
        span_puntos = fila.find("span", class_="columna_puntos")
        if span_puntos:
            puntos = span_puntos.get_text(strip=True)
        else:
            puntos = None

        resultados.append((jornada, rival, sitio, puntos))

    return resultados


# -------------------------
# EJECUCIÓN
# -------------------------
if __name__ == "__main__":
    datos = obtener_datos(URL)
    for jornada, rival, sitio, puntos in datos:
        print(f"Jornada {jornada} | Rival: {rival} | {sitio.upper()} | Puntos: {puntos}")
