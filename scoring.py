def calculate_score(annons):
    score = 0

    totalpris = annons["pris"] + annons["frakt"]

    if totalpris < 60:
        score += 30
    elif totalpris < 100:
        score += 15

    titel = annons["titel"].lower()

    if "osorterat" in titel:
        score += 25
    if "samling" in titel:
        score += 20
    if "album" in titel:
        score += 15
    if "lot" in titel:
        score += 10

    if annons["frakt"] > 45:
        score -= 10

    return score