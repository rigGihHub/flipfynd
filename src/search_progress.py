"""Request/phase progress metadata, independent of the Streamlit connection."""
from contextlib import contextmanager
from contextvars import ContextVar
from threading import RLock
import time

_CURRENT = globals().get("_CURRENT") or ContextVar("search_progress", default=None)


@contextmanager
def track_progress(callback):
    state = {"callback": callback, "lock": RLock(), "started": time.monotonic(),
             "phase": "Förbereder sökning", "requests": 0, "request_seconds": 0.0}
    token = _CURRENT.set(state)
    try:
        report_phase("Förbereder sökning")
        yield
    finally:
        _CURRENT.reset(token)


def report_phase(phase, *, checked=None, total=None, unit=None, fraction=None, page=None):
    state = _CURRENT.get()
    if state is None:
        return
    with state["lock"]:
        if state.get("phase") != phase:
            state.pop("checked", None)
            state.pop("total", None)
            state["phase_started"] = time.monotonic()
        state["phase"] = phase
        if checked is not None:
            state["checked"] = checked
        if total is not None:
            state["total"] = total
        if unit is not None:
            state["unit"] = unit
        if fraction is not None:
            state["fraction"] = max(0, min(.99, fraction))
        payload = {key: state[key] for key in ("phase", "requests", "checked", "total", "unit", "fraction") if key in state}
        payload["elapsed_seconds"] = round(time.monotonic() - state["started"], 1)
        if page is not None:
            payload["page"] = page
        if state.get("total") and state.get("checked", 0) >= 1:
            # Measured phase throughput includes network, rate pacing and CPU.
            elapsed = time.monotonic() - state.get("phase_started", state["started"])
            payload["eta_seconds"] = round(elapsed / state["checked"] * max(0, state["total"] - state["checked"]))
        state["callback"](payload)


def begin_phase(phase, total, *, unit=None):
    state = _CURRENT.get()
    if state is not None:
        with state["lock"]:
            state["phase_started"] = time.monotonic()
            report_phase(phase, checked=0, total=total, unit=unit)


def record_request(seconds):
    state = _CURRENT.get()
    if state is not None:
        with state["lock"]:
            state["requests"] += 1
            state["request_seconds"] += max(0, seconds)
            report_phase(state["phase"])


def _duration(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60} min {seconds % 60} s" if seconds >= 60 else f"{seconds} s"


def progress_text(job):
    progress = job.get("progress") or {}
    elapsed = max(0, int(time.time() - job.get("started_at", time.time())))
    label = progress.get("phase") or "Förbereder sökning"
    total = progress.get("total") or 0
    checked = progress.get("checked") or 0
    detail = f"{checked} / {total} {progress.get("unit") or "kort"} · " if total else ""
    if progress.get("page"):
        detail += f"sida {progress["page"]} · "
    detail += f"{progress.get('requests', 0)} eBay-anrop gjorda · tid hittills: {_duration(elapsed)}"
    eta = progress.get("eta_seconds")
    if total and checked >= total and job.get('status') == 'RUNNING':
        detail += ' · delsteget klart; omgången fortsätter'
    elif eta is not None:
        detail += f" · cirka {_duration(eta)} kvar i detta steg"
    else:
        detail += " · beräknar återstående tid"
    if job.get("params", {}).get("kind") == "seller" and elapsed >= 20:
        detail += " · externa svar kan förlänga tiden"
    return label, detail, progress.get("fraction", min(.99, checked / total) if total else 0.0)


def render_search_progress(job):
    from html import escape
    import streamlit as st
    label, detail, fraction = progress_text(job)
    # The app uses a dark surface even when the browser selects a light theme.
    # Explicit text colours keep the phase and ETA readable in both themes.
    st.markdown('<div style="color:#f7eee4;background:#17212b;border-left:3px solid #e2a45c;'
                'padding:12px 14px;margin:8px 0"><strong>' + escape(label)
                + '</strong><div style="margin-top:5px">' + escape(detail) + '</div></div>',
                unsafe_allow_html=True)
    st.progress(fraction)
