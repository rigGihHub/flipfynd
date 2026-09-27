#!/usr/bin/env python3
"""Run the versioned Seller Top 5 quality contract."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.seller_quality_benchmark import evaluate_seller_quality_portfolio


def main() -> int:
    payload = json.loads((ROOT / "data" / "seller_quality_benchmark.json").read_text(encoding="utf-8"))
    result = evaluate_seller_quality_portfolio(payload.get("cases") or [])
    printable = {key: value for key, value in result.items() if key != "results"}
    print(json.dumps(printable, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["release_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
