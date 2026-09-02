"""Små, testbara regler för FlipFynds data-onboarding."""


def build_data_readiness(total_items: int, fetch_status: str = "idle") -> dict:
    total = max(0, int(total_items or 0))
    status = str(fetch_status or "idle").lower()

    if total > 0:
        return {
            "ready": True,
            "state": "ready",
            "headline": "Annonsdata finns inläst",
            "analysis_enabled": True,
            "primary_action": "update",
        }

    if status == "running":
        return {
            "ready": False,
            "state": "fetching",
            "headline": "Hämtar annonser från Tradera",
            "analysis_enabled": False,
            "primary_action": "stop",
        }

    if status == "failed":
        return {
            "ready": False,
            "state": "failed",
            "headline": "Hämtningen misslyckades",
            "analysis_enabled": False,
            "primary_action": "retry",
        }

    return {
        "ready": False,
        "state": "empty",
        "headline": "Hämta annonser från Tradera först",
        "analysis_enabled": False,
        "primary_action": "fetch",
    }
