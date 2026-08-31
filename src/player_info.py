from src.card_parser import parse_card_features

PLAYER_DB = {
    "Connor Bedard": {
        "age": 20,
        "career_summary": "Toppnamn bland moderna hockeykort. Extrem uppmärksamhet som rookie och fortsatt stark efterfrågan i hobby/flip.",
    },
    "Macklin Celebrini": {
        "age": 19,
        "career_summary": "Mycket hett ungt namn i hobby just nu. Stark chase-faktor i moderna produkter.",
    },
    "Ivan Demidov": {
        "age": 20,
        "career_summary": "Mycket hajpat prospectsnamn med stark kortuppsida när marknaden är het.",
    },
    "Connor McDavid": {
        "age": 29,
        "career_summary": "Etablerad superstjärna och ett av de mest likvida moderna namnen på kortmarknaden.",
    },
    "Wayne Gretzky": {
        "age": 65,
        "career_summary": "Legendstatus. Ikoniskt namn med stadig långsiktig efterfrågan i hockeykort.",
    },
    "Sidney Crosby": {
        "age": 38,
        "career_summary": "Legend på modern sida. Ofta stark efterfrågan, särskilt på viktiga rookie- och premiumkort.",
    },
    "Alex Ovechkin": {
        "age": 40,
        "career_summary": "Historiskt starkt samlarnamn med stadig efterfrågan, särskilt på nyckelkort och viktiga inserts.",
    },
    "Nathan MacKinnon": {
        "age": 30,
        "career_summary": "Stjärnspelare med god marknadsrespekt, även om flipvärdet varierar mellan set och korttyp.",
    },
    "Cale Makar": {
        "age": 27,
        "career_summary": "Starkt modernt namn, särskilt i premium- och rookie-relaterade kort.",
    },
    "Auston Matthews": {
        "age": 28,
        "career_summary": "Högt profilerat namn med bra samlarintresse, men flipstyrkan beror mycket på set och pris.",
    },
    "Ryan Leonard": {
        "age": 21,
        "career_summary": "Relevant ungt namn i prospects-segmentet med viss hobbyhetta.",
    },
    "Lane Hutson": {
        "age": 22,
        "career_summary": "Modernt ungt namn som kan vara hett i rätt produkt och rätt prismässig nivå.",
    },
    "Adam Fantilli": {
        "age": 21,
        "career_summary": "Ungt namn med intresse i hobby, särskilt när marknaden är het och kortet är rätt typ.",
    },
    "Artem Levshunov": {
        "age": 20,
        "career_summary": "Prospectnamn med samlarintresse, men värdet är starkt beroende av hype och timing.",
    },
    "William Nylander": {
        "age": 30,
        "career_summary": "Välkänt namn med stabilt intresse, men inte alltid optimalt som snabbflip i premiumsegmentet.",
    },
    "Elias Pettersson": {
        "age": 27,
        "career_summary": "Bra spelare med visst samlarintresse, men premiumkort kräver ofta försiktigare flipbedömning.",
    },
    "Juraj Slafkovsky": {
        "age": 22,
        "career_summary": "Fortfarande intressant ungt namn, men efterfrågan varierar tydligt med form, hype och set.",
    },
    "Rasmus Dahlin": {
        "age": 26,
        "career_summary": "Respekterat namn med viss samlarstyrka, men inte automatiskt stark quick flip i alla premiumset.",
    },
    "Nils Höglander": {
        "age": 25,
        "career_summary": "Kan ha visst samlarintresse, men är normalt inte ett av de hetaste flipnamnen i premiumsegmentet.",
    },
    "Nils Hoglander": {
        "age": 25,
        "career_summary": "Kan ha visst samlarintresse, men är normalt inte ett av de hetaste flipnamnen i premiumsegmentet.",
    },
}


ALIASES = {
    "Connor Mcdavid": "Connor McDavid",
    "Nathan Mackinnon": "Nathan MacKinnon",
    "Nils Hoglander": "Nils Hoglander",
}


def normalize_player_name(name):
    if not name:
        return None
    clean = str(name).strip()
    return ALIASES.get(clean, clean)


def get_player_info_from_title(title: str) -> dict:
    if not title or not str(title).strip():
        return {
            "success": False,
            "error": "Ingen titel att analysera.",
            "query": "",
            "matched_title": "",
            "match_confidence": "low",
            "age": None,
            "career_summary": None,
            "note": "Spelarinformation visas bara när spelaren kan identifieras säkert från titeln.",
        }

    features = parse_card_features(title)
    player_name = normalize_player_name(features.get("player_name"))

    if not player_name:
        return {
            "success": False,
            "error": "Kunde inte identifiera någon spelare säkert från titeln.",
            "query": title,
            "matched_title": "",
            "match_confidence": "low",
            "age": None,
            "career_summary": None,
            "note": "Ingen spelare identifierades med tillräcklig säkerhet.",
        }

    player_info = PLAYER_DB.get(player_name)
    if not player_info:
        return {
            "success": False,
            "error": f"Spelaren '{player_name}' identifierades men finns inte i den lokala spelardatabasen ännu.",
            "query": title,
            "matched_title": player_name,
            "match_confidence": "medium",
            "age": None,
            "career_summary": None,
            "note": "Ingen extern chansning gjordes. Lägg hellre till spelaren i databasen än att få fel träff.",
        }

    return {
        "success": True,
        "error": None,
        "query": title,
        "matched_title": player_name,
        "match_confidence": "high",
        "age": player_info.get("age"),
        "career_summary": player_info.get("career_summary"),
        "note": "Spelarinformationen bygger på säker identifiering från titeln och en lokal databas, inte på lös webbgissning.",
    }