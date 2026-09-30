"""Human-readable provider quotas, including their actual reset time."""
from datetime import datetime
from zoneinfo import ZoneInfo
import time


def quota_lines(quota):
    quota = quota or {}
    lines = []
    for rate in quota.get("rates", []):
        reset = datetime.fromtimestamp(rate["reset_at"], ZoneInfo("Europe/Stockholm"))
        window = rate["timeWindow"]
        label = "dygn" if window == 86400 else f"{window} sekunder"
        lines.append(f"{rate['resource']}: {rate['remaining']} av {rate['limit']} anrop kvar / {label}. "
                     f"Återställs {reset:%Y-%m-%d %H:%M:%S} svensk tid.")
    if quota.get("paused_until", 0) > time.time():
        reset = datetime.fromtimestamp(quota["paused_until"], ZoneInfo("Europe/Stockholm"))
        lines.append(f"Prisanrop pausade till {reset:%Y-%m-%d %H:%M:%S} svensk tid.")
    if quota.get("status") not in {None, "OK"}:
        lines.append("eBays kvotkontroll: " + str(quota["status"]) +
                     (f" (HTTP {quota['http_status']})" if quota.get("http_status") else ""))
    return lines


def render_quota_status(quota, error_ids=None):
    import streamlit as st
    for line in quota_lines(quota):
        st.write(line)
    if quota and quota.get("status") == "NO_QUOTA_DATA":
        st.caption("Kvotendpointens HTTP-status: " + str(quota.get("http_status", "okänd")))
        st.json(quota.get("provider_metadata", []), expanded=False)
    if error_ids:
        st.caption("eBays felkoder: " + ", ".join(error_ids))
