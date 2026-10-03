"""Show asking-price arithmetic separately from verified SOLD valuations."""
from __future__ import annotations
from math import isfinite
from urllib.parse import urlsplit
import re

MINIMUM_FIND_PROFIT = 35.0
MINIMUM_FIND_ROI = 15.0


def _net_roi(data):
    """Return scenario ROI on the complete acquisition cost, never a SOLD ROI."""
    try:
        total_cost = float(data.get("total_cost") or 0)
        margin = float(data.get("net_margin") or 0)
    except (TypeError, ValueError):
        return None
    if total_cost <= 0:
        return None
    return margin / total_cost * 100.0


def render_asking_price_opportunity(opportunity):
    import streamlit as st

    data = opportunity or {}
    if data.get("status") not in {"POSSIBLE_FIND", "NO_MARGIN", "RESEARCH_SINGLE_ACTIVE"}:
        return
    if data.get("status") == "RESEARCH_SINGLE_ACTIVE":
        st.markdown("**Osäkert prisuppslag · endast 1 jämförelsepris**")
    elif data.get("possible_find") and not practical_price_suggestions([{'asking_price_opportunity': data}]):
        st.markdown("**Positivt scenario · liten marginal**")
    elif data.get("possible_find"):
        st.markdown("**Möjligt fynd · svagt underlag (1 exakt jämförelse)**" if data.get("weak_find_signal") else "**Möjligt fynd · begärda priser**")
    else:
        st.markdown("**Ingen marginal mot begärda priser**")
    shipping_label = "frakt" if data["shipping_known"] else "antagen frakt"
    st.write(
        f"Inköp {data['purchase_price']:.0f} kr + {shipping_label} {data['shipping']:.0f} kr "
        + (f"+ köparskydd {data['buyer_protection_fee']:.0f} kr " if data.get('buyer_protection_fee') else "")
        + (f"+ budmarginal {data['auction_buffer']:.0f} kr " if data.get('auction_buffer') else "")
        +
        f"= **{data['total_cost']:.0f} kr totalt**"
    )
    if not data.get("purchase_cost_verified"):
        st.caption("Inköpskostnaden är inte kontrollerad mot annonsen; frakt och eventuellt köparskydd behöver bekräftas.")
    if data.get("auction_current_bid"):
        st.info("Auktion: nettovinsten gäller om du vinner på det visade budet. Ett högre slutbud minskar vinsten.")
    if data.get("condition_warning"):
        st.warning("Säljaren beskriver slitage/EX-skick. Jämförelsepriset kan avse bättre skick; kontrollera bilderna och räkna med lägre försäljningspris.")
    st.write(
        f"Lägsta jämförbara begärda kortpris: **{data.get('observed_asking_price', data['reference_asking_price']):.2f} kr** · "
        f"{data['comparison_count']} annonser"
    )
    st.write(f"Försäljningsscenario efter 15 % avdrag: **{data['reference_asking_price']:.2f} kr**")
    roi = _net_roi(data)
    roi_text = f" · **{roi:+.0f}% möjlig avkastning**" if roi is not None else ""
    st.write(
        f"Avgift {data['selling_fee']:.0f} kr + emballage {data['packaging']:.0f} kr · "
        f"**Möjlig nettovinst {data['net_margin']:+g} kr**{roi_text}"
    )
    st.caption(
        ("Endast en exakt aktiv jämförelse: signalen kan vara intressant men är osäker och fastställer inte marknadsvärdet."
         if data.get("weak_find_signal")
         else "Detta är ett scenario mot aktiva begärda priser, inte ett verifierat marknadsvärde eller en genomförd försäljning.")
    )
    st.caption(data["note"])
    if data.get("fx_date"):
        st.caption(f"Omräknat till SEK med ECB:s referenskurs {data['fx_date']}.")
    if data.get("fetched_at"):
        st.caption(f"Jämförelseannonser hämtade {data['fetched_at'][:16].replace('T', ' ')} UTC.")
    with st.expander("Visa jämförelseannonser"):
        for comparison in data.get("comparisons") or []:
            st.link_button(
                f"{comparison['asking_price_sek']:.0f} kr · {comparison.get('title') or 'eBay-annons'} ↗",
                comparison["url"],
            )


def _shortlist_rank(row):
    data = row.get("asking_price_opportunity") or {}
    margin = float(data.get("net_margin") or 0)
    roi = _net_roi(data)
    # Absolute profit remains primary, but ROI breaks ties and is shown to the
    # user so a tiny nominal spread cannot masquerade as a major bargain.
    return margin, roi if roi is not None else float("-inf")


def positive_price_suggestions(results, research_leads=None):
    """Rank all positive scenarios without upgrading their evidence status."""
    candidates = list(results or []) + [
        {"titel": lead.get("title"), "lank": lead.get("url"), "asking_price_opportunity": lead.get("scenario") or {}}
        for lead in research_leads or [] if isinstance(lead, dict)
    ]
    rows, seen = [], set()
    for row in candidates:
        data = row.get("asking_price_opportunity") or {}
        try:
            margin = float(data.get("net_margin"))
        except (TypeError, ValueError):
            continue
        if not isfinite(margin) or margin < 1 or not (
                data.get("possible_find") or data.get("status") == "RESEARCH_SINGLE_ACTIVE"):
            continue
        url = str(row.get("lank") or row.get("url") or "")
        parts = urlsplit(url)
        key = (parts.netloc, parts.path) if url else str(row.get("titel") or row.get("title") or "")
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return sorted(rows, key=_shortlist_rank, reverse=True)


def practical_price_suggestions(results, research_leads=None):
    """Separate a meaningful resale edge from a merely positive calculation."""
    return [row for row in positive_price_suggestions(results, research_leads)
            if row['asking_price_opportunity']['net_margin'] >= MINIMUM_FIND_PROFIT
            and (roi := _net_roi(row['asking_price_opportunity'])) is not None
            and isfinite(roi) and roi >= MINIMUM_FIND_ROI]


def meaningful_opportunity_candidates(results):
    """Keep weak known margins out of ordinary Top 5, retaining unknown cases."""
    return [row for row in results or []
            if (row.get('asking_price_opportunity') or {}).get('net_margin') is None
            or str(row.get('beslut') or '').startswith('KÖP')
            or practical_price_suggestions([row])]


def render_asking_price_shortlist(results, *, heading="Möjliga fynd med meningsfull marginal", research_leads=None):
    import streamlit as st

    all_positive = positive_price_suggestions(results, research_leads)
    practical = practical_price_suggestions(results, research_leads)
    rows = [row for row in practical if row['asking_price_opportunity'].get('possible_find')
            and int(row['asking_price_opportunity'].get('comparison_count') or 0) >= 2]
    single = [row for row in practical if row not in rows]
    small = [row for row in all_positive if row not in practical]
    if not all_positive:
        return
    if rows:
        st.markdown("### " + heading)
        st.caption(f"{len(rows)} möjliga fynd · minst {MINIMUM_FIND_PROFIT:g} kr netto och {MINIMUM_FIND_ROI:g}% avkastning efter alla kostnader · "
                   "minst 2 exakta jämförelseannonser. Störst netto visas först. Begärda priser är osäkert underlag.")
    def render_row(row):
        st.markdown(f"#### {row.get('titel') or row.get('title') or 'Kortannons'}")
        display_data = dict(row["asking_price_opportunity"])
        # Older saved searches can call a hybrid listing "Köp nu" even though
        # their calculation used its lower current bid. Keep that distinction
        # visible without changing or rerunning the saved calculation.
        if re.search(r"eller\s+köp\s+nu", str(row.get("titel") or row.get("title") or ""), re.I):
            display_data["auction_current_bid"] = True
        render_asking_price_opportunity(display_data)
        url = row.get("lank") or row.get("url")
        if url:
            st.link_button("Öppna annonsen på Tradera ↗", url)
    for row in rows[:5]:
        render_row(row)
    if len(rows) > 5:
        with st.expander(f"Visa övriga {len(rows) - 5} möjliga fynd"):
            for row in rows[5:]:
                render_row(row)
    if single:
        with st.expander(f"{len(single)} prisuppslag med bara ett jämförelsepris – behöver mer underlag"):
            for row in single:
                render_row(row)
    if small:
        st.caption(f"{len(small)} positiva scenarier når inte fyndkravet: minst {MINIMUM_FIND_PROFIT:g} kr netto och {MINIMUM_FIND_ROI:g}% avkastning.")
        with st.expander(f"Visa små marginaler ({len(small)})"):
            for row in small:
                render_row(row)
