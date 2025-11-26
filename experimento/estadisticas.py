import requests

url = "https://www.livefutbol.com/match-report/co97/primera-division/ma11222876/girona-fc_rayo-vallecano/lineup/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)

with open("pagina_livefutbol.html", "w", encoding="utf-8") as f:
    f.write(response.text)

print("Archivo guardado como pagina_livefutbol.html")
