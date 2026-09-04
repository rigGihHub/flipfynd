from pathlib import Path


def test_app_has_sold_collector_import_guard():
    text = Path('app.py').read_text(encoding='utf-8')
    assert 'except ImportError:' in text
    assert 'smart_collect_local_sold_comps = None' in text
    assert 'Resten av FlipFynd kan användas' in text


def test_current_collector_exports_smart_collector():
    from src import sold_comp_collector
    assert callable(sold_comp_collector.collect_sold_comps)
    assert callable(sold_comp_collector.smart_collect_local_sold_comps)


def test_decision_first_result_uses_qualitative_liquidity():
    text = Path('app.py').read_text(encoding='utf-8')
    assert '<div class="ff-quick-label">SÄLJBARHET</div>' in text
    assert '🔥 **Informationsövertag**' in text
    assert '**Fyndsäkerhet:**' in text
    assert 'Visa hela analysen och underlaget' in text
