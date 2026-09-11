"""Card Hierarchy Engine: structural hobby context, never a price model."""
from __future__ import annotations

def _norm(v): return " ".join(str(v or "").casefold().split())

HOCKEY_ROLES = {
    ("upper deck series","young guns"):("FLAGSHIP_ROOKIE",90,"Flagship rookie-program"),
    ("sp authentic","future watch"):("PREMIUM_ROOKIE_AUTO",92,"Premium rookie/autograph-program"),
    ("the cup",""):("PREMIUM_RPA",96,"High-end rookie patch/autograph-program"),
    ("skybox metal universe","precious metal gems"):("ICONIC_PARALLEL_FAMILY",91,"Etablerad parallel/chase-familj"),
    ("o-pee-chee platinum","opc platinum parallels"):("CHROME_PARALLEL_FAMILY",78,"Parallel-fokuserad produktfamilj"),
}
FOOTBALL_ROLES = {
    ("topps chrome uefa",""):("CHROME_FLAGSHIP_FAMILY",86,"Chrome-baserad central samlarfamilj"),
    ("prizm football",""):("CHROME_FLAGSHIP_FAMILY",86,"Prizm-baserad central parallel/chase-familj"),
    ("topps finest uefa",""):("PREMIUM_CHROME_FAMILY",78,"Premium chrome/inserts-program"),
    ("topps merlin uefa",""):("CHROME_INSERT_FAMILY",74,"Chrome-baserad insert/parallel-familj"),
}

def _family_role(sport, product, program):
    role_map=FOOTBALL_ROLES if _norm(sport) in {"football","fotboll"} else HOCKEY_ROLES
    p,g=_norm(product),_norm(program)
    for (prod,prog),v in role_map.items():
        if p==prod and prog and g==prog: return v
    for (prod,prog),v in role_map.items():
        if p==prod and not prog: return v
    return None

def _category_role(signal):
    c=_norm(signal.get("category")); r=_norm(signal.get("rarity_signal")); run=signal.get("print_run")
    if isinstance(run,int) and run==1: return ("ONE_OF_ONE",98,"1/1-struktur")
    if c=="rookie_patch_auto": return ("ROOKIE_PATCH_AUTO",94,"Rookie patch autograph")
    if c=="rookie_auto": return ("ROOKIE_AUTOGRAPH",88,"Rookie autograph")
    if c in {"grail_program","case_hit","ssp_insert"} or "ultra_rare" in r or "case_level" in r:
        return ("CHASE_SSP",84,"SSP/case-hit-struktur")
    if c=="rookie_parallel": return ("ROOKIE_PARALLEL",80,"Rookie parallel")
    if c in {"autograph_program","autograph_parallel"}: return ("AUTOGRAPH_PROGRAM",72,"Autografprogram")
    if c in {"parallel","parallel_family"}:
        if isinstance(run,int) and run<=25: return ("LOW_NUMBERED_PARALLEL",82,f"Lågnumrerad parallel /{run}")
        return ("PARALLEL",62,"Parallel")
    if c=="rookie_program": return ("ROOKIE_PROGRAM",72,"Rookieprogram")
    if c in {"insert","memorabilia"}: return ("INSERT_OR_RELIC",48,"Insert/relic-program")
    return ("BASE_OR_UNCLASSIFIED",25,"Bas/oklassificerad struktur")

def build_card_hierarchy_engine(*, sport, signals=None, features=None):
    signals=[dict(s) for s in (signals or []) if isinstance(s,dict)]
    features=dict(features or {})
    candidates=[]; reasons=[]; traps=[]
    for s in signals[:12]:
        label=str(s.get("label") or "Okänd variant")
        fam=_family_role(sport,s.get("product_family"),s.get("program_family"))
        cat=_category_role(s)
        if fam:
            candidates.append((fam[1],fam[0],fam[2]))
            reasons.append(f"{label} ligger i {fam[2].lower()}.")
        candidates.append((cat[1],cat[0],cat[2]))
        if cat[1]>=72: reasons.append(f"{label}: {cat[2]}.")
    if not candidates:
        if features.get("is_rookie") and features.get("is_auto") and features.get("is_patch"):
            candidates=[(70,"UNVERIFIED_RPA_CLAIM","Rookie patch autograph-anspråk")]
            traps.append("RPA-termer räcker inte; program/set måste verifieras.")
        elif features.get("is_rookie") and features.get("is_auto"):
            candidates=[(62,"UNVERIFIED_ROOKIE_AUTO","Rookie autograph-anspråk")]
            traps.append("Rookie-auto utan verifierat program är inte automatiskt ett centralt rookie-kort.")
        elif features.get("is_rookie"):
            candidates=[(45,"GENERIC_ROOKIE","Generisk rookie-signal")]
            traps.append("RC/rookie i rubriken är inte samma sak som ett etablerat nyckelrookieprogram.")
        elif features.get("is_auto"):
            candidates=[(42,"GENERIC_AUTO","Generisk autograf-signal")]
            traps.append("Autograf i sig säger inget om spelarens efterfrågan eller programmets betydelse.")
        else:
            candidates=[(20,"BASE_OR_UNKNOWN","Bas/okänd hobbyhierarki")]
    score,role,label=max(candidates,key=lambda x:x[0])
    identity=float(features.get("identity_confidence_score") or 0)
    if identity<50:
        score=min(score,64)
        traps.append("Svag kortidentitet gör program-/variantplaceringen osäker.")
    if role in {"BASE_OR_UNCLASSIFIED","BASE_OR_UNKNOWN"}:
        traps.append("Vanlig bas/oklassificerad struktur får inte premium enbart på spelarnamnet.")
    if score>=90: tier,tier_label="TIER_A","Central premium-/rookie-/chase-hierarki"
    elif score>=78: tier,tier_label="TIER_B","Stark samlarhierarki"
    elif score>=60: tier,tier_label="TIER_C","Relevant samlarprogram"
    elif score>=40: tier,tier_label="TIER_D","Selektivt program – kräver stark spelare/marknad"
    else: tier,tier_label="TIER_E","Bas/okänd struktur"
    return {
        "score":int(round(score)),"tier":tier,"tier_label":tier_label,"role":role,"role_label":label,
        "reasons":list(dict.fromkeys(reasons))[:6],"hobby_traps":list(dict.fromkeys(traps))[:5],
        "safe_for_valuation":False,"creates_market_value":False,"creates_buy_decision":False,
        "note":"Hobbyhierarkin beskriver korttypens/programmens samlarroll, inte pris. Verifierade SOLD-comps krävs fortfarande."
    }
