"""Helpers ship with app data; browser state never becomes executable code."""
import pytest
from src import inline_components


@pytest.mark.parametrize('directory', [
    'loading_status_component', 'workspace_browser_storage', 'search_browser_storage'])
def test_inline_helpers_preserve_reply_without_separate_assets(monkeypatch, directory):
    import streamlit.components.v2 as components
    inline_components._register.cache_clear()
    definitions, mounts = [], []
    def register(name, **definition):
        definitions.append(definition)
        def mount(**kwargs):
            mounts.append(kwargs)
            return {'reply': {'token': 'a' * 32, 'error': 'STORAGE_UNAVAILABLE'}}
        return mount
    monkeypatch.setattr(components, 'component', register)
    data = {'blob': '<script>untrusted saved text</script>'}
    try:
        value = inline_components.mount_inline(directory, directory, key='test', data=data)
        assert value['error'] == 'STORAGE_UNAVAILABLE'
        assert definitions[0]['js'].startswith('export default function')
        assert data['blob'] not in definitions[0]['js']
        assert 'streamlit:componentReady' not in definitions[0]['js']
        assert mounts[0]['data'] == data
        assert mounts[0]['height'] == 0
        assert callable(mounts[0]['on_reply_change'])
        inline_components.mount_inline(directory, directory, key='test', data={'blob': 'updated'})
        assert len(definitions) == 1
    finally:
        inline_components._register.cache_clear()
