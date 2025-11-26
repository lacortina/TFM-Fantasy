###############################################
# SEASON SCRAPER – LiveFutbol
# Partidos + Alineaciones + Estadísticas equipo
# Salida en CSV listos para importación MySQL
###############################################

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

RESULTS_CSV = "resultados_partidos.csv"
PLAYERS_CSV = "players_stats.csv"
TEAM_STATS_CSV = "team_stats.csv"
PROCESSED_JSON = "processed_matches.json"

HEADERS = {"User-Agent": "Mozilla/5.0"}

############################################################
# NETWORK UTILITIES
############################################################

def fetch_with_requests(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[fetch_with_requests] Error en {url}: {e}")
        return None


def fetch_with_selenium(url):
    print("[selenium] fallback in:", url)
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    driver.get(url)
    time.sleep(3)
    html = driver.page_source
    driver.quit()
    return html


def fetch_html(url, require=None):
    """
    Descarga HTML con requests y, si falla o no contiene un fragmento requerido,
    hace fallback automático a Selenium.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            html = r.text
            if require and require not in html:
                print("[fetch_html] Requiere JS o bloque específico, usando Selenium...")
                return fetch_with_selenium(url)
            return html
    except Exception as e:
        print("[fetch_html] Requests error:", e)

    print("[fetch_html] Usando Selenium como fallback")
    return fetch_with_selenium(url)


############################################################
# UTILITIES
############################################################

def extraer_minuto(texto):
    if texto is None:
        return None
    m = re.search(r"(\d+)\.", texto)
    return int(m.group(1)) if m else None


def minutos_jugados(entrar, salir, es_suplente, length=90):
    if es_suplente and entrar is None:
        return 0
    if not es_suplente and entrar == 0 and salir is None:
        return length
    if not es_suplente and salir is not None:
        return salir
    if es_suplente and entrar is not None and salir is None:
        return max(0, length - entrar)
    if entrar is not None and salir is not None:
        return max(0, salir - entrar)
    return 0


############################################################
# PARSE MAIN PAGE: partidos + enlaces lineup
############################################################

def parsear_partidos(html):
    soup = BeautifulSoup(html, "html.parser")
    modulo = soup.find("div", class_="module-gameplan")
    if not modulo:
        raise RuntimeError("No se encontró module-gameplan")

    datos = []
    jornadas = modulo.find_all("div", class_="hs-head hs-head--round round-head")

    for jornada_tag in jornadas:
        jornada_texto = jornada_tag.get_text(strip=True)
        cursor = jornada_tag.find_next_sibling()

        while cursor and cursor.get("class") != ["hs-head", "hs-head--round", "round-head"]:
            if "match" in (cursor.get("class") or []):
                local_tag = cursor.find("div", class_="team-name-home")
                visit_tag = cursor.find("div", class_="team-name-away")
                result_tag = cursor.find("div", class_="match-result")

                local = local_tag.get_text(strip=True)
                visitante = visit_tag.get_text(strip=True)
                resultado = result_tag.get_text(strip=True) if result_tag else ""

                mm = cursor.find("div", class_="match-more")
                lineup_href = None
                if mm:
                    a = mm.find("a", href=True)
                    if a and "lineup" in a["href"]:
                        lineup_href = urljoin(BASE, a["href"])

                fecha_tag = cursor.find_previous_sibling(
                    "div", class_="hs-head hs-head--date hs-head--date date-head"
                )
                fecha = fecha_tag.get_text(strip=True) if fecha_tag else ""

                datos.append({
                    "jornada": jornada_texto,
                    "fecha": fecha,
                    "local": local,
                    "visitante": visitante,
                    "resultado": resultado,
                    "lineup_url": lineup_href
                })

            cursor = cursor.find_next_sibling()

    return datos


############################################################
# PARSE LINEUP PAGE (jugadores)
############################################################

def procesar_lineup_html(html):
    soup = BeautifulSoup(html, "html.parser")
    players = {}

    def procesar(side):
        team_div = soup.find("div", class_=f"team-image team-image-{side} team-autoimage")
        img = team_div.find("img") if team_div else None
        team_name = img["alt"] if img and "alt" in img.attrs else side

        # titulares
        titulares = soup.find("div", class_=f"hs-lineup--starter {side}")
        if titulares:
            for ev in titulares.find_all("div", class_="event"):
                ntag = ev.find("div", class_="person-name")
                if not ntag:
                    continue
                nombre = ntag.get_text(strip=True)
                out_tag = ev.find("div", class_="playing substitute-out")
                salida = extraer_minuto(out_tag.text) if out_tag else None
                goles = len(ev.find_all("div", class_=re.compile("goal")))

                key = (nombre, team_name)
                mins = minutos_jugados(0, salida, False)

                if key not in players:
                    players[key] = {"equipo": team_name, "minutos": 0, "goles": 0, "partidos": 0}

                players[key]["minutos"] += mins
                players[key]["goles"] += goles
                if mins > 0:
                    players[key]["partidos"] += 1

        # suplentes
        bench = soup.find("div", class_=f"hs-lineup--bench {side}")
        if bench:
            for ev in bench.find_all("div", class_="event"):
                ntag = ev.find("div", class_="person-name")
                if not ntag:
                    continue
                nombre = ntag.get_text(strip=True)
                in_tag = ev.find("div", class_="playing substitute-in")
                entrada = extraer_minuto(in_tag.text) if in_tag else None
                goles = len(ev.find_all("div", class_=re.compile("goal")))

                key = (nombre, team_name)
                mins = minutos_jugados(entrada, None, True)

                if key not in players:
                    players[key] = {"equipo": team_name, "minutos": 0, "goles": 0, "partidos": 0}

                players[key]["minutos"] += mins
                players[key]["goles"] += goles
                if mins > 0:
                    players[key]["partidos"] += 1

    procesar("home")
    procesar("away")
    return players


############################################################
# PARSE TEAM-STATISTICS PAGE
############################################################

def parse_team_statistics_page(url):
    """
    Descarga y parsea la página de 'team-statistics'.
    Devuelve una lista de filas:
    [{'stat':..., 'home':..., 'away':..., 'home_team':..., 'away_team':...}, ...]
    Si no se encuentra la sección de estadísticas devuelve [].
    """
    if not url:
        print("  [team_stats] Enlace vacío.")
        return []

    print(f"  [team_stats] Descargando {url} ...")
    html = fetch_html(url, require="hs-comparison")
    if not html:
        print(f"  [team_stats] No se pudo descargar HTML para {url}.")
        return []

    soup = BeautifulSoup(html, "html.parser")

    # Buscar el bloque de comparación con varias heurísticas
    header = soup.find("ul", class_="hs-comparison")
    if not header:
        header = soup.find("ul", class_=re.compile(r"hs-comparison"))
    if not header:
        header = soup.find("div", class_=re.compile(r"hs-comparison"))

    if not header:
        print(f"  [team_stats] No se encontró el bloque hs-comparison en {url}. Saltando estadísticas.")
        return []

    # Nombres de equipos
    home_name = None
    away_name = None
    head_li = header.find("li", class_=re.compile(r"hs-head"))
    if head_li:
        home_div = head_li.find("div", class_=re.compile(r"hs-home"))
        away_div = head_li.find("div", class_=re.compile(r"hs-away"))
        if home_div:
            sn = home_div.find("div", class_=re.compile(r"team-shortname"))
            if sn:
                home_name = sn.get_text(strip=True)
            else:
                img = home_div.find("img")
                if img and img.get("alt"):
                    home_name = img.get("alt").strip()
        if away_div:
            sn = away_div.find("div", class_=re.compile(r"team-shortname"))
            if sn:
                away_name = sn.get_text(strip=True)
            else:
                img = away_div.find("img")
                if img and img.get("alt"):
                    away_name = img.get("alt").strip()

    if not home_name or not away_name:
        imgs = header.find_all("img")
        if imgs and len(imgs) >= 2:
            if not home_name and imgs[0].get("alt"):
                home_name = imgs[0].get("alt").strip()
            if not away_name and imgs[1].get("alt"):
                away_name = imgs[1].get("alt").strip()

    if not home_name:
        home_name = "home"
    if not away_name:
        away_name = "away"

    rows = []

    for li in header.find_all("li"):
        classes = li.get("class") or []
        if any(re.search(r"hs-head", c) for c in classes):
            continue

        name_tag = li.find("div", class_="hs-name")
        if not name_tag:
            continue
        stat = name_tag.get_text(strip=True)

        hv = li.find("div", class_="hs-value hs-value-home")
        av = li.find("div", class_="hs-value hs-value-away")
        if not hv:
            hv = li.find("div", class_=re.compile(r"hs-value.*home"))
        if not av:
            av = li.find("div", class_=re.compile(r"hs-value.*away"))

        if not (hv and av):
            print(f"  [team_stats] Stat '{stat}' sin valores home/away claros, se omite.")
            continue

        def to_number(s):
            s = s.strip().replace(",", ".").replace("%", "")
            if s == "":
                return None
            try:
                if "." in s:
                    return float(s)
                return int(s)
            except:
                return s

        home_val = to_number(hv.get_text(strip=True))
        away_val = to_number(av.get_text(strip=True))

        rows.append({
            "stat": stat,
            "home": home_val,
            "away": away_val,
            "home_team": home_name,
            "away_team": away_name
        })

    if not rows:
        print(f"  [team_stats] No se extrajeron filas de estadísticas en {url} (posible estructura inesperada).")

    return rows


############################################################
# NUEVA FUNCIÓN: obtener SIEMPRE el enlace correcto team-statistics
############################################################

def get_correct_team_stats_link_from_lineup(lineup_url):
    """
    Obtiene SIEMPRE el enlace correcto:
    /match-report/.../team-statistics/
    a partir de la página lineup.
    """
    if not lineup_url:
        print("[team_stats_link] lineup_url vacío")
        return None

    html = fetch_html(lineup_url, require=None)
    if not html:
        print(f"[team_stats_link] No se pudo descargar lineup {lineup_url}")
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Buscar SOLO dentro de <article id="hs-content">
    article = soup.find("article", id="hs-content")
    if not article:
        print("[team_stats_link] No se encontró <article id='hs-content'> (posible JS no cargado)")
        return None

    # Buscar SOLO el menú de nivel de partido
    nav = article.find("nav", class_="hs-menu-level-sub")
    if not nav:
        nav = article.find("nav", class_="hs-menu-level-match")
    if not nav:
        print("[team_stats_link] No se encontró nav.hs-menu-level-sub ni hs-menu-level-match")
        return None

    ul = nav.find("ul", class_="hs-menu--list")
    if not ul:
        print("[team_stats_link] No se encontró ul.hs-menu--list dentro del nav")
        return None

    # Buscar el enlace correcto (solo match-report, NO competition)
    for a in ul.find_all("a", href=True):
        href = a["href"].strip()
        if "/match-report/" in href and "team-statistics" in href:
            full = urljoin(BASE, href)
            print("[team_stats_link] Enlace correcto encontrado:", full)
            return full

    print("[team_stats_link] No se encontró enlace team-statistics dentro del menú del partido")
    return None


############################################################
# CSV DATA MANAGEMENT
############################################################

def load_players():
    if not os.path.exists(PLAYERS_CSV):
        return {}
    df = pd.read_csv(PLAYERS_CSV)
    base = {}
    for _, r in df.iterrows():
        key = (r["nombre"], r["equipo"])
        base[key] = {
            "equipo": r["equipo"],
            "minutos": int(r["minutos_totales"]),
            "goles": int(r["goles_totales"]),
            "partidos": int(r["partidos_jugados"])
        }
    return base


def save_players(players):
    rows = []
    for (nombre, equipo), v in players.items():
        rows.append({
            "nombre": nombre,
            "equipo": equipo,
            "minutos_totales": v["minutos"],
            "goles_totales": v["goles"],
            "partidos_jugados": v["partidos"]
        })
    pd.DataFrame(rows).to_csv(PLAYERS_CSV, index=False)


############################################################
# MAIN
############################################################

def main():
    print("=== Descargando temporada... ===")
    html = fetch_html(SEASON_URL, require="module-gameplan")

    partidos = parsear_partidos(html)
    print("Partidos encontrados:", len(partidos))

    results_rows = []
    team_stats_rows = []

    players_master = load_players()

    processed = {}
    if os.path.exists(PROCESSED_JSON):
        processed = json.load(open(PROCESSED_JSON, "r"))

    for i, p in enumerate(partidos, 1):
        print(f"[{i}/{len(partidos)}] Procesando {p['local']} vs {p['visitante']}...")

        # Info básica del partido
        base_info = {
            "jornada": p["jornada"],
            "fecha": p["fecha"],
            "local": p["local"],
            "visitante": p["visitante"],
            "resultado": p["resultado"],
            "lineup_url": p["lineup_url"]
        }

        # 1) Alineaciones
        lineup_players = {}

        if p["lineup_url"]:
            lineup_html = fetch_html(p["lineup_url"])
            lineup_players = procesar_lineup_html(lineup_html)

            # update global players
            for key, stats in lineup_players.items():
                if key not in players_master:
                    players_master[key] = stats
                else:
                    players_master[key]["minutos"] += stats["minutos"]
                    players_master[key]["goles"] += stats["goles"]
                    players_master[key]["partidos"] += stats["partidos"]

        # 2) Team statistics usando la nueva función robusta
        team_stats = []

        match_lineup_url = p["lineup_url"]
        if match_lineup_url:
            stat_link = get_correct_team_stats_link_from_lineup(match_lineup_url)

            if stat_link:
                team_stats = parse_team_statistics_page(stat_link)
                if team_stats:
                    for row in team_stats:
                        team_stats_rows.append({
                            "jornada": p["jornada"],
                            "fecha": p["fecha"],
                            "local": p["local"],
                            "visitante": p["visitante"],
                            "stat": row["stat"],
                            "valor_local": row["home"],
                            "valor_visitante": row["away"]
                        })
            else:
                print(f"[WARNING] No hay estadísticas para {p['local']} vs {p['visitante']}")

        # Guardar info resumen partido
        results_rows.append(base_info)

        # guardados parciales
        save_players(players_master)
        pd.DataFrame(results_rows).to_csv(RESULTS_CSV, index=False)
        pd.DataFrame(team_stats_rows).to_csv(TEAM_STATS_CSV, index=False)

        time.sleep(1)

    # Final save
    save_players(players_master)
    pd.DataFrame(results_rows).to_csv(RESULTS_CSV, index=False)
    pd.DataFrame(team_stats_rows).to_csv(TEAM_STATS_CSV, index=False)

    print("=== FINALIZADO ===")


if __name__ == "__main__":
    main()
