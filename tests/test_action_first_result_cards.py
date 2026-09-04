from pathlib import Path


def test_primary_card_keeps_core_decision_fields():
    text = Path('app.py').read_text(encoding='utf-8')
    assert 'REALISTISKT VÄRDE' in text
    assert 'MÖJLIG NETTOVINST' in text
    assert 'SÄLJBARHET' in text
    assert '**Varför?**' in text
    assert 'Max köppris inkl. frakt' in text


def test_primary_card_keeps_material_assumption_warnings():
    text = Path('app.py').read_text(encoding='utf-8')
    assert 'Frakten kunde inte läsas säkert' in text
    assert 'Auktionskalkylen använder' in text


def test_detailed_scoring_remains_available_in_full_analysis():
    text = Path('app.py').read_text(encoding='utf-8')
    assert 'Visa hela analysen och underlaget' in text
    assert '**Värderingssäkerhet:**' in text
    assert '**Risk:**' in text
    assert 'Exact Identity Gate' in text
