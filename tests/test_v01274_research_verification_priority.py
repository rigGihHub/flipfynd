from src.research_verification_priority import prioritize_verification_candidates


def row(label="STRONG_CANDIDATE", confidence=90, source="eBay", sold=False, conflicts=None, title="x"):
    return {"label": label, "candidate_confidence": confidence, "source": source, "sold_claim": sold, "conflicts": conflicts or [], "title": title}


def test_sold_strong_candidate_prioritized():
    out = prioritize_verification_candidates([row(confidence=92, sold=False, title="a"), row(confidence=88, sold=True, title="b")])
    assert out[0]["title"] == "b"
    assert out[0]["creates_sold_evidence"] is False


def test_rejects_conflicted_candidate_from_priority_queue():
    out = prioritize_verification_candidates([row(conflicts=["extra parallel"]), row(label="REVIEW", confidence=75, source="Tradera", title="ok")])
    assert [x["title"] for x in out] == ["ok"]


def test_diversifies_sources_before_duplicates():
    out = prioritize_verification_candidates([
        row(confidence=95, source="eBay", title="e1"),
        row(confidence=94, source="eBay", title="e2"),
        row(confidence=80, source="Tradera", title="t1"),
    ], limit=2)
    assert {x["title"] for x in out} == {"e1", "t1"}


def test_does_not_create_exact_identity_or_buy():
    out = prioritize_verification_candidates([row()])[0]
    assert out["creates_exact_identity"] is False
    assert out["creates_buy_decision"] is False
