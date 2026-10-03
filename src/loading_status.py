"""Browser-side elapsed time; never polls or reruns the Python app."""
INLINE_COMPONENT_DELIVERY = True


def render_loading_status():
    from src.inline_components import mount_inline
    mount_inline('flipfynd_loading_status', 'loading_status_component',
                 key='loading_status', reply=False)
