"""Collect explicit sold evidence from local JSON snapshots into data/sold_comps.json."""
from __future__ import annotations

import argparse
from pathlib import Path

from src.loader import load_sold_comps
from src.sold_comp_collector import collect_sold_comps, load_rows_from_json
from src.sold_comp_import import save_sold_comps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", required=True, help="JSON file to scan; may be repeated")
    parser.add_argument("--output", default="data/sold_comps.json")
    args = parser.parse_args()

    existing = load_sold_comps(args.output)
    total_added = total_candidates = total_not_sold = total_invalid = 0
    for source in args.source:
        rows = load_rows_from_json(source)
        result = collect_sold_comps(rows, existing=existing, source_name=Path(source).name)
        existing = result["records"]
        total_added += result["added_count"]
        total_candidates += result["candidate_count"]
        total_not_sold += result["not_sold_count"]
        total_invalid += result["invalid_count"]
        print(
            f"{source}: {result['added_count']} nya, {result['duplicate_count']} dubbletter, "
            f"{result['not_sold_count']} utan explicit såld-evidens, {result['invalid_count']} ogiltiga"
        )

    save_sold_comps(existing, args.output)
    print(
        f"Klart: {total_added} nya av {total_candidates} verifierbara kandidater. "
        f"{total_not_sold} ignorerades som ej verifierat sålda; {total_invalid} ogiltiga."
    )


if __name__ == "__main__":
    main()
