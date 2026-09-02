import argparse
from pathlib import Path

from src.tradera_fetcher import (
    CATEGORY_URLS,
    fetch_tradera_category,
    load_items,
    load_fetch_state,
    merge_items,
    save_items,
    start_fetch_run,
    start_fetch_category,
    record_fetch_progress,
    finish_fetch_category,
    finish_fetch_run,
    prune_active_items,
    SMART_MAX_PAGES,
    MARKET_BATCH_PAGES,
    get_market_sync_status,
    mark_market_batch,
    SMART_STOP_AFTER_KNOWN_PAGES,
    get_smart_refresh_plan,
)


def fetch_one_category(category, mode, headed, output_path, safety_max_pages, detail_limit=6, smart_max_pages=SMART_MAX_PAGES, market_batch_pages=MARKET_BATCH_PAGES):
    old_items = load_items(output_path)
    known_links = {item.get("lank") for item in old_items if item.get("lank")}

    stop_after_known_pages = SMART_STOP_AFTER_KNOWN_PAGES if mode == "incremental" else 0
    if mode == "scheduled_refresh":
        plan = get_smart_refresh_plan(category)
        if not plan.get("due"):
            print(f"Smart refresh: inget behöver uppdateras för {category}.", flush=True)
            return 0, 0, len(old_items)
        start_page = int(plan["start_page"])
        end_page = int(plan["end_page"])
        print(f"Smart refresh: {category}, sida {start_page}-{end_page} • {plan.get('reason', '')}", flush=True)
    elif mode == "market_batch":
        sync = get_market_sync_status(category)
        if sync["complete"]:
            print(f"Marknaden redan komplett för {category} – hoppar över.", flush=True)
            return 0, 0, len(old_items)
        start_page = sync["next_page"]
        end_page = start_page + max(1, int(market_batch_pages)) - 1
        print(
            f"Startar marknadsomgång: {category}, sida {start_page}-{end_page}",
            flush=True,
        )
    else:
        start_page = 1
        end_page = None
        print(
            f"Startar {'smart uppdatering' if mode == 'incremental' else 'full genomsökning'}: "
            f"{category}, sida 1 och framåt",
            flush=True,
        )

    start_fetch_category(category)

    def persist_page(**progress):
        current_items = load_items(output_path)
        merged_page = merge_items(current_items, progress["page_items"])
        # Keep the full archive on disk. Interactive analysis applies its own
        # bounded working set, so older market pages are not deleted.
        save_items(merged_page, output_path)
        record_fetch_progress(
            category_name=category,
            page_number=progress["page_number"],
            pages_scanned=progress["pages_scanned"],
            items_seen=progress["items_seen"],
            new_items=progress["new_items"],
        )
        print(
            f"PROGRESS|{category}|{progress['page_number']}|{progress['items_seen']}|{progress['new_items']}",
            flush=True,
        )

    new_items, logs = fetch_tradera_category(
        category_name=category,
        start_page=start_page,
        end_page=end_page,
        headless=not headed,
        known_links=known_links,
        stop_after_known_pages=stop_after_known_pages,
        safety_max_pages=max(10, safety_max_pages),
        page_callback=persist_page,
        detail_limit=(0 if mode == "scheduled_refresh" else min(detail_limit, 2) if mode == "market_batch" else detail_limit),
        smart_max_pages=(smart_max_pages if mode == "incremental" else None),
    )

    merged_items = merge_items(load_items(output_path), new_items)
    save_items(merged_items, output_path)
    truly_new = sum(1 for item in new_items if item.get("lank") not in known_links)

    if mode == "market_batch":
        info = load_fetch_state().get("categories", {}).get(category, {})
        reason = str(info.get("last_stop_reason") or "")
        scanned = int(info.get("last_pages_scanned", 0) or 0)
        actual_end = start_page + max(0, scanned - 1)
        complete = (
            reason.startswith("inga annonser")
            or reason.startswith("upprepad resultatsida")
        )
        mark_market_batch(category, start_page, actual_end, reason, complete=complete)

    print(f"Nya annonser ({category}): {truly_new}", flush=True)
    print(f"Annonser lästa ({category}): {len(new_items)}", flush=True)
    print(f"Totalt sparade objekt: {len(merged_items)}", flush=True)
    state_stop_reason = "klar"
    try:
        from src.tradera_fetcher import load_fetch_state
        state_stop_reason = (
            load_fetch_state().get("categories", {}).get(category, {}).get("last_stop_reason")
            or "klar"
        )
    except Exception:
        pass
    finish_fetch_category(
        category,
        pages_scanned=(load_fetch_state().get("categories", {}).get(category, {}).get("last_pages_scanned", 0) or 0),
        items_seen=len(new_items),
        new_items=truly_new,
        stop_reason=state_stop_reason,
    )
    return truly_new, len(new_items), len(merged_items)


def main():
    parser = argparse.ArgumentParser()
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--category", choices=list(CATEGORY_URLS.keys()))
    scope.add_argument("--all-categories", action="store_true")
    parser.add_argument("--mode", choices=["incremental", "scheduled_refresh", "market_batch", "full"], default="incremental")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--output", default="tradera_data.json")
    parser.add_argument("--safety-max-pages", type=int, default=250)
    parser.add_argument(
        "--detail-limit",
        type=int,
        default=6,
        help="Max antal prioriterade annonser per kategori som öppnas för detaljberikning.",
    )
    parser.add_argument(
        "--market-batch-pages",
        type=int,
        default=MARKET_BATCH_PAGES,
        help="Antal Tradera-sidor per steg i Läs in hela marknaden.",
    )
    parser.add_argument(
        "--smart-max-pages",
        type=int,
        default=SMART_MAX_PAGES,
        help="Max antal sidor per sport i Smart uppdatering. Full genomsökning påverkas inte.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    categories = list(CATEGORY_URLS.keys()) if args.all_categories else [args.category]

    total_new = 0
    total_seen = 0
    final_total = len(load_items(output_path))
    start_fetch_run("all" if args.all_categories else categories[0])

    try:
        for index, category in enumerate(categories, start=1):
            if len(categories) > 1:
                print(f"=== Kategori {index}/{len(categories)}: {category} ===", flush=True)
            new_count, seen_count, final_total = fetch_one_category(
                category=category,
                mode=args.mode,
                headed=args.headed,
                output_path=output_path,
                safety_max_pages=args.safety_max_pages,
                detail_limit=max(0, args.detail_limit),
                smart_max_pages=max(1, args.smart_max_pages),
                market_batch_pages=max(1, args.market_batch_pages),
            )
            total_new += new_count
            total_seen += seen_count

        if len(categories) > 1:
            print("=== Alla sporter klara ===", flush=True)
            print(f"Nya annonser totalt: {total_new}", flush=True)
            print(f"Annonser lästa totalt: {total_seen}", flush=True)
            print(f"Totalt sparade objekt: {final_total}", flush=True)

        finish_fetch_run(
            "finished",
            f"Klar: {total_new} nya annonser, {final_total} totalt sparade.",
        )
    except Exception as exc:
        finish_fetch_run("failed", str(exc))
        raise


if __name__ == "__main__":
    main()
