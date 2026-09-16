"""Show asking-price arithmetic separately from verified SOLD valuations."""
from __future__ import annotations


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
    if data.get("status") not in {"POSSIBLE_FIND", "NO_MARGIN"}:
        return
    st.markdown("**Möjligt fynd · begärda priser**" if data.get("possible_find") else "**Ingen marginal mot begärda priser**")
    shipping_label = "frakt" if data["shipping_known"] else "antagen frakt"
    st.write(
        f"Inköp {data['purchase_price']:.0f} kr + {shipping_label} {data['shipping']:.0f} kr "
        f"= **{data['total_cost']:.0f} kr totalt**"
    )
    st.write(
        f"Lägsta jämförbara begärda kortpris: **{data['reference_asking_price']:.0f} kr** · "
        f"{data['comparison_count']} annonser"
    )
    roi = _net_roi(data)
    roi_text = f" · **{roi:+.0f}% möjlig avkastning**" if roi is not None else ""
    st.write(
        f"Avgift {data['selling_fee']:.0f} kr + emballage {data['packaging']:.0f} kr · "
        f"**Möjlig nettovinst {data['net_margin']:+g} kr**{roi_text}"
    )
    st.caption(
        "Detta är ett scenario mot aktiva begärda priser, inte ett verifierat marknadsvärde eller en genomförd försäljning."
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


def render_asking_price_shortlist(results):
    import streamlit as st

    rows = [row for row in results or [] if (row.get("asking_price_opportunity") or {}).get("possible_find")]
    rows.sort(key=_shortlist_rank, reverse=True)
    if not rows:
        return
    st.markdown("### Möjliga fynd mot begärda priser")
    st.caption("Sorteras främst på möjlig nettovinst. Aktivt annonspris är research, inte SOLD-evidens.")
    for row in rows[:5]:
        st.markdown(f"#### {row.get('titel') or row.get('title') or 'Kortannons'}")
        render_asking_price_opportunity(row["asking_price_opportunity"])
        url = row.get("lank") or row.get("url")
        if url:
            st.link_button("Öppna annonsen på Tradera ↗", url)
