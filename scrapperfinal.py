# full_season_scraper.py
# Basado en tu resultadosscrapper.py (archivo original subido: /mnt/data/resultadosscrapper.py)
# Ejecutar en la misma carpeta. Requiere: requests, bs4, pandas, selenium, webdriver_manager

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import sys
import json
import re
from urllib.parse import urljoin

# Selenium fallback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

BASE = "https://www.livefutbol.com"
SEASON_URL = "https://www.livefutbol.com/competition/co97/espana-primera-division/se74771/2024-2025/all-matches/"
DEBUG_FILE = "debug_livefutbol.html"
RESULTS_CSV = "resultados_laliga.csv"
PLAYERS_CSV = "players_stats.csv"
PROCESSED_JSON = "processed_matches.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120 Safari/537.36"
}

# ---------------------------
# NETWORK: requests + selenium
# ---------------------------
def fetch_with_requests(url, timeout=15):
    s = requests.Session()
    try:
        r = s.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[requests] error fetching {url}: {e}")
        return None

def fetch_with_selenium(url, headless=True):
    print("[selenium] arrancando navegador...")
    options = Options()
    if headless:
        # usar el nuevo modo headless si disponible
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(url)
        time.sleep(3)
        return driver.page_source
    finally:
        driver.quit()

def fetch_html(url, require_contains=None):
    html = fetch_with_requests(url)
    if html and require_contains and require_contains not in html:
        # fallback to selenium when expected fragment is missing
        print("[fetch_html] expected fragment not in requests HTML, intentando selenium...")
        html = fetch_with_selenium(url)
    if not html:
        print("[fetch_html] requests falló, intentando selenium...")
        html = fetch_with_selenium(url)
    return html

# ---------------------------
# UTIL: minuto y minutos
# ---------------------------
def extraer_minuto(texto):
    if texto is None:
        return None
    m = re.search(r"(\d+)\.", texto)
    return int(m.group(1)) if m else None

def minutos_jugados(entrar, salir, es_suplente, match_len=90):
    # Suplente que no entró
    if es_suplente and entrar is None:
        return 0
    # Titular que juega todo
    if not es_suplente and entrar == 0 and salir is None:
        return match_len
    # Titular sustituido
    if not es_suplente and salir is not None:
        return max(0, salir)
    # Suplente que entró
    if es_suplente and entrar is not None and salir is None:
        return max(0, match_len - entrar)
    # Entró y salió (suplente que también salió)
    if entrar is not None and salir is not None:
        return max(0, salir - entrar)
    return 0

# ---------------------------
# PARSE: extraer partidos y enlaces lineup
# ---------------------------
def parsear_partidos_con_links(html):
    soup = BeautifulSoup(html, "html.parser")
    modulo = soup.find("div", class_="module-gameplan")
    if modulo is None:
        raise RuntimeError("No se encontró module-gameplan en la página principal.")

    datos = []
    jornadas = modulo.find_all("div", class_="hs-head hs-head--round round-head")

    for jornada_tag in jornadas:
        jornada_texto = jornada_tag.get_text(strip=True)
        cursor = jornada_tag.find_next_sibling()
        while cursor and cursor.get("class") != ["hs-head", "hs-head--round", "round-head"]:
            clases = cursor.get("class") or []
            if "match" in clases:
                # sólo procesar partidos que tengan al menos equipos (puede haber many states)
                local_tag = cursor.find("div", class_="team-name-home")
                visitante_tag = cursor.find("div", class_="team-name-away")
                resultado_tag = cursor.find("div", class_="match-result")
                local = local_tag.get_text(strip=True) if local_tag else ""
                visitante = visitante_tag.get_text(strip=True) if visitante_tag else ""
                resultado = resultado_tag.get_text(strip=True) if resultado_tag else ""

                # buscar el enlace lineup dentro de match-more a[href*="/match-report/"][href*="lineup"]
                lineup_href = None
                mm = cursor.find("div", class_="match-more")
                if mm:
                    a = mm.find("a", href=True)
                    if a and "/match-report/" in a['href'] and "lineup" in a['href']:
                        lineup_href = a['href']

                # si no hay match-more, intentar buscar enlace en todo cursor
                if not lineup_href:
                    a = cursor.find("a", href=True)
                    if a and "/match-report/" in a['href'] and "lineup" in a['href']:
                        lineup_href = a['href']

                # fecha (buscar tag de fecha anterior)
                fecha_tag = cursor.find_previous_sibling("div", class_="hs-head hs-head--date hs-head--date date-head")
                fecha = fecha_tag.get_text(strip=True) if fecha_tag else ""

                datos.append({
                    "jornada": jornada_texto,
                    "fecha": fecha,
                    "local": local,
                    "visitante": visitante,
                    "resultado": resultado,
                    "lineup": urljoin(BASE, lineup_href) if lineup_href else None
                })
            cursor = cursor.find_next_sibling()
    return datos

# ---------------------------
# PARSE: procesar una página de lineup -> devuelve stats por jugador (dict)
# ---------------------------
def procesar_lineup_html(html):
    soup = BeautifulSoup(html, "html.parser")
    match_len = 90  # por ahora fijo; detectar tiempo extra si necesario
    
    players = {}  # key: (nombre, equipo) -> {'equipo':..., 'minutos':..., 'goles':...}

    # helper para procesar un bloque (home/away)
    def procesar_bloque(side):
        # side: 'home' o 'away'
        equipo_name = None
        # intentar extraer nombre del encabezado <h3 class="hs-block-header"> ... Team Name ...
        header = soup.find("h3", class_="hs-block-header")
        # Pero hay dos encabezados (home y away) — mejor buscar la imagen con class team-image-home/team-image-away
        team_div = soup.find("div", class_=f"team-image team-image-{side} team-autoimage")
        if team_div:
            # el alt/title del img contiene el nombre
            img = team_div.find("img")
            if img and img.get("alt"):
                equipo_name = img.get("alt").strip()

        # Si no se detecta, usar texto del h3 respectivo (buscar por patrón que contenga nombre seguido de '(')
        # Buscamos h3 que contenga la imagen y texto
        if not equipo_name:
            h3s = soup.find_all("h3", class_="hs-block-header")
            for h in h3s:
                txt = h.get_text(" ", strip=True)
                if "(" in txt:  # formato "Equipo (formación)"
                    # heurística: si en el h3 hay un team-image con clase side
                    if h.find_previous("div", class_=f"team-image team-image-{side} team-autoimage") or h.find("div", class_=f"team-image team-image-{side} team-autoimage"):
                        equipo_name = txt.split("(")[0].strip()
                        break

        # Si aun no, dejar None y llenarlo con 'home'/'away'
        if not equipo_name:
            equipo_name = side

        # titulares
        titulares_div = soup.find("div", class_=f"hs-lineup--starter {side}")
        if titulares_div:
            for ev in titulares_div.find_all("div", class_="event"):
                nombre_tag = ev.find("div", class_="person-name")
                if not nombre_tag:
                    continue
                nombre = nombre_tag.get_text(strip=True)
                salida_tag = ev.find("div", class_="playing substitute-out")
                minuto_salida = extraer_minuto(salida_tag.text) if salida_tag else None

                # goles: contar elementos .goal dentro del bloque del jugador
                goles = 0
                goles_tags = ev.find_all("div", class_=re.compile("goal"))
                goles = len(goles_tags)

                key = (nombre, equipo_name)
                players[key] = players.get(key, {"equipo": equipo_name, "minutos": 0, "goles": 0, "partidos": 0})
                # titular -> entrar = 0
                mins = minutos_jugados(0, minuto_salida, es_suplente=False, match_len=match_len)
                players[key]["minutos"] += mins
                players[key]["goles"] += goles
                if mins > 0:
                    players[key]["partidos"] += 1

        # suplentes
        suplentes_div = soup.find("div", class_=f"hs-lineup--bench {side}")
        if suplentes_div:
            for ev in suplentes_div.find_all("div", class_="event"):
                nombre_tag = ev.find("div", class_="person-name")
                if not nombre_tag:
                    continue
                nombre = nombre_tag.get_text(strip=True)
                entrar_tag = ev.find("div", class_="playing substitute-in")
                minuto_entrada = extraer_minuto(entrar_tag.text) if entrar_tag else None

                # goles en su bloque
                goles_tags = ev.find_all("div", class_=re.compile("goal"))
                goles = len(goles_tags)

                key = (nombre, equipo_name)
                players[key] = players.get(key, {"equipo": equipo_name, "minutos": 0, "goles": 0, "partidos": 0})
                mins = minutos_jugados(minuto_entrada, None, es_suplente=True, match_len=match_len)
                players[key]["minutos"] += mins
                players[key]["goles"] += goles
                if mins > 0:
                    players[key]["partidos"] += 1

    # procesar ambos lados
    procesar_bloque("home")
    procesar_bloque("away")
    return players

# ---------------------------
# CSV players: leer/actualizar/escribir
# ---------------------------
def load_players_csv():
    if not os.path.exists(PLAYERS_CSV):
        return {}  # key: (nombre, equipo) -> dict
    df = pd.read_csv(PLAYERS_CSV, encoding="utf-8")
    d = {}
    for _, row in df.iterrows():
        key = (row['nombre'], row['equipo'])
        d[key] = {
            "equipo": row['equipo'],
            "minutos": int(row['minutos_totales']),
            "goles": int(row['goles_totales']),
            "partidos": int(row['partidos_jugados'])
        }
    return d

def save_players_csv(players_dict):
    rows = []
    for (nombre, equipo), vals in players_dict.items():
        rows.append({
            "nombre": nombre,
            "equipo": equipo,
            "minutos_totales": vals['minutos'],
            "goles_totales": vals['goles'],
            "partidos_jugados": vals['partidos']
        })
    df = pd.DataFrame(rows)
    df.to_csv(PLAYERS_CSV, index=False, encoding="utf-8")
    print(f"✔ Guardado {PLAYERS_CSV} ({len(rows)} jugadores)")

# ---------------------------
# PROCESSED matches tracking
# ---------------------------
def load_processed():
    if os.path.exists(PROCESSED_JSON):
        with open(PROCESSED_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_processed(d):
    with open(PROCESSED_JSON, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# ---------------------------
# MAIN flow
# ---------------------------
def main():
    print("=== Descargando página de la temporada ===")
    html = fetch_html(SEASON_URL, require_contains="module-gameplan")
    if not html:
        print("❌ No se pudo descargar la página de la temporada.")
        sys.exit(1)

    # guardar debug opcional
    with open(DEBUG_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print("=== Parseando partidos y enlaces de lineup ===")
    partidos = parsear_partidos_con_links(html)
    print(f"Partidos detectados: {len(partidos)}")

    # guardar resultados CSV simple
    df = pd.DataFrame(partidos)
    df.to_csv(RESULTS_CSV, index=False, encoding="utf-8")
    print(f"✔ CSV de resultados guardado: {RESULTS_CSV}")

    # cargar jugadores existentes y procesados
    players_master = load_players_csv()
    processed = load_processed()

    session = requests.Session()
    session.headers.update(HEADERS)

    # recorrer partidos y procesar alineaciones
    for i, p in enumerate(partidos, 1):
        link = p.get("lineup")
        clave = link if link else f"{p['local']} vs {p['visitante']} ({p['jornada']})"
        if clave in processed:
            print(f"[{i}/{len(partidos)}] Saltando partido ya procesado: {clave}")
            continue
        if not link:
            print(f"[{i}/{len(partidos)}] No hay enlace de lineup para {p['local']} - {p['visitante']}")
            processed[clave] = {"status": "no_lineup"}
            save_processed(processed)
            continue

        print(f"[{i}/{len(partidos)}] Procesando lineup: {link}")
        # intentar requests primero
        html_lineup = None
        try:
            r = session.get(link, timeout=15)
            if r.ok and "hs-lineup" in r.text:
                html_lineup = r.text
            else:
                html_lineup = fetch_with_selenium(link)
        except Exception as e:
            print(f"  [!] Error requests lineup: {e} -> probando selenium...")
            try:
                html_lineup = fetch_with_selenium(link)
            except Exception as e2:
                print(f"  [!] selenium falló: {e2}")
                processed[clave] = {"status": "failed", "error": str(e2)}
                save_processed(processed)
                continue

        # parse lineup
        try:
            players_here = procesar_lineup_html(html_lineup)
        except Exception as e:
            print(f"  [!] Error parseando lineup: {e}")
            processed[clave] = {"status": "failed_parse", "error": str(e)}
            save_processed(processed)
            continue

        # actualizar master
        for (nombre, equipo), stats in players_here.items():
            key = (nombre, equipo)
            if key not in players_master:
                players_master[key] = {"equipo": equipo, "minutos": stats['minutos'], "goles": stats['goles'], "partidos": stats['partidos']}
            else:
                players_master[key]['minutos'] += stats['minutos']
                players_master[key]['goles'] += stats['goles']
                players_master[key]['partidos'] += stats['partidos']

        # marcar procesado
        processed[clave] = {"status": "done", "local": p['local'], "visitante": p['visitante'], "resultado": p['resultado']}
        save_processed(processed)

        # guardar intermedio para no perder datos si larga ejecución
        save_players_csv(players_master)

        # pequeño delay respetuoso
        time.sleep(1.0)

    # final save
    save_players_csv(players_master)
    print("=== PROCESO FINALIZADO ===")

if __name__ == "__main__":
    main()
