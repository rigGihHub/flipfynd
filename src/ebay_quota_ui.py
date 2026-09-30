"""Human-readable provider quotas, including their actual reset time."""
from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo
import time


def counter_details(quota, *, now=None):
    quota = quota or {}
    now = time.time() if now is None else now
    rates = [r for r in quota.get("rates", []) if r.get("applies_to_search")
             and r.get("reset_at", 0) > now]
    if not rates:
        return None
    rate = min(rates, key=lambda r: r["remaining"])
    reset = datetime.fromtimestamp(rate["reset_at"], ZoneInfo("Europe/Stockholm"))
    checked = quota.get("last_check")
    checked_text = datetime.fromtimestamp(checked, ZoneInfo("Europe/Stockholm")).strftime("%H:%M") if checked else None
    return {"remaining": rate["remaining"], "limit": rate["limit"],
            "reset": reset.strftime("%d/%m kl. %H:%M"), "checked": checked_text,
            "stale": quota.get("status") != "OK"}


def render_quota_counter(quota):
    import streamlit as st
    details = counter_details(quota)
    if details:
        remaining = f"{details['remaining']:,}".replace(",", " ")
        limit = f"{details['limit']:,}".replace(",", " ")
        title = f"eBay-anrop kvar: {remaining} / {limit}"
        note = f"Återställs {details['reset']} svensk tid."
        if details["checked"]:
            note += f" Kontrollerat kl. {details['checked']}."
        if details["stale"]:
            note += " Senast kända antal – aktuell kvot kunde inte hämtas."
    else:
        title = "eBay-anrop kvar: okänt"
        note = "Antalet kunde inte hämtas från eBay."
    st.markdown('<div style="color:#f7eee4;background:#17212b;border-left:3px solid #e2a45c;'
                'padding:12px 14px;margin:8px 0"><strong style="font-size:1.15rem">'
                + escape(title) + '</strong><div style="margin-top:4px;font-size:.9rem">'
                + escape(note) + '</div></div>', unsafe_allow_html=True)


def quota_lines(quota):
    quota = quota or {}
    lines = []
    for rate in quota.get("rates", []):
        if not rate.get("applies_to_search"):
            continue
        reset = datetime.fromtimestamp(rate["reset_at"], ZoneInfo("Europe/Stockholm"))
        window = rate["timeWindow"]
        label = "dygn" if window == 86400 else f"{window} sekunder"
        lines.append(f"{rate['resource']}: {rate['remaining']} av {rate['limit']} anrop kvar / {label}. "
                     f"Återställs {reset:%Y-%m-%d %H:%M:%S} svensk tid.")
    until = max([quota.get("paused_until", 0), *[r["reset_at"] for r in quota.get("rates", [])
        if r.get("applies_to_search") and r.get("remaining") == 0]])
    if until > time.time():
        reset = datetime.fromtimestamp(until, ZoneInfo("Europe/Stockholm"))
        lines.append(f"Prisanrop pausade till {reset:%Y-%m-%d %H:%M:%S} svensk tid.")
    if quota.get("status") not in {None, "OK"}:
        lines.append("eBays kvotkontroll: " + str(quota["status"]) +
                     (f" (HTTP {quota['http_status']})" if quota.get("http_status") else ""))
    return lines


def render_quota_status(quota, error_ids=None):
    import streamlit as st
    for line in quota_lines(quota):
        st.markdown('<div style="color:#f7eee4;background:#17212b;border-left:3px solid #e2a45c;padding:10px 14px;margin:8px 0">' + escape(line) + '</div>', unsafe_allow_html=True)
    if quota and quota.get("status") == "NO_QUOTA_DATA":
        st.caption("Kvotendpointens HTTP-status: " + str(quota.get("http_status", "okänd")))
        st.json(quota.get("provider_metadata", []), expanded=False)
    if error_ids:
        st.caption("eBays felkoder: " + ", ".join(error_ids))
