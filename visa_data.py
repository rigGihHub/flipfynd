import json

def uppskattat_varde(item):
    titel = item["titel"].lower()
    pris = item["pris"]

    varde = pris

    if "game-worn" in titel:
        varde += 70
    if "jersey" in titel:
        varde += 30
    if "dominion" in titel:
        varde += 40
    if "/150" in titel:
        varde += 40
    if "autograf" in titel:
        varde += 60
    if "bedard" in titel:
        varde += 40
    if "gretzky" in titel:
        varde += 20
    if "ovechkin" in titel:
        varde += 20
    if "peter forsberg" in titel:
        varde += 15
    if "samling" in titel:
        varde += 10

    if titel == "hockeykort samling":
        varde -= 15

    if varde < 0:
        varde = 0

    return varde

def ai_kommentar(item, varde):
    titel = item["titel"].lower()
    pris = item["pris"]
    skillnad = varde - pris

    kommentarer = []

    if "game-worn" in titel or "jersey" in titel:
        kommentarer.append("Innehåller memorabilia-ord, vilket ofta är mer intressant än vanliga baskort.")

    if "dominion" in titel or "/150" in titel:
        kommentarer.append("Tyder på numrerat eller mer premiumbetonat kort.")

    if "autograf" in titel:
        kommentarer.append("Autograf nämns i titeln, vilket ofta ger bättre efterfrågan.")

    if "samling" in titel and pris > 150:
        kommentarer.append("Samlingsannons med högre pris. Risk att det mest är bulk utan starka nyckelkort.")

    if "gretzky" in titel or "forsberg" in titel or "ovechkin" in titel:
        kommentarer.append("Stort namn i titeln, men det betyder inte automatiskt att kortet har högt marknadsvärde.")

    if "bedard" in titel:
        kommentarer.append("Bedard är het på marknaden, men många billiga kort är ändå vanliga baskort.")

    if skillnad >= 50:
        kommentarer.append("Priset ser lågt ut jämfört med den enkla värdemodellen.")
    elif skillnad <= 0:
        kommentarer.append("Ingen tydlig marginal enligt nuvarande modell.")

    if not kommentarer:
        kommentarer.append("Ser okej ut, men annonsen behöver ofta granskas manuellt innan köp.")

    return " ".join(kommentarer)

with open("tradera_data.json", "r", encoding="utf-8") as fil:
    data = json.load(fil)

print("\nTOPP FYND:\n")

for item in data[:15]:
    varde = uppskattat_varde(item)
    skillnad = varde - item["pris"]
    kommentar = ai_kommentar(item, varde)

    beslut = "SKIP"
    if skillnad >= 50:
        beslut = "KÖP (starkt fynd)"
    elif skillnad >= 20:
        beslut = "KÖP"
    elif skillnad >= 5:
        beslut = "KANSKE"

    print(item["titel"])
    print(f"Pris: {item['pris']} kr")
    print(f"Score: {item['score']}")
    print(f"Uppskattat värde: ca {varde} kr")
    print(f"Möjlig marginal: {skillnad} kr")
    print(f"Beslut: {beslut}")
    print(f"Kommentar: {kommentar}")
    print(f"Länk: {item['lank']}")
    print("-" * 60)