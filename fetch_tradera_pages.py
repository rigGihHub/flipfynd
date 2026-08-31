import argparse
from pathlib import Path

from src.tradera_fetcher import (
    CATEGORY_URLS,
    fetch_tradera_category,
    load_items,
    merge_items,
    save_items,
)


def fetch_one_category(category, mode, headed, output_path, safety_max_pages):
    old_items = load_items(output_path)
    known_links = {item.get("lank") for item in old_items if item.get("lank")}

    stop_after_known_pages = 3 if mode == "incremental" else 0
    print(
        f"Startar {'smart uppdatering' if mode == 'incremental' else 'full genomsökning'}: "
        f"{category}, sida 1 och framåt",
        flush=True,
    )

    new_items, logs = fetch_tradera_category(
        category_name=category,
        start_page=1,
        end_page=None,
        headless=not headed,
        known_links=known_links,
        stop_after_known_pages=stop_after_known_pages,
        safety_max_pages=max(10, safety_max_pages),
    )

    merged_items = merge_items(old_items, new_items)
    save_items(merged_items, output_path)
    truly_new = sum(1 for item in new_items if item.get("lank") not in known_links)

    print(f"Nya annonser ({category}): {truly_new}", flush=True)
    print(f"Annonser lästa ({category}): {len(new_items)}", flush=True)
    print(f"Totalt sparade objekt: {len(merged_items)}", flush=True)
    return truly_new, len(new_items), len(merged_items)


def main():
    parser = argparse.ArgumentParser()
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--category", choices=list(CATEGORY_URLS.keys()))
    scope.add_argument("--all-categories", action="store_true")
    parser.add_argument("--mode", choices=["incremental", "full"], default="incremental")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--output", default="tradera_data.json")
    parser.add_argument("--safety-max-pages", type=int, default=250)
    args = parser.parse_args()

    output_path = Path(args.output)
    categories = list(CATEGORY_URLS.keys()) if args.all_categories else [args.category]

    total_new = 0
    total_seen = 0
    final_total = len(load_items(output_path))

    for index, category in enumerate(categories, start=1):
        if len(categories) > 1:
            print(f"=== Kategori {index}/{len(categories)}: {category} ===", flush=True)
        new_count, seen_count, final_total = fetch_one_category(
            category=category,
            mode=args.mode,
            headed=args.headed,
            output_path=output_path,
            safety_max_pages=args.safety_max_pages,
        )
        total_new += new_count
        total_seen += seen_count

    if len(categories) > 1:
        print("=== Alla sporter klara ===", flush=True)
        print(f"Nya annonser totalt: {total_new}", flush=True)
        print(f"Annonser lästa totalt: {total_seen}", flush=True)
        print(f"Totalt sparade objekt: {final_total}", flush=True)


if __name__ == "__main__":
    main()
