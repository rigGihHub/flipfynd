import json
import re
from datetime import datetime, timezone
from urllib.parse import urljoin


INTEREST_PATTERNS = {
    "rookie_program": [
        r"\byoung guns?\b", r"\bfuture watch\b", r"\brated rookie\b",
        r"\bprizm rookie\b", r"\btopps chrome rookie\b", r"\bmerlin rookie\b",
    ],
    "autograph": [r"\bauto(?:graph)?\b", r"\bsigned\b", r"\bsignature\b", r"\bautograf\b"],
    "relic_patch": [r"\bpatch\b", r"\brelic\b", r"\bmemorabilia\b", r"\bjersey\b"],
    "chase": [r"\bssp\b", r"\bcase hit\b", r"\bgenesis\b", r"\bcolor blast\b", r"\bwhite tiger\b"],
    "serial": [r"\b\d{1,4}\s*/\s*\d{1,4}\b", r"\b1\s*/\s*1\b", r"\bone of one\b"],
    "parallel": [r"\bparallel\b", r"\bhigh gloss\b", r"\bexclusives?\b", r"\boutburst\b", r"\bpmg\b"],
}


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def score_detail_priority(item):
    """Return a discovery-only priority for opening the item page.

    The score only decides which listings deserve richer metadata first. It is
    deliberately disconnected from valuation, profit, ROI and max bid.
    """
    title = _norm(item.get("titel")).lower()
    raw = _norm(item.get("raw_text")).lower()
    text = f"{title} {raw}".strip()
    score = 0
    reasons = []

    weights = {
        "rookie_program": 18,
        "autograph": 16,
        "relic_patch": 14,
        "chase": 22,
        "serial": 20,
        "parallel": 12,
    }
    for label, patterns in INTEREST_PATTERNS.items():
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            score += weights[label]
            reasons.append(label)

    # Generic/short titles can hide relevant details in the full description.
    if title and len(title.split()) <= 5:
        score += 12
        reasons.append("kort/generisk titel")
    if not item.get("image_urls"):
        score += 8
        reasons.append("saknar kategori-bild")
    if item.get("frakt") is None:
        score += 4
        reasons.append("frakt saknas")

    return min(100, score), reasons


def select_detail_candidates(items, known_links=None, limit=12):
    known_links = {str(x) for x in (known_links or set()) if x}
    ranked = []
    for item in items or []:
        link = item.get("lank")
        if not link:
            continue
        priority, reasons = score_detail_priority(item)
        is_new = link not in known_links
        already_rich = bool(item.get("detail_enriched_at") and item.get("full_description"))
        # Prefer new listings, then old listings that still lack useful detail.
        freshness = 2 if is_new else (1 if not already_rich else 0)
        if freshness == 0:
            continue
        ranked.append((freshness, priority, item, reasons))

    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    out = []
    for freshness, priority, item, reasons in ranked[: max(0, int(limit or 0))]:
        clone = item
        clone["detail_priority_score"] = priority
        clone["detail_priority_reasons"] = reasons
        out.append(clone)
    return out


def parse_detail_text(body_text):
    text = _norm(body_text)
    lower = text.lower()
    result = {}

    # Prefer the shipping amount shown on the item detail page. This is more
    # authoritative than the category-card text and avoids presenting the
    # conservative 29 SEK fallback as if it were an observed shipping price.
    if "fri frakt" in lower:
        result["detail_shipping"] = 0
        result["detail_shipping_source"] = "Tradera-annons"
    else:
        shipping_patterns = [
            r"frakt(?:\s+från)?\s*:?\s*(\d[\d\s.]*)\s*kr",
            r"leverans(?:kostnad)?\s*:?\s*(\d[\d\s.]*)\s*kr",
        ]
        for pattern in shipping_patterns:
            match = re.search(pattern, lower, flags=re.IGNORECASE)
            if match:
                try:
                    result["detail_shipping"] = int(match.group(1).replace(" ", "").replace(".", ""))
                    result["detail_shipping_source"] = "Tradera-annons"
                    break
                except ValueError:
                    pass

    bid_patterns = [
        r"(\d+)\s+bud\b",
        r"bud\s*\(?\s*(\d+)\s*\)?",
    ]
    for pattern in bid_patterns:
        match = re.search(pattern, lower, flags=re.IGNORECASE)
        if match:
            result["bid_count"] = int(match.group(1))
            break

    end_patterns = [
        r"(?:avslutas|slutar|auktionen avslutas)\s*:?\s*([^|]{3,80}?)(?=\s{2,}|\bfrakt\b|\bsäljare\b|$)",
        r"(?:tid kvar)\s*:?\s*([^|]{3,60}?)(?=\s{2,}|\bfrakt\b|$)",
    ]
    for pattern in end_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = _norm(match.group(1))
            if value:
                result["exact_end_text"] = value[:100]
                break

    seller_patterns = [
        r"(?:säljare|seller)\s*:?\s*([^|]{2,80}?)(?=\s{2,}|\bomdöme\b|\bfrakt\b|$)",
    ]
    for pattern in seller_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            seller = _norm(match.group(1))
            if 2 <= len(seller) <= 80:
                result["seller_detail"] = seller
                break

    return result


def _json_ld_objects(html):
    objects = []
    for raw in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        str(html or ""),
        flags=re.IGNORECASE | re.DOTALL,
    ):
        try:
            data = json.loads(raw.strip())
        except Exception:
            continue
        if isinstance(data, list):
            objects.extend(x for x in data if isinstance(x, dict))
        elif isinstance(data, dict):
            graph = data.get("@graph")
            if isinstance(graph, list):
                objects.extend(x for x in graph if isinstance(x, dict))
            objects.append(data)
    return objects


def extract_jsonld_detail(html):
    result = {}
    images = []
    for obj in _json_ld_objects(html):
        if not result.get("detail_title") and obj.get("name"):
            result["detail_title"] = _norm(obj.get("name"))[:240]
        if not result.get("full_description") and obj.get("description"):
            result["full_description"] = _norm(obj.get("description"))[:8000]
        image = obj.get("image")
        if isinstance(image, str):
            images.append(image)
        elif isinstance(image, list):
            images.extend(x for x in image if isinstance(x, str))
    if images:
        result["detail_image_urls"] = list(dict.fromkeys(images))[:16]
    return result


def _collect_page_images(page):
    urls = []
    try:
        og = page.locator('meta[property="og:image"]')
        for idx in range(min(og.count(), 4)):
            content = og.nth(idx).get_attribute("content")
            if content:
                urls.append(urljoin("https://www.tradera.com", content))
    except Exception:
        pass
    try:
        images = page.locator("img")
        for idx in range(min(images.count(), 30)):
            img = images.nth(idx)
            src = img.get_attribute("src") or img.get_attribute("data-src")
            if src:
                urls.append(urljoin("https://www.tradera.com", src))
            srcset = img.get_attribute("srcset") or ""
            for candidate in srcset.split(","):
                candidate = candidate.strip().split(" ")[0]
                if candidate:
                    urls.append(urljoin("https://www.tradera.com", candidate))
    except Exception:
        pass
    return list(dict.fromkeys(urls))[:16]


def enrich_listing_detail(page, item, timeout_ms=30000):
    link = item.get("lank")
    enriched = dict(item)
    enriched["detail_enrichment_status"] = "failed"
    enriched["detail_source"] = "tradera_item_page"
    if not link:
        enriched["detail_enrichment_error"] = "saknar annonslänk"
        return enriched

    try:
        page.goto(link, wait_until="domcontentloaded", timeout=int(timeout_ms))
        page.wait_for_timeout(700)
        html = page.content()
        body_text = ""
        try:
            body_text = page.locator("body").inner_text(timeout=5000)
        except Exception:
            pass

        parsed = extract_jsonld_detail(html)
        parsed.update(parse_detail_text(body_text))

        # Fallback description from metadata if JSON-LD did not contain one.
        if not parsed.get("full_description"):
            try:
                meta = page.locator('meta[name="description"]')
                if meta.count():
                    desc = _norm(meta.first.get_attribute("content"))
                    if desc:
                        parsed["full_description"] = desc[:8000]
            except Exception:
                pass

        page_images = _collect_page_images(page)
        if page_images:
            existing = parsed.get("detail_image_urls") or []
            parsed["detail_image_urls"] = list(dict.fromkeys(existing + page_images))[:16]

        enriched.update({k: v for k, v in parsed.items() if v not in (None, "", [])})
        if parsed.get("detail_shipping") is not None:
            enriched["frakt"] = parsed.get("detail_shipping")
            enriched["shipping_source"] = parsed.get("detail_shipping_source") or "Tradera-annons"
        enriched["detail_enriched_at"] = datetime.now(timezone.utc).isoformat()
        enriched["detail_enrichment_status"] = "ok"
        enriched.pop("detail_enrichment_error", None)
    except Exception as exc:
        enriched["detail_enrichment_error"] = _norm(exc)[:300]
    return enriched


def enrich_selected_listings(browser, items, known_links=None, limit=12, timeout_ms=30000, log=print):
    candidates = select_detail_candidates(items, known_links=known_links, limit=limit)
    if not candidates:
        return items, {"attempted": 0, "enriched": 0, "failed": 0}

    by_link = {item.get("lank"): item for item in items if item.get("lank")}
    page = browser.new_page(viewport={"width": 1440, "height": 1800})
    enriched_count = 0
    failed_count = 0
    try:
        for index, candidate in enumerate(candidates, start=1):
            if log:
                log(f"Detaljberikar {index}/{len(candidates)}: {candidate.get('titel', 'annons')}")
            enriched = enrich_listing_detail(page, candidate, timeout_ms=timeout_ms)
            by_link[candidate.get("lank")] = enriched
            if enriched.get("detail_enrichment_status") == "ok":
                enriched_count += 1
            else:
                failed_count += 1
    finally:
        page.close()

    rebuilt = [by_link.get(item.get("lank"), item) for item in items]
    return rebuilt, {
        "attempted": len(candidates),
        "enriched": enriched_count,
        "failed": failed_count,
    }
