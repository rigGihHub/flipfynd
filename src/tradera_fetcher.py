import json
import re
import time
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

    pages.add(
        int(page_number)
    )

    category_info["loaded_pages"] = sorted(
        pages
    )

    category_info["max_page_loaded"] = (
        max(
            category_info["loaded_pages"]
        )
        if category_info["loaded_pages"]
        else 0
    )

    save_fetch_state(
        state
    )


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


def fetch_tradera_category(
    category_name,
    start_page=1,
    end_page=10,
    headless=True,
):
    if category_name not in CATEGORY_URLS:
        raise ValueError(
            f"Okänd kategori: "
            f"{category_name}"
        )

    try:
        from playwright.sync_api import (
            sync_playwright
        )

    except ImportError as exc:
        raise RuntimeError(
            "Playwright saknas."
        ) from exc

    base_url = (
        CATEGORY_URLS[
            category_name
        ]
    )

    all_items = []
    logs = []

    with sync_playwright() as playwright:
        browser = (
            playwright.chromium.launch(
                headless=headless
            )
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1800,
            }
        )

        for page_number in range(
            start_page,
            end_page + 1,
        ):
            url = build_page_url(
                base_url,
                page_number,
            )

            message = (
                f"Öppnar "
                f"{category_name} "
                f"sida {page_number}"
            )

            logs.append(
                message
            )

            print(
                message,
                flush=True,
            )

            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                page.wait_for_timeout(
                    1800
                )

                anchors = page.locator(
                    'a[href*="/item/"]'
                )

                count = anchors.count()

                page_items = []
                seen_links = set()

                for index in range(
                    count
                ):
                    item = extract_item(
                        anchors.nth(index),
                        category_name,
                        page_number,
                    )

                    if not item:
                        continue

                    if (
                        item["lank"]
                        in seen_links
                    ):
                        continue

                    seen_links.add(
                        item["lank"]
                    )

                    page_items.append(
                        item
                    )

                all_items.extend(
                    page_items
                )

                mark_page_loaded(
                    category_name,
                    page_number,
                )

                message = (
                    f"Sida "
                    f"{page_number}: "
                    f"{len(page_items)} annonser"
                )

                logs.append(
                    message
                )

                print(
                    message,
                    flush=True,
                )

            except Exception as exc:
                message = (
                    f"Fel på sida "
                    f"{page_number}: "
                    f"{exc}"
                )

                logs.append(
                    message
                )

                print(
                    message,
                    flush=True,
                )

            time.sleep(
                0.3
            )

        browser.close()

    return (
        all_items,
        logs,
    )