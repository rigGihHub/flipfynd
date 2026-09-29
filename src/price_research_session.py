"""Deduplicate identical requests inside one analysis, never across searches."""
from concurrent.futures import Future
from contextvars import ContextVar
from copy import deepcopy
from functools import wraps
from threading import Lock

_CURRENT = ContextVar("price_research_session", default=None)


def price_research_run(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        token = _CURRENT.set({"lock": Lock(), "requests": {}})
        try:
            return fn(*args, **kwargs)
        finally:
            _CURRENT.reset(token)
    return wrapped


def fetch_once(key, fn):
    session = _CURRENT.get()
    if session is None:
        return fn()
    with session["lock"]:
        future = session["requests"].get(key)
        owner = future is None
        if owner:
            future = Future()
            session["requests"][key] = future
    if owner:
        try:
            future.set_result(fn())
        except Exception as exc:
            future.set_exception(exc)
    return deepcopy(future.result())
