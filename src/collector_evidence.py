"""Auditable presentation of stored evidence; never creates a valuation."""
from datetime import datetime, timezone
from math import isfinite
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from src.card_parser import parse_card_features, clean_card_title
from src.shipping_truth import resolve_shipping


def number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (TypeError, ValueError):
        return None


def money(value, currency="SEK"):
    value = number(value)
    if value is None:
        return "Saknas"
    # Currency codes avoid Streamlit's dollar-delimited math rendering.
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " " + str(currency or "SEK")


def timestamp(value):
    if value in (None, ""):
        return "Okänd tidpunkt"
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(value, timezone.utc)
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("Europe/Stockholm")).strftime("%Y-%m-%d %H:%M %Z")
    except (TypeError, ValueError, OverflowError, OSError):
        return "Okänd tidpunkt"


def evidence_item(row):
    out = dict(row.get("_source_item") or row.get("source_item") or {})
    out.update({key: value for key, value in row.items() if key not in {"source_item", "_source_item"}})
    return out


def acquisition_breakdown(row, total_cost=None):
    item = evidence_item(row)
    scenario = item.get("asking_price_opportunity") or {}
    shipping = resolve_shipping(item)
    price = number(scenario.get("purchase_price", item.get("pris", item.get("price"))))
    freight = number(scenario.get("shipping", shipping["shipping"]))
    fee = number(scenario.get("buyer_protection_fee", item.get("buyer_protection_fee")))
    total = number(total_cost)
    if total is None:
        total = number(scenario.get("total_cost", item.get("analysis_total_cost", item.get("total_cost"))))
    known = bool(scenario.get("shipping_known", shipping["known"]))
    parts = [("Kortpris", price), ("Frakt" if known else "Antagen frakt", freight), ("Köparskydd", fee)]
    buffer = number(scenario.get("auction_buffer"))
    if buffer:
        parts.append(("Auktionsbuffert (antagande)", buffer))
    # Legacy snapshots may lack a fee field. Show the discrepancy without
    # pretending to know what the charge was or modifying the saved total.
    residual = None
    if total is not None and price is not None and freight is not None:
        delta = round(total - price - freight - (fee or 0) - (buffer or 0), 2)
        if abs(delta) > .01:
            residual = delta
            parts.append(("Övrig inköpskostnad (ej specificerad)", delta))
    return {"parts": parts, "total": total, "residual": residual,
            "verified": bool(item.get("purchase_cost_verified") or scenario.get("purchase_cost_verified"))}


def price_evidence(row):
    item = evidence_item(row)
    scenario = item.get("asking_price_opportunity") or {}
    context = item.get("ebay_active_context") or {}
    groups = [(scenario.get("comparisons") or [], "Begärt pris", scenario.get("fetched_at")),
              ([r for r in context.get("rows") or [] if r.get("asking_comparison_eligible")],
               "Begärt pris", context.get("fetched_at")),
              (item.get("comparable_details") or [], None, None),
              (item.get("premium_comp_hunter_exact") or [], None, None)]
    rows, seen = [], set()
    for candidates, kind, fetched in groups:
        for raw in candidates:
            if not isinstance(raw, dict):
                continue
            url = str(raw.get("url") or raw.get("lank") or "")
            parsed_url = urlsplit(url)
            if parsed_url.scheme not in {"https", "http"} or not parsed_url.netloc:
                continue
            key = (parsed_url.netloc.casefold(), parsed_url.path.rstrip("/"))
            if key in seen:
                continue
            seen.add(key)
            title = str(raw.get("title") or raw.get("titel") or "Jämförelsekort")
            fields = parse_card_features(title)
            state = str(raw.get("market_state") or "").casefold()
            evidence_kind = kind or ("SOLD · enligt sparat underlag" if state == "sold" else "Jämförelse · ej verifierad försäljning")
            value = raw.get("asking_price_sek")
            currency = "SEK" if value is not None else raw.get("currency") or "SEK"
            if value is None:
                value = raw.get("sold_price") if state == "sold" and raw.get("sold_price") is not None else raw.get("price")
            identity = " · ".join(str(x) for x in (
                fields.get("player_name"), fields.get("season"), fields.get("set_name"), fields.get("insert_name"),
                "#" + str(fields["card_number"]) if fields.get("card_number") else None,
                fields.get("parallel"), "/" + str(fields["serial_number"]) if fields.get("serial_number") else None,
                fields.get("grade")) if x)
            price_text = money(value, currency)
            if raw.get("asking_price_sek") is not None and raw.get("currency") not in (None, "", "SEK"):
                price_text += " (" + money(raw.get("price"), raw["currency"]) + ")"
            rows.append({"title": clean_card_title(title), "url": url, "kind": evidence_kind,
                         "price": price_text, "identity": identity or "Identitet saknas",
                         "condition": raw.get("condition") or raw.get("condition_text") or "Skick ej angivet",
                         "date": timestamp(raw.get("sold_at") or raw.get("date") or raw.get("fetched_at") or fetched),
                         "date_label": "Försäljningsdatum" if state == "sold" else "Kontrollerad",
                         "match": raw.get("match_label") or raw.get("match_quality") or "Enligt sparad analys"})
    return rows


def render_listing_review(row, *, total_cost=None):
    import streamlit as st
    item = evidence_item(row)
    checked = item.get("purchase_checked_at") or item.get("detail_enriched_at")
    st.caption("Annons senast kontrollerad: " + timestamp(checked))
    if item.get("analysed_at"):
        st.caption("Analys utförd: " + timestamp(item["analysed_at"]))
    with st.expander("Kalkyl och prisbevis", expanded=False):
        costs = acquisition_breakdown(item, total_cost)
        st.write("**Inköpskostnad**")
        for label, value in costs["parts"]:
            st.write(f"{label}: {money(value)}")
        st.write("**Total kostnad: " + money(costs["total"]) + "**")
        if not costs["verified"] or costs["residual"] is not None:
            st.caption("Kostnaden är ett sparat underlag. Kontrollera aktuellt pris, frakt och köparskydd i annonsen.")
        scenario = item.get("asking_price_opportunity") or {}
        breakdown = item.get("profit_breakdown") or {}
        if scenario.get("net_margin") is not None:
            st.write("**Försäljningsscenario · begärda priser**")
            st.write("Observerat begärt kortpris: " + money(scenario.get("observed_asking_price")))
            st.write("Antaget försäljningspris efter 15 % avdrag: " + money(scenario.get("reference_asking_price")))
            st.write("Antagen försäljningsavgift: " + money(scenario.get("selling_fee")))
            st.write("Emballage: " + money(scenario.get("packaging")))
            st.write("Nettoscenario: " + money(scenario.get("net_margin")))
            st.caption("Avgiftsantagande: 10 % (3–200 kr). Köparen antas betala vidarefrakten. Begärda priser fastställer inte marknadsvärdet.")
            if scenario.get("auction_current_bid"):
                st.info("Auktion: scenariot gäller endast om du vinner till det visade budet.")
        elif breakdown:
            st.write("**Försäljningskalkyl · " + ("verifierat underlag" if item.get("valuation_display_safe") else "modellantagande") + "**")
            for label, key in (("Försäljningspris", "resale_price"), ("Antagen försäljningsavgift", "selling_fee"),
                               ("Emballage", "packaging"), ("Vidarefrakt", "outbound_shipping_cost")):
                st.write(label + ": " + money(breakdown.get(key)))
            st.caption(str(breakdown.get("selling_fee_assumption") or "Avgiftsantagande saknas"))
            st.caption(str(breakdown.get("outbound_shipping_assumption") or "Fraktantagande saknas"))
        else:
            st.caption("Försäljningskostnader saknas i den sparade kalkylen. Ingen ny nettovinst räknas fram här.")
        if scenario.get("fx_date"):
            st.caption("Valutakurs till SEK: ECB " + str(scenario["fx_date"]))
        st.write("**Jämförelseannonser och försäljningar**")
        comparisons = price_evidence(item)
        if not comparisons:
            st.info("Inga klickbara prisbevis finns i det sparade resultatet. Kör en ny analys för att hämta underlag.")
        for comp in comparisons[:10]:
            st.link_button(comp["price"] + " · " + comp["title"] + " ↗", comp["url"])
            st.caption(comp["kind"] + " · " + comp["date_label"] + ": " + comp["date"])
            st.caption(comp["identity"] + " · " + str(comp["condition"]) + " · " + str(comp["match"]))


def snapshot_notice(snapshot, debug, active_count):
    debug = debug or {}
    count = debug.get("total_items")
    if count is None:
        count = debug.get("raw_total_items")
    count_text = str(int(number(count))) + " inlästa annonser" if number(count) is not None else "okänt antal inlästa annonser"
    date = timestamp((snapshot or {}).get("completed_at"))
    text = f"Sparad analys: {count_text} · slutförd {date}. Aktuell marknad: {active_count} annonser."
    if not active_count:
        text += " Marknadsarkivet saknas; resultaten nedan är från den sparade analysen. Läs in annonser för en ny sökning."
    else:
        text += " Priserna gäller respektive kontrolltidpunkt; nya annonser ändrar inte den sparade analysen."
    return text
