from pathlib import Path
from src.flip_journal import build_entry_from_listing, journal_metrics, load_journal, save_journal, update_entry

def test_journal_records_actual_flip_and_profit(tmp_path: Path):
    path = tmp_path / "journal.json"
    entry = build_entry_from_listing({"titel":"Testkort","lank":"https://example.test/1","deal_score":80,"net_profit":120}, purchase_price=100, purchase_date="2026-08-01")
    save_journal([entry], path)
    rows = update_entry(load_journal(path), entry["id"], sale_date="2026-08-11", sale_price=250, selling_fee=25, packaging_cost=5)
    assert rows[0]["actual_net_profit"] == 120
    assert rows[0]["days_to_sell"] == 10
    assert rows[0]["status"] == "sålt"

def test_journal_metrics_do_not_invent_results():
    rows = [build_entry_from_listing({"titel":"A"}, purchase_price=50, purchase_date="2026-08-01")]
    metrics = journal_metrics(rows)
    assert metrics["sold_count"] == 0
    assert metrics["win_rate"] is None
    assert metrics["median_days_to_sell"] is None

def test_journal_compares_predicted_and_actual_profit():
    row = build_entry_from_listing({"titel":"A","net_profit":100}, purchase_price=100, purchase_date="2026-08-01")
    rows = update_entry([row], row["id"], sale_date="2026-08-06", sale_price=240, selling_fee=20, packaging_cost=5)
    assert journal_metrics(rows)["mean_profit_error"] == 15


def test_new_journal_entry_has_empty_outcome_review():
    row = build_entry_from_listing({"titel":"A"}, purchase_price=50)
    assert row["outcome_review_reasons"] == []
    assert row["outcome_review_note"] == ""
    assert row["outcome_reviewed_at"] is None
