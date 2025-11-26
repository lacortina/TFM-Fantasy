from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests

BASE = "https://www.livefutbol.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.text


def get_match_team_statistics_link(lineup_url):
    html = fetch(lineup_url)
    soup = BeautifulSoup(html, "html.parser")

    # 1. Buscar SOLO el contenido del partido
    article = soup.find("article", id="hs-content")
    if not article:
        print("❌ No se encontró <article id='hs-content'> (quizá requiere Selenium).")
        return None

    # 2. Buscar SOLO el menú de partido (no el menú general)
    nav = article.find("nav", class_="hs-menu-level-match")
    if not nav:
        print("❌ No se encontró nav.hs-menu-level-match dentro del artículo.")
        return None

    ul = nav.find("ul", class_="hs-menu--list")
    if not ul:
        print("❌ No existe ul.hs-menu--list dentro del menú de partido.")
        return None

    # 3. Buscar el enlace correcto
    for a in ul.find_all("a", href=True):
        href = a["href"]
        if "/match-report/" in href and "team-statistics" in href:
            full = urljoin(BASE, href)
            print("✔ Enlace correcto encontrado:", full)
            return full

    print("❌ No se encontró enlace team-statistics dentro del menú correcto.")
    return None


# ---------------------------------------------------------
# PRUEBA: Athletic - Getafe
# ---------------------------------------------------------

if __name__ == "__main__":
    url = "https://www.livefutbol.com/match-report/co97/primera-division/ma10299623/athletic-club_getafe-cf/lineup/"
    link = get_match_team_statistics_link(url)
    print("RESULT:", link)
