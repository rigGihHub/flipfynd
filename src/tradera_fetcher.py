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


BASE_DIR = Path(__file__).resolve().parent.parent

STATE_PATH = BASE_DIR / "tradera_fetch_state.json"
DATA_PATH = BASE_DIR / "tradera_data.json"


CATEGORY_URLS = {
    "Hockey - NHL": "https://www.tradera.com/category/293316",
    "Fotboll": "https://www.tradera.com/category/293311",
}


def normalize_space(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()


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
    category_info["last_fetch_at"] = datetime.now(timezone.utc).isoformat()
    category_info["last_pages_scanned"] = int(pages_scanned)
    category_info["last_items_seen"] = int(items_seen)
    category_info["last_new_items"] = int(new_items)
    category_info["last_stop_reason"] = str(stop_reason or "")
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

    return {
        "titel": title,
        "pris": price,
        "frakt": shipping,
        "saljare": seller,
        "lank": href,
        "raw_text": raw_text,
        "sida": page_number,
        "source_category": category_name,
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
    stop_after_known_pages=3,
    safety_max_pages=250,
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
        final_page = int(start_page) + max(1, int(safety_max_pages)) - 1

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright, headless=headless)
        page = browser.new_page(viewport={"width": 1440, "height": 1800})

        for page_number in range(int(start_page), final_page + 1):
            url = build_page_url(base_url, page_number)
            message = f"Öppnar {category_name} sida {page_number}"
            logs.append(message)
            print(message, flush=True)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1800)

                anchors = page.locator('a[href*="/item/"]')
                count = anchors.count()
                page_items = []
                page_links = []

                for index in range(count):
                    item = extract_item(anchors.nth(index), category_name, page_number)
                    if not item:
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

            time.sleep(0.3)
        else:
            stop_reason = f"säkerhetsgräns {safety_max_pages} sidor" if end_page is None else f"angiven slutsida {end_page}"

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

