from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from src import tradera_fetcher as fetcher


def browser(tmp_path, *, installed=True, side_effect=None):
    binary = tmp_path / 'chrome'
    if installed:
        binary.touch()
    chromium = SimpleNamespace(executable_path=str(binary), launch=Mock(side_effect=side_effect))
    return SimpleNamespace(chromium=chromium), binary


def test_system_browser_failure_falls_back_to_existing_bundle(monkeypatch, tmp_path):
    runtime, binary = browser(tmp_path, side_effect=[RuntimeError('system launch failed'), 'browser'])
    monkeypatch.setattr(fetcher, '_find_system_chromium', lambda: '/usr/bin/chromium')
    monkeypatch.setattr(fetcher, '_install_playwright_chromium', lambda: pytest.fail('Bundle already exists'))
    assert fetcher._launch_chromium(runtime) == 'browser'
    assert runtime.chromium.launch.call_args_list[0].kwargs['executable_path'] == '/usr/bin/chromium'
    assert runtime.chromium.launch.call_args_list[1].kwargs['executable_path'] == str(binary)


def test_missing_bundle_installs_and_launches_exact_binary(monkeypatch, tmp_path):
    runtime, binary = browser(tmp_path, installed=False)
    monkeypatch.setattr(fetcher, '_find_system_chromium', lambda: None)
    install = Mock(side_effect=lambda: binary.touch())
    monkeypatch.setattr(fetcher, '_install_playwright_chromium', install)
    fetcher._launch_chromium(runtime, headless=False)
    install.assert_called_once()
    assert runtime.chromium.launch.call_args.kwargs['executable_path'] == str(binary)
    assert runtime.chromium.launch.call_args.kwargs['headless'] is False


def test_installer_preserves_driver_cache_environment(monkeypatch):
    monkeypatch.delenv('PLAYWRIGHT_BROWSERS_PATH', raising=False)
    monkeypatch.setenv('XDG_CACHE_HOME', '/tmp/custom-cache')
    run = Mock(return_value=SimpleNamespace(returncode=0, stdout=''))
    monkeypatch.setattr(fetcher.subprocess, 'run', run)
    fetcher._install_playwright_chromium()
    assert 'PLAYWRIGHT_BROWSERS_PATH' not in run.call_args.kwargs['env']
    assert run.call_args.kwargs['env']['XDG_CACHE_HOME'] == '/tmp/custom-cache'
    monkeypatch.setenv('PLAYWRIGHT_BROWSERS_PATH', '/tmp/explicit-browser-cache')
    fetcher._install_playwright_chromium()
    assert run.call_args.kwargs['env']['PLAYWRIGHT_BROWSERS_PATH'] == '/tmp/explicit-browser-cache'


def test_final_error_includes_actual_launch_failure(monkeypatch, tmp_path):
    runtime, _ = browser(tmp_path, side_effect=RuntimeError('libExample.so: cannot open shared object file'))
    monkeypatch.setattr(fetcher, '_find_system_chromium', lambda: None)
    with pytest.raises(RuntimeError, match='libExample.so'):
        fetcher._launch_chromium(runtime)
