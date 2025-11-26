from bs4 import BeautifulSoup
import csv
import re

# Cargar archivo HTML previamente guardado
with open("pagina_livefutbol.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# -----------------------------
# Auxiliares
# -----------------------------

def extraer_minuto(texto):
    if texto is None:
        return None
    m = re.search(r"(\d+)\.", texto)
    return int(m.group(1)) if m else None

def minutos_jugados(entrar, salir, es_suplente):
    # Suplente que NO entró
    if es_suplente and entrar is None:
        return 0

    # Titular que juega todo (entrar=0 y no sale)
    if not es_suplente and entrar == 0 and salir is None:
        return 90

    # Titular sustituido
    if not es_suplente and salir is not None:
        return salir

    # Suplente que entra y no sale
    if es_suplente and entrar is not None and salir is None:
        return 90 - entrar

    # Caso general
    if entrar is not None and salir is not None:
        return max(0, salir - entrar)

    return 0


# -----------------------------
# Función para extraer info de un equipo
# -----------------------------
def procesar_equipo(tipo, nombre_equipo):
    """
    tipo: 'home' o 'away'
    nombre_equipo: string ('Girona FC' o 'Rayo Vallecano')
    """
    datos = {}

    # --- TITULARES ---
    titulares_div = soup.find("div", class_=f"hs-lineup--starter {tipo}")
    if titulares_div:
        for ev in titulares_div.find_all("div", class_="event"):
            nombre_tag = ev.find("div", class_="person-name")
            if not nombre_tag:
                continue
            nombre = nombre_tag.get_text(strip=True)

            salida_tag = ev.find("div", class_="playing substitute-out")
            minuto_salida = extraer_minuto(salida_tag.text) if salida_tag else None

            # goles
            goles_tag = ev.find("div", class_="match_event-goal")
            goles = len(goles_tag.find_all("div", class_=re.compile("goal"))) if goles_tag else 0

            datos[nombre] = {
                "equipo": nombre_equipo,
                "entrar": 0,
                "salir": minuto_salida,
                "goles": goles,
                "es_suplente": False
            }

    # --- SUPLENTES ---
    suplentes_div = soup.find("div", class_=f"hs-lineup--bench {tipo}")
    if suplentes_div:
        for ev in suplentes_div.find_all("div", class_="event"):
            nombre_tag = ev.find("div", class_="person-name")
            if not nombre_tag:
                continue
            nombre = nombre_tag.get_text(strip=True)

            entrar_tag = ev.find("div", class_="playing substitute-in")
            minuto_entrada = extraer_minuto(entrar_tag.text) if entrar_tag else None

            goles_tag = ev.find("div", class_="match_event-goal")
            goles = len(goles_tag.find_all("div", class_=re.compile("goal"))) if goles_tag else 0

            datos[nombre] = {
                "equipo": nombre_equipo,
                "entrar": minuto_entrada,
                "salir": None,
                "goles": goles,
                "es_suplente": True
            }

    # --- Cálculo de minutos ---
    for jugador, info in datos.items():
        info["minutos"] = minutos_jugados(info["entrar"], info["salir"], info["es_suplente"])

    return datos


# -----------------------------
# Procesar ambos equipos
# -----------------------------
girona = procesar_equipo("home", "Girona FC")
rayo   = procesar_equipo("away", "Rayo Vallecano")

# Combinar
todos = {**girona, **rayo}

# -----------------------------
# Exportar CSV
# -----------------------------
with open("alineaciones_minutos.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["equipo", "nombre", "minutos_jugados", "goles"])

    for jugador, info in todos.items():
        writer.writerow([info["equipo"], jugador, info["minutos"], info["goles"]])

print("CSV generado: alineaciones_minutos.csv")
