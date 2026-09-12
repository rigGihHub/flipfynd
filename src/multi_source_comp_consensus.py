"""Multi-source exact sold-comp consensus for FlipFynd.

This module never scrapes remote websites and never turns a price guide into a
realised sale. It only reconciles exact, explicitly sold rows already present in
FlipFynd's sold library. Source weighting is deliberately modest: Tradera gets a
small local-market relevance boost for SEK sales, while price-guide-only sources
are excluded unless the row itself carries explicit individual-sale evidence.
"""
from __future__ import annotations

from statistics import median
from typing import Iterable

from src.exact_comp_hunter import classify_comp


DIRECT_SOURCE_WEIGHTS = {
    "tradera": 1.15,
    "tradera verifierade avslut": 1.15,
    "ebay": 1.00,
    "ebay sold": 1.00,
    "ebay product research": 1.05,
    "fanatics collect": 1.00,
    "card ladder": 0.95,
    "comc": 0.90,
    "130 point": 0.85,
    "130point": 0.85,
}

GUIDE_ONLY_TOKENS = ("sportscardspro", "price guide", "guidevärde", "market estimate")


def _norm(value):
    return " ".join(str(value or "").casefold().strip().split())


def _price_sek(record):
    for key in ("sold_total_price_sek", "sold_price_sek"):
        value=record.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError,ValueError):
                pass
    currency=_norm(record.get("currency") or "sek")
    if currency in {"sek","kr","sek kr"}:
        for key in ("sold_total_price","sold_price","price","pris"):
            value=record.get(key)
            if value not in (None, ""):
                try:
                    return float(value)
                except (TypeError,ValueError):
                    pass
    return None


def _source_name(record):
    return str(record.get("source_platform") or record.get("platform") or record.get("source") or "okänd källa")


def _has_individual_sale_evidence(record):
    evidence=_norm(record.get("source_sale_evidence"))
    status=_norm(record.get("sale_status") or record.get("status"))
    sold=record.get("sold") is True or _norm(record.get("sold")) in {"true","1","yes","ja","sold","såld"}
    return bool(evidence or sold or "sold" in status or "såld" in status)


def _source_weight(record):
    source=_norm(_source_name(record))
    if any(token in source for token in GUIDE_ONLY_TOKENS) and not _has_individual_sale_evidence(record):
        return 0.0
    for key,weight in DIRECT_SOURCE_WEIGHTS.items():
        if key in source:
            return weight
    return 0.80


def _weighted_median(pairs):
    pairs=sorted((float(v),float(w)) for v,w in pairs if w>0)
    if not pairs:
        return None
    total=sum(w for _,w in pairs)
    cutoff=total/2
    running=0.0
    for value,weight in pairs:
        running+=weight
        if running>=cutoff:
            return value
    return pairs[-1][0]


def build_multi_source_consensus(identity: dict, records: Iterable[dict] | None) -> dict:
    accepted=[]
    rejected=[]
    for record in records or []:
        if not isinstance(record,dict):
            continue
        classified=classify_comp(identity,record)
        if classified.get("tier")!="EXACT" or not classified.get("sold"):
            continue
        price=_price_sek(record)
        if price is None or price<=0:
            rejected.append({"source":_source_name(record),"reason":"saknar säkert SEK-pris"})
            continue
        weight=_source_weight(record)
        if weight<=0:
            rejected.append({"source":_source_name(record),"reason":"prisguide utan verifierad individuell sale"})
            continue
        accepted.append({
            "source":_source_name(record),
            "price_sek":round(price,2),
            "weight":weight,
            "sold_at":record.get("sold_at") or record.get("sold_date") or record.get("date"),
            "url":record.get("url") or record.get("lank"),
        })

    prices=[r["price_sek"] for r in accepted]
    by_source={}
    for row in accepted:
        by_source.setdefault(row["source"],[]).append(row["price_sek"])
    source_rows=[
        {"source":source,"count":len(values),"median_sek":round(median(values),2)}
        for source,values in sorted(by_source.items(),key=lambda kv:(-len(kv[1]),kv[0].casefold()))
    ]
    weighted=_weighted_median([(r["price_sek"],r["weight"]) for r in accepted])
    local=[r["price_sek"] for r in accepted if "tradera" in _norm(r["source"])]
    intl=[r["price_sek"] for r in accepted if "tradera" not in _norm(r["source"])]
    local_med=median(local) if local else None
    intl_med=median(intl) if intl else None
    divergence=None
    if local_med and intl_med:
        divergence=abs(local_med-intl_med)/max((local_med+intl_med)/2,1)*100

    if len(accepted)>=5 and len(by_source)>=2:
        confidence="HÖG"
    elif len(accepted)>=2:
        confidence="MEDEL"
    elif accepted:
        confidence="LÅG"
    else:
        confidence="INGET UNDERLAG"

    return {
        "exact_sold_count":len(accepted),
        "source_count":len(by_source),
        "median_sek":round(median(prices),2) if prices else None,
        "weighted_median_sek":round(weighted,2) if weighted is not None else None,
        "tradera_median_sek":round(local_med,2) if local_med is not None else None,
        "international_median_sek":round(intl_med,2) if intl_med is not None else None,
        "local_vs_international_divergence_pct":round(divergence,1) if divergence is not None else None,
        "confidence":confidence,
        "sources":source_rows,
        "accepted":accepted,
        "rejected":rejected,
        "note":"Konsensus använder bara exact + explicit sålda poster. Tradera får en liten lokal relevansvikt; prisguider räknas inte som sales utan individuell sale-evidens.",
    }
