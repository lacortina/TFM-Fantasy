from bs4 import BeautifulSoup
import pandas as pd

HTML_LOCAL = "debug_livefutbol1.html"   # <-- aquí pon tu archivo html real

def parsear_html_local():
    with open(HTML_LOCAL, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    modulo = soup.find("div", class_="module-gameplan")
    if modulo is None:
        print("No se encontró el módulo 'module-gameplan'")
        return []

    datos_finales = []

    # -------------------------------
    # 1. Todas las jornadas
    # -------------------------------
    jornadas = modulo.find_all("div", class_="hs-head hs-head--round round-head")

    for jornada_tag in jornadas:

        jornada_texto = jornada_tag.get_text(strip=True)

        # El contenedor de los partidos es SIGUIENTE HERMANO
        cursor = jornada_tag.find_next_sibling()

        # Continuar leyendo hasta encontrar un partido o la siguiente jornada
        while cursor and not cursor.get("class") == ["hs-head", "hs-head--round", "round-head"]:

            # -------------------------------
            # 2. Partidos dentro de la jornada
            # (clases incluyen "finished" y "match")
            # -------------------------------
            if cursor.has_attr("class") and "finished" in cursor["class"] and "match" in cursor["class"]:
                
                # PARTIDO ENCONTRADO
                partido = cursor

                # Equipo local
                local_tag = partido.find("div", class_="team-name-home")
                local = local_tag.get_text(strip=True) if local_tag else ""

                # Equipo visitante
                visitante_tag = partido.find("div", class_="team-name-away")
                visitante = visitante_tag.get_text(strip=True) if visitante_tag else ""

                # Resultado
                resultado_tag = partido.find("div", class_="match-result")
                resultado = resultado_tag.get_text(strip=True) if resultado_tag else ""

                # Fecha: está en el hermano inmediatamente anterior con clase `date-head`
                fecha_tag = partido.find_previous_sibling("div", class_="hs-head hs-head--date hs-head--date date-head")
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


# Guardar CSV
def guardar_csv(partidos):
    df = pd.DataFrame(partidos)
    df.to_csv("resultados_laliga.csv", index=False, encoding="utf-8")
    print("CSV guardado como resultados_laliga.csv")
    print(df.head())


if __name__ == "__main__":
    partidos = parsear_html_local()
    if not partidos:
        print("No se encontraron partidos.")
    else:
        guardar_csv(partidos)
