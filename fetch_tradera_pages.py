import argparse
from pathlib import Path

from src.tradera_fetcher import (
    CATEGORY_URLS,
    fetch_tradera_category,
    load_fetch_state,
    load_items,
    merge_items,
    save_items,
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--category",
        required=True,
        choices=list(CATEGORY_URLS.keys()),
    )

    parser.add_argument(
        "--pages",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--mode",
        choices=["incremental", "full"],
        default="incremental",
    )

    parser.add_argument(
        "--headed",
        action="store_true",
    )

    parser.add_argument(
        "--output",
        default="tradera_data.json",
    )

    args = parser.parse_args()

    state = load_fetch_state()

    category_info = state.get(
        "categories",
        {},
    ).get(
        args.category,
        {},
    )

    max_loaded = int(
        category_info.get(
            "max_page_loaded",
            0,
        )
        or 0
    )

    if args.mode == "incremental":
        start_page = max_loaded + 1 if max_loaded > 0 else 1
    else:
        start_page = 1

    end_page = args.pages

    if start_page > end_page:
        print(
            f"Inget att hämta. "
            f"{args.category} är redan hämtad till sida {max_loaded}.",
            flush=True,
        )
        return

    print(
        f"Startar hämtning: "
        f"{args.category}, "
        f"sida {start_page}-{end_page}",
        flush=True,
    )

    new_items, logs = fetch_tradera_category(
        category_name=args.category,
        start_page=start_page,
        end_page=end_page,
        headless=not args.headed,
    )

    output_path = Path(args.output)

    old_items = load_items(output_path)

    merged_items = merge_items(
        old_items,
        new_items,
    )

    save_items(
        merged_items,
        output_path,
    )

    print(
        f"Nya träffar: {len(new_items)}",
        flush=True,
    )

    print(
        f"Totalt sparade objekt: {len(merged_items)}",
        flush=True,
    )


if __name__ == "__main__":
    main()