import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from src.listing_detail_enrichment import enrich_selected_listings


BASE_DIR = Path(__file__).resolve().parent.parent

STATE_PATH = BASE_DIR / "tradera_fetch_state.json"
DATA_PATH = BASE_DIR / "tradera_data.json"


CATEGORY_URLS = {
    "Hockey - NHL": "https://www.tradera.com/category/293316",
    "Fotboll": "https://www.tradera.com/category/293311",
}

CATEGORY_IDS = {
    "293316": "Hockey - NHL",
    "293311": "Fotboll",
}

SMART_MAX_PAGES = 12
SMART_STOP_AFTER_KNOWN_PAGES = 2
MAX_ACTIVE_ITEMS_PER_CATEGORY = 1500
MARKET_BATCH_PAGES = 12


def normalize_space(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()




def infer_category_from_item_url(url, fallback=None):
    """Infer sport category from Tradera's item URL when possible.

    Item URLs include the category id, e.g. /item/293316/... for hockey.
    This gives us a second guard against a redirect or caller/category mismatch.
    """
    match = re.search(r"/item/(\d+)/", str(url or ""))
    if match:
        return CATEGORY_IDS.get(match.group(1), fallback)
    return fallback


def prune_active_items(items, max_per_category=MAX_ACTIVE_ITEMS_PER_CATEGORY):
    """Bound the active-listing dataset so cloud analysis stays lightweight.

    Lower Tradera page numbers are newer because the category scan starts from
    the newest listings. We keep the newest bounded slice independently per
    sport and preserve unknown categories in a small fallback bucket.
    """
    limit = max(1, int(max_per_category or MAX_ACTIVE_ITEMS_PER_CATEGORY))
    buckets = {}
    for pos, item in enumerate(items or []):
        clone = dict(item)
        category = infer_category_from_item_url(
            clone.get("lank"),
            clone.get("source_category") or "Okänd",
        )
        clone["source_category"] = category
        page = clone.get("sida")
        try:
            page_num = int(page)
        except (TypeError, ValueError):
            page_num = 999999
        enriched = 0 if clone.get("detail_enrichment_status") == "ok" else 1
        buckets.setdefault(category, []).append((page_num, enriched, pos, clone))

    kept = []
    for category, rows in buckets.items():
        category_limit = limit if category in CATEGORY_URLS else min(limit, 300)
        rows.sort(key=lambda row: (row[0], row[1], row[2]))
        kept.extend(row[3] for row in rows[:category_limit])
    return kept


def parse_price(text):
    if not text:
        return None

    values = re.findall(
        r"(\d[\d\s.]*)\s*kr",
        str(text),
        flags=re.IGNORECASE,
    )

    for value in values:
        cleaned = (
            value
            .replace(" ", "")
            .replace(".", "")
        )

        try:
            price = int(cleaned)

            if price > 0:
                return price

        except ValueError:
            continue

    return None


def parse_shipping(text):
    if not text:
        return None

    text = str(text).lower()

    if "fri frakt" in text:
        return 0

    patterns = [
        r"frakt(?:\s+från)?\s*(\d[\d\s.]*)\s*kr",
        r"från\s*(\d[\d\s.]*)\s*kr",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            try:
                return int(
                    match.group(1)
                    .replace(" ", "")
                    .replace(".", "")
                )

            except ValueError:
                pass

    return None


def choose_seller(text):
    if not text:
        return None

    patterns = [
        r"säljare\s*:?\s*([^\n|]+)",
        r"seller\s*:?\s*([^\n|]+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            str(text),
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        seller = normalize_space(
            match.group(1)
        )

        if 2 <= len(seller) <= 60:
            return seller

    return None


def build_page_url(
    base_url,
    page_number,
):
    if page_number <= 1:
        return base_url

    separator = (
        "&"
        if "?" in base_url
        else "?"
    )

    return (
        f"{base_url}"
        f"{separator}"
        f"paging={page_number}"
    )


def load_fetch_state():
    if not STATE_PATH.exists():
        return {
            "categories": {}
        }

    try:
        with open(
            STATE_PATH,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(
            data,
            dict,
        ):
            return {
                "categories": {}
            }

        data.setdefault(
            "categories",
            {},
        )

        return data

    except Exception:
        return {
            "categories": {}
        }


def save_fetch_state(state):
    state.setdefault(
        "categories",
        {},
    )

    with open(
        STATE_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2,
        )


def mark_page_loaded(
    category_name,
    page_number,
):
    state = load_fetch_state()

    category_info = (
        state["categories"]
        .setdefault(
            category_name,
            {
                "loaded_pages": [],
                "max_page_loaded": 0,
            },
        )
    )

    pages = set(
        category_info.get(
            "loaded_pages",
            [],
        )
    )

    pages.add(int(page_number))
    category_info["loaded_pages"] = sorted(pages)
    category_info["max_page_loaded"] = max(category_info["loaded_pages"]) if category_info["loaded_pages"] else 0
    save_fetch_state(state)


def record_fetch_summary(
    category_name,
    pages_scanned,
    items_seen,
    new_items,
    stop_reason,
):
    state = load_fetch_state()
    category_info = state["categories"].setdefault(category_name, {})
    category_info["last_fetch_at"] = _utc_now_iso()
    category_info["last_pages_scanned"] = int(pages_scanned)
    category_info["last_items_seen"] = int(items_seen)
    category_info["last_new_items"] = int(new_items)
    category_info["last_stop_reason"] = str(stop_reason or "")
    save_fetch_state(state)




def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def start_fetch_run(scope):
    state = load_fetch_state()
    state["active_run"] = {
        "status": "running",
        "scope": str(scope or ""),
        "started_at": _utc_now_iso(),
        "heartbeat_at": _utc_now_iso(),
        "current_category": "",
        "current_page": 0,
        "total_items_seen": 0,
        "total_new_items": 0,
        "completed_categories": [],
    }
    save_fetch_state(state)


def start_fetch_category(category_name):
    state = load_fetch_state()
    run = state.setdefault("active_run", {})
    run.update({
        "status": "running",
        "current_category": category_name,
        "current_page": 0,
        "category_items_seen": 0,
        "category_new_items": 0,
        "heartbeat_at": _utc_now_iso(),
    })
    save_fetch_state(state)


def record_fetch_progress(category_name, page_number, pages_scanned, items_seen, new_items):
    state = load_fetch_state()
    run = state.setdefault("active_run", {})
    run.update({
        "status": "running",
        "current_category": category_name,
        "current_page": int(page_number),
        "category_pages_scanned": int(pages_scanned),
        "category_items_seen": int(items_seen),
        "category_new_items": int(new_items),
        "heartbeat_at": _utc_now_iso(),
    })
    category_info = state.setdefault("categories", {}).setdefault(category_name, {})
    category_info.update({
        "running": True,
        "current_page": int(page_number),
        "current_items_seen": int(items_seen),
        "current_new_items": int(new_items),
        "heartbeat_at": _utc_now_iso(),
    })
    save_fetch_state(state)


def finish_fetch_category(category_name, pages_scanned, items_seen, new_items, stop_reason):
    state = load_fetch_state()
    run = state.setdefault("active_run", {})
    completed = list(run.get("completed_categories", []) or [])
    if category_name not in completed:
        completed.append(category_name)
    run.update({
        "completed_categories": completed,
        "total_items_seen": int(run.get("total_items_seen", 0) or 0) + int(items_seen),
        "total_new_items": int(run.get("total_new_items", 0) or 0) + int(new_items),
        "heartbeat_at": _utc_now_iso(),
    })
    category_info = state.setdefault("categories", {}).setdefault(category_name, {})
    category_info["running"] = False
    category_info["current_page"] = int(pages_scanned)
    category_info["current_items_seen"] = int(items_seen)
    category_info["current_new_items"] = int(new_items)
    save_fetch_state(state)
    record_fetch_summary(category_name, pages_scanned, items_seen, new_items, stop_reason)


def finish_fetch_run(status="finished", message=""):
    state = load_fetch_state()
    run = state.setdefault("active_run", {})
    run.update({
        "status": str(status),
        "finished_at": _utc_now_iso(),
        "heartbeat_at": _utc_now_iso(),
        "message": str(message or ""),
    })
    for info in state.setdefault("categories", {}).values():
        if isinstance(info, dict):
            info["running"] = False
    save_fetch_state(state)

def format_loaded_pages(pages):
    if not pages:
        return "Inga"

    pages = sorted(
        {
            int(page)
            for page in pages
        }
    )

    ranges = []

    start = pages[0]
    previous = pages[0]

    for page in pages[1:]:
        if page == previous + 1:
            previous = page
            continue

        if start == previous:
            ranges.append(
                str(start)
            )
        else:
            ranges.append(
                f"{start}-{previous}"
            )

        start = page
        previous = page

    if start == previous:
        ranges.append(
            str(start)
        )
    else:
        ranges.append(
            f"{start}-{previous}"
        )

    return ", ".join(
        ranges
    )


def get_market_sync_status(category_name):
    """Return resumable full-market crawl status for one sport."""
    state = load_fetch_state()
    info = state.setdefault("categories", {}).setdefault(category_name, {})
    loaded_pages = sorted({int(p) for p in info.get("loaded_pages", []) if str(p).isdigit()})
    max_loaded = max(loaded_pages) if loaded_pages else 0
    next_page = int(info.get("market_next_page", max_loaded + 1) or (max_loaded + 1))
    return {
        "loaded_pages": loaded_pages,
        "max_page_loaded": max_loaded,
        "next_page": max(1, next_page),
        "complete": bool(info.get("market_complete", False)),
        "completed_at": info.get("market_completed_at"),
        "last_batch_start": info.get("market_last_batch_start"),
        "last_batch_end": info.get("market_last_batch_end"),
    }


def mark_market_batch(category_name, start_page, end_page, stop_reason="", complete=False):
    state = load_fetch_state()
    info = state.setdefault("categories", {}).setdefault(category_name, {})
    info["market_last_batch_start"] = int(start_page)
    info["market_last_batch_end"] = int(end_page)
    info["market_next_page"] = int(end_page) + 1
    if complete:
        info["market_complete"] = True
        info["market_completed_at"] = _utc_now_iso()
    elif str(stop_reason or "").startswith("inga annonser"):
        info["market_complete"] = True
        info["market_completed_at"] = _utc_now_iso()
    save_fetch_state(state)


def reset_market_sync(category_name=None):
    """Restart the resumable market scan without deleting already saved ads."""
    state = load_fetch_state()
    names = [category_name] if category_name else list(CATEGORY_URLS.keys())
    for name in names:
        info = state.setdefault("categories", {}).setdefault(name, {})
        info["market_next_page"] = 1
        info["market_complete"] = False
        info.pop("market_completed_at", None)
        info.pop("market_last_batch_start", None)
        info.pop("market_last_batch_end", None)
    save_fetch_state(state)


def load_items(
    path=DATA_PATH,
):
    path = Path(path)

    if not path.exists():
        return []

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if isinstance(
            data,
            list,
        ):
            return data

    except Exception:
        pass

    return []


def save_items(
    items,
    path=DATA_PATH,
):
    path = Path(path)

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            items,
            file,
            ensure_ascii=False,
            indent=2,
        )


def merge_items(
    old_items,
    new_items,
):
    merged = {}

    for item in (
        old_items
        + new_items
    ):
        link = item.get(
            "lank"
        )

        if link:
            key = link

        else:
            key = (
                f"{item.get('titel', '')}|"
                f"{item.get('pris')}|"
                f"{item.get('source_category', '')}"
            )

        if key in merged:
            old_item = merged[key]

            if (
                item.get("frakt")
                is None
                and old_item.get("frakt")
                is not None
            ):
                item["frakt"] = (
                    old_item["frakt"]
                )

            if (
                not item.get("saljare")
                and old_item.get("saljare")
            ):
                item["saljare"] = (
                    old_item["saljare"]
                )

            if not item.get("image_urls") and old_item.get("image_urls"):
                item["image_urls"] = old_item.get("image_urls", [])
            if not item.get("image_alts") and old_item.get("image_alts"):
                item["image_alts"] = old_item.get("image_alts", [])

            # Detail-page enrichment is deliberately selective. Preserve a prior
            # successful snapshot when a later category crawl only sees the
            # compact listing card again.
            detail_keys = [
                "detail_priority_score", "detail_priority_reasons",
                "detail_enrichment_status", "detail_source", "detail_enriched_at",
                "detail_title", "full_description", "detail_image_urls",
                "exact_end_text", "bid_count", "seller_detail",
            ]
            for detail_key in detail_keys:
                if item.get(detail_key) in (None, "", []) and old_item.get(detail_key) not in (None, "", []):
                    item[detail_key] = old_item.get(detail_key)

        merged[key] = item

    return list(
        merged.values()
    )


def clear_all_loaded_data():
    if DATA_PATH.exists():
        DATA_PATH.unlink()

    if STATE_PATH.exists():
        STATE_PATH.unlink()


def find_listing_container(anchor):
    current = anchor

    for _ in range(7):
        try:
            text = normalize_space(
                current.inner_text(
                    timeout=1500
                )
            )

        except Exception:
            text = ""

        if len(text) >= 25:
            return current

        try:
            current = (
                current.locator(
                    ".."
                )
            )

        except Exception:
            break

    return anchor


def extract_item(
    anchor,
    category_name,
    page_number,
):
    try:
        href = anchor.get_attribute(
            "href"
        )

    except Exception:
        return None

    if (
        not href
        or "/item/" not in href
    ):
        return None

    href = urljoin(
        "https://www.tradera.com",
        href,
    )

    container = find_listing_container(
        anchor
    )

    try:
        raw_text = normalize_space(
            container.inner_text(
                timeout=1800
            )
        )

    except Exception:
        raw_text = ""

    try:
        title = normalize_space(
            anchor.inner_text(
                timeout=1500
            )
        )

    except Exception:
        title = ""

    if (
        not title
        or len(title) < 3
    ):
        title = raw_text[:180]

    if not title:
        return None

    price = parse_price(
        raw_text
    )

    if price is None:
        return None

    shipping = parse_shipping(
        raw_text
    )

    seller = choose_seller(
        raw_text
    )

    # Capture listing image references for Visual Edge. We only store URLs and
    # alt text here; no visual claim is inferred from the pixels.
    image_urls = []
    image_alts = []
    try:
        images = container.locator("img")
        for idx in range(min(images.count(), 8)):
            img = images.nth(idx)
            src = img.get_attribute("src") or img.get_attribute("data-src")
            if src:
                src = urljoin("https://www.tradera.com", src)
                if src not in image_urls:
                    image_urls.append(src)
            alt = normalize_space(img.get_attribute("alt"))
            if alt and alt not in image_alts:
                image_alts.append(alt)
    except Exception:
        pass

    return {
        "titel": title,
        "pris": price,
        "frakt": shipping,
        "saljare": seller,
        "lank": href,
        "raw_text": raw_text,
        "image_urls": image_urls,
        "image_alts": image_alts,
        "sida": page_number,
        "source_category": infer_category_from_item_url(href, category_name),
    }


def _find_system_chromium():
    """Returnera sökväg till system-Chromium om en sådan finns.

    Streamlit Community Cloud kan installera Chromium via packages.txt.
    Lokalt lämnas detta normalt till Playwrights egen browser-bundle.
    """
    candidates = [
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
    ]

    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path

    return None


def _install_playwright_chromium():
    """Installera Playwrights Chromium-bundle om den saknas.

    Streamlit Community Cloud kan ibland bygga om Python-miljön utan att
    systempaketet chromium blir tillgängligt. Då installerar vi Playwrights
    egen browser-bundle i den skrivbara användarcachen och försöker igen.
    """
    env = os.environ.copy()
    env.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path.home() / ".cache" / "ms-playwright"))

    completed = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180,
        check=False,
    )

    if completed.returncode != 0:
        tail = "\n".join((completed.stdout or "").splitlines()[-20:])
        raise RuntimeError(
            "Chromium kunde inte installeras automatiskt i körmiljön. "
            "Installationslogg:\n" + tail
        )


def _launch_chromium(playwright, headless=True):
    """Starta Chromium robust både lokalt och på Streamlit Cloud."""
    system_chromium = _find_system_chromium()

    launch_kwargs = {
        "headless": headless,
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    }

    if system_chromium:
        launch_kwargs["executable_path"] = system_chromium

    try:
        return playwright.chromium.launch(**launch_kwargs)
    except Exception as exc:
        message = str(exc)

        if "Executable doesn't exist" in message or "playwright install" in message:
            _install_playwright_chromium()
            try:
                return playwright.chromium.launch(
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
            except Exception as retry_exc:
                raise RuntimeError(
                    "Chromium saknas eller kunde inte startas efter automatisk installation. "
                    "Se hämtloggen för detaljer."
                ) from retry_exc

        raise


def fetch_tradera_category(
    category_name,
    start_page=1,
    end_page=None,
    headless=True,
    known_links=None,
    stop_after_known_pages=SMART_STOP_AFTER_KNOWN_PAGES,
    safety_max_pages=250,
    page_callback=None,
    detail_limit=6,
    smart_max_pages=SMART_MAX_PAGES,
):
    """Fetch a Tradera category page-by-page.

    When end_page is None the crawler continues automatically until Tradera
    returns no listings, a page repeats, several consecutive pages contain no
    previously unseen listings, or the safety limit is reached.
    """
    if category_name not in CATEGORY_URLS:
        raise ValueError(f"Okänd kategori: {category_name}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright saknas.") from exc

    base_url = CATEGORY_URLS[category_name]
    all_items = []
    logs = []
    known_links = {str(link) for link in (known_links or set()) if link}
    seen_this_run = set()
    page_signatures = set()
    consecutive_known_pages = 0
    pages_scanned = 0
    stop_reason = ""

    if end_page is not None:
        final_page = max(int(start_page), int(end_page))
    else:
        effective_pages = max(1, int(safety_max_pages))
        if stop_after_known_pages and smart_max_pages:
            effective_pages = min(effective_pages, max(1, int(smart_max_pages)))
        final_page = int(start_page) + effective_pages - 1

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright, headless=headless)
        page = browser.new_page(viewport={"width": 1440, "height": 1800})

        for page_number in range(int(start_page), final_page + 1):
            url = build_page_url(base_url, page_number)
            message = f"Öppnar {category_name} sida {page_number}"
            logs.append(message)
            print(message, flush=True)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(1200)

                anchors = page.locator('a[href*="/item/"]')
                count = anchors.count()
                page_items = []
                page_links = []

                for index in range(count):
                    item = extract_item(anchors.nth(index), category_name, page_number)
                    if not item:
                        continue
                    if item.get("source_category") != category_name:
                        # Never silently ingest another sport through a redirect
                        # or malformed category page. This also makes sport counts
                        # trustworthy in the UI.
                        continue
                    link = item.get("lank")
                    if not link or link in page_links:
                        continue
                    page_links.append(link)
                    if link in seen_this_run:
                        continue
                    seen_this_run.add(link)
                    page_items.append(item)

                pages_scanned += 1

                # An empty result page is Tradera's natural end marker.
                if not page_links:
                    stop_reason = f"inga annonser på sida {page_number}"
                    message = f"Sida {page_number}: inga annonser – slut på resultat"
                    logs.append(message)
                    print(message, flush=True)
                    break

                signature = tuple(page_links)
                if signature in page_signatures:
                    stop_reason = f"upprepad resultatsida vid sida {page_number}"
                    message = f"Sida {page_number}: samma annonser som tidigare sida – stoppar"
                    logs.append(message)
                    print(message, flush=True)
                    break
                page_signatures.add(signature)

                all_items.extend(page_items)
                mark_page_loaded(category_name, page_number)

                unseen_on_page = sum(1 for link in page_links if link not in known_links)
                if known_links and unseen_on_page == 0:
                    consecutive_known_pages += 1
                else:
                    consecutive_known_pages = 0

                message = (
                    f"Sida {page_number}: {len(page_items)} annonser, "
                    f"{unseen_on_page} nya jämfört med sparad data"
                )
                logs.append(message)
                print(message, flush=True)

                if page_callback is not None:
                    page_callback(
                        category_name=category_name,
                        page_number=page_number,
                        page_items=list(page_items),
                        pages_scanned=pages_scanned,
                        items_seen=len(all_items),
                        new_items=sum(1 for item in all_items if item.get("lank") not in known_links),
                    )

                # Smart incremental stop: once several whole pages only contain
                # listings already present locally, deeper pages are unlikely to
                # add fresh listings. Full scans pass stop_after_known_pages=0.
                if (
                    end_page is None
                    and stop_after_known_pages
                    and known_links
                    and consecutive_known_pages >= int(stop_after_known_pages)
                ):
                    stop_reason = f"{consecutive_known_pages} sidor i rad utan nya annonser"
                    message = f"Stoppar smart uppdatering: {stop_reason}."
                    logs.append(message)
                    print(message, flush=True)
                    break

            except Exception as exc:
                message = f"Fel på sida {page_number}: {exc}"
                logs.append(message)
                print(message, flush=True)
                # Do not silently skip through many pages after a navigation error.
                stop_reason = f"fel på sida {page_number}"
                break

            time.sleep(0.08)
        else:
            if end_page is None and stop_after_known_pages and smart_max_pages:
                stop_reason = f"smart sidgräns {min(int(safety_max_pages), int(smart_max_pages))} sidor"
            else:
                stop_reason = f"säkerhetsgräns {safety_max_pages} sidor" if end_page is None else f"angiven slutsida {end_page}"

        detail_summary = {"attempted": 0, "enriched": 0, "failed": 0}
        if int(detail_limit or 0) > 0 and all_items:
            try:
                all_items, detail_summary = enrich_selected_listings(
                    browser,
                    all_items,
                    known_links=known_links,
                    limit=int(detail_limit),
                    timeout_ms=30000,
                    log=lambda msg: print(msg, flush=True),
                )
                message = (
                    f"Detaljberikning: {detail_summary['enriched']}/{detail_summary['attempted']} lyckades"
                )
                logs.append(message)
                print(message, flush=True)
            except Exception as exc:
                message = f"Detaljberikning kunde inte slutföras: {exc}"
                logs.append(message)
                print(message, flush=True)

        browser.close()

    new_count = sum(1 for item in all_items if item.get("lank") not in known_links)
    record_fetch_summary(
        category_name,
        pages_scanned=pages_scanned,
        items_seen=len(all_items),
        new_items=new_count,
        stop_reason=stop_reason,
    )
    return all_items, logs

