import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time

BASE = "https://www.livefutbol.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(f"[fetch_html] Error en {url}: {e}")
    return None

def fetch_html_selenium(url):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    import time

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=options)
    driver.get(url)
    time.sleep(5)  # esperar JS cargar bien
    html = driver.page_source
    driver.quit()
    return html

def fetch_html_with_fallback(url):
    html = fetch_html(url)
    if not html or "team-statistics" not in html:
        print("[fetch_html_with_fallback] Fallback a Selenium para", url)
        html = fetch_html_selenium(url)
    return html

def extract_team_stats_links(lineup_url):
    print(f"\n[INFO] Procesando: {lineup_url}")
    html = fetch_html_with_fallback(lineup_url)
    if not html:
        print(f"[ERROR] No se pudo obtener HTML de {lineup_url}")
        return []

    soup = BeautifulSoup(html, "html.parser")

    # Buscar en todo el documento todos los enlaces con "team-statistics"
    all_links = soup.find_all("a", href=True)
    ts_links = []
    for a in all_links:
        href = a["href"].strip()
        text = a.get_text(strip=True)
        if "team-statistics" in href.lower():
            full_url = urljoin(BASE, href)
            ts_links.append((full_url, text))

    if not ts_links:
        print("[WARNING] No se encontraron enlaces team-statistics en esta página.")
    else:
        print(f"[RESULTADO] {len(ts_links)} enlaces team-statistics encontrados:")
        for url, text in ts_links:
            print(f"  - {url}  (texto link: '{text}')")

    return ts_links

if __name__ == "__main__":
    # Ejemplo: lista de URLs lineup para analizar
    lineup_urls = [
        "https://www.livefutbol.com/lineup/ma10299623/athletic-club_getafe-cf/",
        "https://www.livefutbol.com/lineup/ma10299971/real-valladolid_athletic-club/",
        # añade aquí más URLs a analizar
    ]

    for url in lineup_urls:
        extract_team_stats_links(url)
        time.sleep(2)  # para no saturar el servidor
