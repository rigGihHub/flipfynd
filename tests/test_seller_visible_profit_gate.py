from pathlib import Path


def test_streamlit_seller_toplist_requires_positive_known_net_profit():
    source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert "and known_positive_net_profit(row)" in source
    assert "Nettovinst: ej beräkningsbar" in source
    assert "_seller_display_rows = (_find_rows + _research_rows)[:5]" in source
