"""Optional Tradera API search helper.

Uses Tradera's stable v3 SearchService only when credentials are supplied through
environment variables. No credentials are stored in source code.
"""
from __future__ import annotations
import os
import requests

SEARCH_URL = "https://api.tradera.com/v3/searchservice.asmx/Search"


def api_credentials(env=None):
    env = os.environ if env is None else env
    app_id = str(env.get("TRADERA_APP_ID") or "").strip()
    app_key = str(env.get("TRADERA_APP_KEY") or "").strip()
    if not app_id or not app_key:
        return None
    return app_id, app_key


def fetch_tradera_search(query, category_id, page_number=1, order_by="Relevance", *, env=None, timeout=30):
    creds = api_credentials(env)
    if not creds:
        return {
            "ok": False,
            "status": "NOT_CONFIGURED",
            "error": "TRADERA_APP_ID och TRADERA_APP_KEY saknas.",
            "raw_response": None,
        }

    query = str(query or "").strip()
    if not query:
        return {"ok": False, "status": "INVALID_QUERY", "error": "Tom sökfråga.", "raw_response": None}

    app_id, app_key = creds
    params = {
        "appId": app_id,
        "appKey": app_key,
        "query": query,
        "categoryId": int(category_id),
        "pageNumber": max(1, int(page_number)),
        "orderBy": str(order_by or "Relevance"),
    }
    try:
        response = requests.get(SEARCH_URL, params=params, timeout=timeout)
    except requests.RequestException as exc:
        return {"ok": False, "status": "REQUEST_FAILED", "error": str(exc), "raw_response": None}

    return {
        "ok": response.status_code == 200,
        "status": "OK" if response.status_code == 200 else "HTTP_ERROR",
        "http_status": response.status_code,
        "error": None if response.status_code == 200 else "Tradera API returnerade ett fel.",
        "raw_response": response.text,
    }


if __name__ == "__main__":
    print("Denna modul kräver TRADERA_APP_ID och TRADERA_APP_KEY i miljön.")
