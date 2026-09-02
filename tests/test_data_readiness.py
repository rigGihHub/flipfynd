from src.data_readiness import build_data_readiness


def test_empty_dataset_requests_fetch():
    state = build_data_readiness(0, "idle")
    assert state["state"] == "empty"
    assert state["primary_action"] == "fetch"
    assert state["analysis_enabled"] is False


def test_failed_fetch_requests_retry():
    state = build_data_readiness(0, "failed")
    assert state["state"] == "failed"
    assert state["primary_action"] == "retry"


def test_running_fetch_disables_analysis():
    state = build_data_readiness(0, "running")
    assert state["state"] == "fetching"
    assert state["analysis_enabled"] is False


def test_existing_data_is_ready_even_after_previous_failure():
    state = build_data_readiness(12, "failed")
    assert state["ready"] is True
    assert state["analysis_enabled"] is True
    assert state["primary_action"] == "update"
