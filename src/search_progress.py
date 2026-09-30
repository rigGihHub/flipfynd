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


def report_phase(phase, *, checked=None, total=None):
    state = _CURRENT.get()
    if state is None:
        return
    with state["lock"]:
        state["phase"] = phase
        if checked is not None:
            state["checked"] = checked
        if total is not None:
            state["total"] = total
        payload = {key: state[key] for key in ("phase", "requests", "checked", "total") if key in state}
        payload["elapsed_seconds"] = round(time.monotonic() - state["started"], 1)
        if state.get("total") and state.get("checked", 0) >= 3:
            # Measured phase throughput includes network, rate pacing and CPU.
            elapsed = time.monotonic() - state.get("phase_started", state["started"])
            payload["eta_seconds"] = round(elapsed / state["checked"] * max(0, state["total"] - state["checked"]))
        state["callback"](payload)


def begin_phase(phase, total):
    state = _CURRENT.get()
    if state is not None:
        with state["lock"]:
            state["phase_started"] = time.monotonic()
            report_phase(phase, checked=0, total=total)


def record_request(seconds):
    state = _CURRENT.get()
    if state is not None:
        with state["lock"]:
            state["requests"] += 1
            state["request_seconds"] += max(0, seconds)


def progress_text(job):
    progress = job.get("progress") or {}
    elapsed = max(0, int(time.time() - job.get("started_at", time.time())))
    label = progress.get("phase") or "Förbereder sökning"
    total = progress.get("total") or 0
    checked = progress.get("checked") or 0
    detail = f"{checked} / {total} kort · " if total else ""
    detail += f"{progress.get('requests', 0)} eBay-anrop gjorda · {elapsed // 60} min {elapsed % 60} s"
    eta = progress.get("eta_seconds")
    if eta is not None:
        detail += f" · cirka {max(1, round(eta / 60))} min kvar i detta steg"
    else:
        detail += " · beräknar återstående tid"
    return label, detail, min(.99, checked / total) if total else 0.0


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
