"""Browser-side elapsed time; never polls or reruns the Python app."""
from pathlib import Path


def render_loading_status():
    from streamlit.components.v1 import declare_component
    component = declare_component('flipfynd_loading_status',
        path=str(Path(__file__).with_name('loading_status_component')))
    component(key='loading_status', default=None)
