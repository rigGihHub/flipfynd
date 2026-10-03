"""Deliver trusted helper scripts in the app payload, without asset iframes."""
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=8)
def _register(runtime, name, javascript):
    from streamlit.components.v2 import component
    return component(name, js=javascript, isolate_styles=False)


def _changed():
    pass


def mount_inline(name, directory, *, key, data=None, reply=True):
    # Only repository-owned JavaScript is executable; user state stays in data.
    javascript = (Path(__file__).parent / directory / 'component.js').read_text(encoding='utf-8')
    from streamlit.runtime import exists, get_instance
    renderer = _register(get_instance() if exists() else None, name, javascript)
    kwargs = {'default': {'reply': None}, 'on_reply_change': _changed} if reply else {}
    result = renderer(key=key, data=data, height=0, **kwargs)
    return result.get('reply') if reply else None
