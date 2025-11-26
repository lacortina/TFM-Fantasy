import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://www.livefutbol.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def fetch_html(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.text


def parse_team_statistics_page(url):
    """
    Devuelve un diccionario:
    {
        'local': 'Athletic Club',
        'visitante': 'Getafe CF',
        'stats': {
            'Duelos': {'home': 42.57, 'away': 57.43},
            'Posesión de balón en %': {'home': 61.65, 'away': 38.35},
            'Tiros a puerta': {'home': 7, 'away': 9},
            ...
        }
    }
    """
    full_url = url if url.startswith("http") else urljoin(BASE, url)
    html = fetch_html(full_url)

    soup = BeautifulSoup(html, "html.parser")

    # ------------------------------------------
    # 1. Extraer nombre del equipo local/visitante
    # ------------------------------------------
    header = soup.find("ul", class_="hs-comparison")
    head = header.find("li", class_="hs-head hs-comparison--head")

    # Local
    home = head.find("div", class_="hs-home")
    home_name = home.find("div", class_="team-shortname").get_text(strip=True)

    # Visitante
    away = head.find("div", class_="hs-away")
    away_name = away.find("div", class_="team-shortname").get_text(strip=True)

    # ------------------------------------------
    # 2. Extraer estadísticas (cada <li> representa una)
    # ------------------------------------------
    stats = {}

    items = header.find_all("li")
    for li in items:
        if "hs-head" in li.get("class", []):
            continue  # saltar el encabezado

        name_tag = li.find("div", class_="hs-name")
        if not name_tag:
            continue

        stat_name = name_tag.get_text(strip=True)

        # valores home/away
        home_val_tag = li.find("div", class_="hs-value hs-value-home")
        away_val_tag = li.find("div", class_="hs-value hs-value-away")

        if not (home_val_tag and away_val_tag):
            continue

        # convertir valores a número
        home_raw = home_val_tag.get_text(strip=True).replace(",", ".").replace("%", "")
        away_raw = away_val_tag.get_text(strip=True).replace(",", ".").replace("%", "")

        # intentar convertir a float/int
        try:
            home_val = float(home_raw) if "." in home_raw else int(home_raw)
        except:
            home_val = home_raw

        try:
            away_val = float(away_raw) if "." in away_raw else int(away_raw)
        except:
            away_val = away_raw

        stats[stat_name] = {
            "home": home_val,
            "away": away_val
        }

    return {
        "local": home_name,
        "visitante": away_name,
        "stats": stats
    }


# ---------------------------
# EJEMPLO DE PRUEBA REAL
# ---------------------------
if __name__ == "__main__":
    # EJEMPLO: Athletic vs Getafe
    ejemplo_url = "/match-report/co97/espana-primera-division/ma10299623/athletic-club_getafe-cf/team-statistics/"
    
    data = parse_team_statistics_page(ejemplo_url)
    print(data)
