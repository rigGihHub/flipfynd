def build_comment(item, estimated_value, confidence, reasons):
    price = item.get("pris", 0) or 0
    shipping = item.get("frakt", 0) or 0
    total_cost = price + shipping
    margin = estimated_value - total_cost

    demand_tier = item.get("demand_tier", "okänd")
    sale_probability = item.get("sale_probability", 0) or 0
    liquidity_score = item.get("liquidity_score", 0) or 0
    risk_adjusted_profit = item.get("risk_adjusted_profit", 0) or 0
    quick_flip_score = item.get("quick_flip_score", 0) or 0
    premium_flip_score = item.get("premium_flip_score", 0) or 0
    value_source = item.get("value_source", "okänd")
    comparable_count = item.get("comparable_count", 0) or 0
    risk_flags = item.get("risk_flags", []) or []
    title = (item.get("titel", "") or "").lower()

    parts = []

    # Kostnad / ingångspris
    if total_cost <= 15:
        parts.append("Total kostnad är mycket låg, vilket begränsar nedsidan.")
    elif total_cost <= 35:
        parts.append("Total kostnad är låg nog för att annonsen kan vara värd en närmare kontroll.")
    elif total_cost >= 250:
        parts.append("Total kostnad är ganska hög, så annonsen måste bära sig på verklig efterfrågan och inte bara på titelns premiumsignal.")
    elif total_cost >= 500:
        parts.append("Det här är en dyr ingång för flip, vilket höjer kravet på stark spelarefterfrågan och säker exit.")

    # Signaler
    if reasons:
        visible_reasons = []
        seen = set()
        for reason in reasons:
            reason_clean = str(reason).strip()
            if reason_clean and reason_clean not in seen:
                visible_reasons.append(reason_clean)
                seen.add(reason_clean)
            if len(visible_reasons) >= 5:
                break

        if visible_reasons:
            parts.append("Identifierade signaler: " + ", ".join(visible_reasons) + ".")

    # Efterfrågan / spelare
    if demand_tier == "elite":
        parts.append("Spelaren ligger i modellens högsta efterfrågelager, vilket hjälper både likviditet och säljsannolikhet.")
    elif demand_tier == "strong":
        parts.append("Spelaren har relativt stark efterfrågan, vilket gör kortet mer rimligt i flip-sammanhang.")
    elif demand_tier == "medium":
        parts.append("Efterfrågan ser bara medelgod ut, så premiumsignal i titel eller set ska inte övertolkas.")
    elif demand_tier == "weak":
        parts.append("Efterfrågan på spelaren ser svag ut, vilket är en tydlig varningssignal för flip även om kortet låter premium.")

    # Premium trap
    if "premium trap" in risk_flags:
        parts.append("Kortet ser premium ut på pappret, men modellen bedömer att spelaren eller likviditeten inte riktigt bär nivån.")

    # Likviditet / säljsannolikhet
    if sale_probability >= 75 and liquidity_score >= 70:
        parts.append("Säljsannolikheten och likviditeten ser starka ut, vilket talar för snabbare exit om bedömningen stämmer.")
    elif sale_probability >= 60 and liquidity_score >= 55:
        parts.append("Likviditeten ser okej ut, men det är fortfarande inte ett givet snabbflip utan kontroll av exakt variant och skick.")
    elif sale_probability < 45 or liquidity_score < 40:
        parts.append("Likviditeten ser svag ut, så kortet kan bli trögt att sälja vidare även om det finns teoretiskt värde.")

    # Marginal / faktisk flipnytta
    if risk_adjusted_profit >= 60:
        parts.append("Modellen ser god riskjusterad vinst, alltså inte bara teoretiskt värde utan även rimlig flipnytta.")
    elif risk_adjusted_profit >= 20:
        parts.append("Det finns viss riskjusterad uppsida, men annonsen är inte självklar och bör dubbelkollas.")
    elif risk_adjusted_profit > 0:
        parts.append("Det kan finnas viss uppsida, men den är tunn när risk och säljsannolikhet räknas in.")
    else:
        parts.append("Efter riskjustering ser modellen ingen tydlig flipfördel.")

    if margin >= 100:
        parts.append("Den uppskattade marginalen mot totalkostnaden ser tydlig ut på pappret.")
    elif margin >= 40:
        parts.append("Det finns möjlig marginal, men den behöver bekräftas mot bild, skick, numrering och exakt kortvariant.")
    elif margin > 0:
        parts.append("Marginalen ser liten ut, så fel identifiering eller svag efterfrågan kan snabbt äta upp den.")
    else:
        parts.append("Modellen ser ingen tydlig ekonomisk marginal efter pris och frakt.")

    # Quick vs premium
    if quick_flip_score >= premium_flip_score + 12:
        parts.append("Det här ser mer ut som ett möjligt quick-flip-case än ett långsammare premiumspel.")
    elif premium_flip_score >= quick_flip_score + 12:
        parts.append("Om något finns uppsidan mer i premiumspåret än i en snabb och säker flip.")
    else:
        parts.append("Objektet ligger ganska mitt emellan snabbflip och premiumcase, vilket ofta betyder att man ska vara extra kritisk.")

    # Datakälla / comps
    if value_source == "heuristic_only":
        parts.append("Värdet bygger främst på heuristik från titel och signaler, inte på stark lokal comp-data.")
    elif value_source == "blended":
        if comparable_count >= 6:
            parts.append("Bedömningen stöds delvis av flera liknande lokala annonser, vilket gör den något mer robust.")
        elif comparable_count >= 2:
            parts.append("Det finns viss lokal comp-data, men underlaget är fortfarande ganska tunt.")
        else:
            parts.append("Lokal comp-data finns, men den är tunn och ska inte tolkas som hårt marknadspris.")

    # Riskflaggor
    risk_messages = []
    if "generisk titel" in risk_flags:
        risk_messages.append("generisk titel")
    if "svagt underlag" in risk_flags:
        risk_messages.append("svagt underlag")
    if "samlingsannons" in risk_flags:
        risk_messages.append("samlingsannons")
    if "spelare ej identifierad" in risk_flags:
        risk_messages.append("spelare ej identifierad")
    if "låg specificitet" in risk_flags:
        risk_messages.append("låg specificitet")
    if "svag efterfrågan" in risk_flags:
        risk_messages.append("svag efterfrågan")
    if "hög numrering" in risk_flags:
        risk_messages.append("hög numrering")
    if "svag patch-signal" in risk_flags:
        risk_messages.append("svag patch-signal")

    if risk_messages:
        parts.append("Viktiga riskflaggor: " + ", ".join(risk_messages[:4]) + ".")

    # Säkerhet
    if confidence < 0.30:
        parts.append("Analysen är ganska osäker eftersom underlaget i titeln är tunt eller tvetydigt.")
    elif confidence < 0.50:
        parts.append("Analysen är medelosäker, så bild, skick och exakt kortvariant måste verifieras innan köp.")
    elif confidence < 0.70:
        parts.append("Analysen är hyggligt stabil, men fortfarande bara en uppskattning och inte ett facit.")
    else:
        parts.append("Titeln och signalerna är relativt tydliga, men även här måste bild och skick bekräfta caset.")

    # Särskild hårdhet för klassiska falska premium-toppar
    premium_words = ["the cup", "sp authentic", "dominion", "premier", "ultimate collection"]
    has_premium_title = any(word in title for word in premium_words)
    if has_premium_title and demand_tier in {"weak", "medium"}:
        parts.append("Premiumset i sig räcker inte här; utan stark spelarefterfrågan blir sådana kort ofta sämre flip än de först ser ut.")

    return " ".join(parts)