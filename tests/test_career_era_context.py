from src.career_era_context import build_career_era_context
from src.player_market import get_player_context

def test_verified_legend_context():
    ctx=get_player_context("Wayne Gretzky","hockey")
    out=build_career_era_context(player_name="Wayne Gretzky",context=ctx,is_rookie=True)
    assert out["verified"] is True
    assert out["career_status"]=="retired_legend"
    assert out["creates_market_value"] is False

def test_missing_metadata_stays_unknown():
    out=build_career_era_context(player_name="Some Player",context={},is_rookie=True)
    assert out["verified"] is False
    assert out["career_status"] is None
    assert out["era"] is None

def test_verified_modern_young_star():
    ctx=get_player_context("Lamine Yamal","football")
    out=build_career_era_context(player_name="Lamine Yamal",context=ctx)
    assert out["career_status"]=="active_young_star"
    assert out["era"]=="modern"
