"""Import verified sold comps from CSV/JSON into FlipFynd's separate evidence file."""

import argparse
from pathlib import Path

from src.loader import load_sold_comps
from src.sold_comp_import import import_sold_comp_rows, parse_import_bytes, save_sold_comps


def main():
    parser = argparse.ArgumentParser(description="Importera verifierade sålda comps till FlipFynd")
    parser.add_argument("input", help="CSV- eller JSON-fil")
    parser.add_argument("--output", default="data/sold_comps.json", help="Målfil")
    parser.add_argument("--source", default=None, help="Provenance, t.ex. ebay_sold_export")
    args = parser.parse_args()

    source = Path(args.input)
    rows = parse_import_bytes(source.read_bytes(), source.name)
    existing = load_sold_comps(args.output)
    provenance = args.source or f"manual_import:{source.name}"
    result = import_sold_comp_rows(rows, existing=existing, provenance=provenance)
    save_sold_comps(result["records"], args.output)

    print(
        f"Godkända: {result['valid_count']} | Nya: {result['added_count']} | "
        f"Dubbletter: {result['duplicate_count']} | Fel: {result['error_count']}"
    )
    for error in result["errors"][:20]:
        print(f"Rad {error['row']}: {error['error']}")


if __name__ == "__main__":
    main()
