from pathlib import Path


def test_streamlit_seller_toplist_shows_comparison_alternatives_with_honest_profit():
    source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert 'seller_top5_result.get("alternatives",' in source
    assert "Nettovinst: ej beräkningsbar" in source
    assert "Avstå · negativ beräknad nettovinst" in source
    assert "djupanalys återstår" in source
    assert "Topp 5 hittills" in source
