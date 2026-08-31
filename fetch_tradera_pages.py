import argparse
from pathlib import Path

from src.tradera_fetcher import (
    CATEGORY_URLS,
    fetch_tradera_category,
    load_items,
    merge_items,
    save_items,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, choices=list(CATEGORY_URLS.keys()))
    parser.add_argument("--mode", choices=["incremental", "full"], default="incremental")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--output", default="tradera_data.json")
    parser.add_argument("--safety-max-pages", type=int, default=250)
    args = parser.parse_args()

    output_path = Path(args.output)
    old_items = load_items(output_path)
    known_links = {item.get("lank") for item in old_items if item.get("lank")}

    # Both modes start at page 1 so newly published listings are discovered.
    # Incremental mode stops after three consecutive fully-known pages; full
    # mode keeps going until Tradera returns no more listings (or safety limit).
    stop_after_known_pages = 3 if args.mode == "incremental" else 0

    print(
        f"Startar {'smart uppdatering' if args.mode == 'incremental' else 'full genomsökning'}: "
        f"{args.category}, sida 1 och framåt",
        flush=True,
    )

    new_items, logs = fetch_tradera_category(
        category_name=args.category,
        start_page=1,
        end_page=None,
        headless=not args.headed,
        known_links=known_links,
        stop_after_known_pages=stop_after_known_pages,
        safety_max_pages=max(10, args.safety_max_pages),
    )

    merged_items = merge_items(old_items, new_items)
    save_items(merged_items, output_path)
    truly_new = sum(1 for item in new_items if item.get("lank") not in known_links)

    print(f"Nya annonser: {truly_new}", flush=True)
    print(f"Annonser lästa denna körning: {len(new_items)}", flush=True)
    print(f"Totalt sparade objekt: {len(merged_items)}", flush=True)


if __name__ == "__main__":
    main()
