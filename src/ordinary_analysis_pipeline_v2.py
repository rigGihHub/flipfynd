"""FlipFynd ordinary analysis pipeline v2; fresh module identity for Streamlit."""
from __future__ import annotations
import time
import re
from src.analyzer import analyze_item
from src.analysis_cache import build_analysis_signature, get_cached_analysis, set_cached_analysis
from src.fast_analysis_pool import select_fast_analysis_pool
from src.analysis_budget import fast_analysis_budget
from src.card_listing_integrity import assess_listing_integrity
from src.card_market_knowledge import detect_market_attention
from src.adaptive_deepening import select_adaptive_full_analysis_indices, dynamic_deep_analysis_cap
from src.collector_signal_coverage import add_collector_signal_coverage_indices
from src.candidate_coverage import diversify_full_analysis_indices
from src.budget_discovery_coverage import add_budget_coverage_indices, budget_coverage_summary
from src.segment_discovery_coverage import add_segment_coverage_indices, segment_coverage_summary
from src.discovery_engine import build_discovery_map, select_discovery_indices
from src.market_sweep_engine import build_market_sweep_map, select_market_sweep_indices
from src.find_more_cards import select_second_pass_indices
from src.top5_verification_budget import add_top5_verification_indices
from src.pricing import total_acquisition_cost
from src.asking_price_opportunity import attach_asking_price_opportunity, select_asking_price_research

def analyze_data(
    data,
    sport,
    search,
    max_price,
    sale_type,
    full_limit,
    strategy,
    numbered_only,
    patch_only,
    auto_only,
    include_older=False,
    *,
    data_version="worker",
    sold_comp_data=None,
):
    analysis_started = time.perf_counter()
    raw_total_items = len(data)
    # Keep interactive analysis bounded even if an older cloud runtime still
    # contains a very large crawl. This is a CPU guard, not a ranking signal.
    # Keep the deployed pipeline self-contained while Streamlit may retain
    # an older imported engine module across hot reloads.
    rows = list(data or [])
    # Freshness is a discovery advantage: analyse newly listed cards first.
    # Prefer explicit listing timestamps; preserve loader order as fallback.
    def _freshness_key(row):
        for key in ("listed_at","created_at","start_time","published_at","fetched_at","seen_at"):
            value=(row or {}).get(key)
            if value:
                return str(value)
        return ""
    if any(_freshness_key(row) for row in rows):
        rows.sort(key=_freshness_key, reverse=True)
    # Self-contained bounded preparation: avoid any hot-reloaded fetcher module
    # attributes in the interactive analysis path.
    cap = 1500
    def _bounded(source):
        buckets = {}
        for row in source:
            key = str((row or {}).get("source_category") or "unknown")
            bucket = buckets.setdefault(key, [])
            if len(bucket) < cap:
                bucket.append(row)
        return [row for bucket in buckets.values() for row in bucket]
    market_data = _bounded(rows)
    # Stability first: do not depend on a separately hot-reloaded latest-market
    # module in the interactive path. The saved dataset is already newest-first;
    # bounded per-category analysis keeps the CPU guard.
    data = _bounded(rows)
    debug = {
        "total_items": raw_total_items,
        "performance_items": len(data),
        "after_sport": 0,
        "valid_price": 0,
        "within_budget": 0,
        "after_search": 0,
        "after_sale_type": 0,
        "after_feature_filters": 0,
        "missing_or_invalid_price": 0,
        "over_budget": 0,
        "search_miss": 0,
        "sale_type_miss": 0,
        "feature_filter_miss": 0,
        "fast_candidates": 0,
        "full_analysis": 0,
        "cache_hits": 0,
        "final_results": 0,
    }

    candidates = []
    fast_pool_source = []

    data_version = str(data_version or "worker")

    # Comps ska alltid komma från samma sport som objektet som analyseras.
    def _sport_of(item):
        source = str((item or {}).get("source_category") or "").casefold()
        if "fotboll" in source or "football" in source:
            return "football"
        if "hockey" in source or "nhl" in source:
            return "hockey"
        return None

    sport_items = [item for item in market_data if isinstance(item, dict)
                   and _sport_of(item) in {None, sport}]
    sold_items = [item for item in (sold_comp_data or []) if isinstance(item, dict)
                  and _sport_of(item) in {None, sport}]
    market_items = sport_items + sold_items

    # Seller presentation context: only descriptive metadata. It must never
    # create a valuation. A high generic-title ratio can reveal listings that
    # informed buyers may find more easily than the wider market.
    seller_rows = {}
    for row in sport_items:
        seller = next((str(row.get(k)).strip() for k in ("saljare","säljare","seller","seller_name","username") if row.get(k) and str(row.get(k)).strip()), "Okänd")
        if seller == "Okänd":
            continue
        title = str(row.get("titel") or row.get("title") or "").strip().lower()
        generic = (len(title) < 28 or title in {"hockeykort", "fotbollskort", "samlarkort"}
                   or title.startswith("hockeykort ") or title.startswith("fotbollskort "))
        bucket = seller_rows.setdefault(seller, {"count": 0, "generic": 0})
        bucket["count"] += 1
        bucket["generic"] += int(generic)
    for row in sport_items + data:
        seller = next((str(row.get(k)).strip() for k in ("saljare","säljare","seller","seller_name","username") if row.get(k) and str(row.get(k)).strip()), "Okänd")
        stats = seller_rows.get(seller)
        if stats:
            row["seller_listing_count"] = stats["count"]
            row["seller_generic_title_ratio"] = stats["generic"] / max(1, stats["count"])

    for item in data:
        if not isinstance(
            item,
            dict,
        ):
            continue

        item_sport = _sport_of(item)

        if (
            item_sport
            and item_sport
            != sport
        ):
            continue

        debug[
            "after_sport"
        ] += 1

        price = item.get(
            "pris"
        )

        if (
            not isinstance(price, (int, float))
            or price <= 0
        ):
            debug["missing_or_invalid_price"] += 1
            continue

        debug["valid_price"] += 1

        total_cost = total_acquisition_cost(
            price,
            item.get("frakt"),
        )

        if total_cost is None or total_cost > max_price:
            debug["over_budget"] += 1
            continue

        debug["within_budget"] += 1

        if not (not search or all(word in (" ".join(str(item.get(k) or "") for k in ("titel","raw_text")).casefold().replace("-"," ")) for word in str(search).casefold().replace("-"," ").split())):
            debug["search_miss"] += 1
            continue

        debug["after_search"] += 1

        # Cheap filters must run before any card analysis. This makes a changed
        # checkbox/filter almost instant instead of re-analysing hundreds of
        # listings that will be discarded anyway.
        direct_sale_type = (("Köp nu" if "köp nu" in " ".join(str(item.get(k) or "") for k in ("sale_type","raw_text","titel")).casefold() else ("Auktion" if any(x in " ".join(str(item.get(k) or "") for k in ("sale_type","raw_text","titel")).casefold() for x in ("auktion","utropspris","ledande bud"," bud")) else "Okänd")))

        if (
            sale_type == "Endast auktioner" and direct_sale_type != "Auktion"
        ) or (
            sale_type == "Endast Köp nu" and direct_sale_type != "Köp nu"
        ):
            debug["sale_type_miss"] += 1
            continue

        debug["after_sale_type"] += 1

        if (
            (numbered_only and not bool(re.search(r"(?<!\d)\d{1,4}\s*/\s*\d{1,4}(?!\d)|\b(?:numbered|numrerad)\b", " ".join(str(item.get(k) or "") for k in ("titel","raw_text","full_description")).casefold())))
            or (patch_only and not bool(re.search(r"\b(?:patch|relic|memorabilia|jersey|game[- ]used|player[- ]worn)\b", " ".join(str(item.get(k) or "") for k in ("titel","raw_text","full_description")).casefold())))
            or (auto_only and not bool(re.search(r"\b(?:auto|autograph|autographed|hard[- ]signed|on[- ]card)\b", " ".join(str(item.get(k) or "") for k in ("titel","raw_text","full_description")).casefold())))
        ):
            debug["feature_filter_miss"] += 1
            continue

        debug["after_feature_filters"] += 1

        fast_pool_source.append(item)

    debug["cheap_filtered_candidates"] = len(fast_pool_source)
    debug["filter_seconds"] = round(time.perf_counter() - analysis_started, 3)
    integrity_eligible = [
        item for item in fast_pool_source
        if assess_listing_integrity(item)["eligible_physical_single_card"]
    ]
    debug["integrity_eligible_candidates"] = len(integrity_eligible)
    debug["integrity_rejected_candidates"] = len(fast_pool_source) - len(integrity_eligible)
    fast_pool_budget = fast_analysis_budget(len(fast_pool_source), context="ordinary")
    fast_pool_source = select_fast_analysis_pool(
        integrity_eligible,
        cap=fast_pool_budget,
        exploration_fraction=0.25,
    )
    debug["fast_pool_budget"] = fast_pool_budget
    debug["fast_pool_selected"] = len(fast_pool_source)
    debug["fast_pool_skipped"] = max(0, debug["cheap_filtered_candidates"] - len(fast_pool_source))

    fast_started = time.perf_counter()
    for item in fast_pool_source:
        fast = analyze_item(
            item,
            mode="fast",
            strategy_mode=strategy,
            sport=sport,
        )

        attention = detect_market_attention(
            f"{item.get('titel', '')} {item.get('raw_text', '') or ''}",
            sport=sport,
        )
        candidates.append(
            (
                item,
                fast,
                attention,
            )
        )
    debug["fast_analysis_seconds"] = round(time.perf_counter() - fast_started, 3)

    # Full-analysis preselection may prioritize known scarce/chase structures so
    # they are not missed by the cheap fast pass. This boost does NOT change
    # market value, profit, max bid or the final result ranking.
    candidates.sort(
        key=lambda value: (
            value[1].get("rank_score", 0)
            + value[2].get("score", 0)
            + min(12, int(value[1].get("player_card_demand_preselection_boost", 0) or 0)),
            value[1].get("rank_score", 0),
            value[1].get("player_card_demand_review_priority_score", 0),
            value[1].get("player_market_score", 0),
        ),
        reverse=True,
    )

    debug[
        "fast_candidates"
    ] = len(
        candidates
    )

    results = []
    dynamic_deep_cap = dynamic_deep_analysis_cap(candidates, base_limit=full_limit, floor=8, max_cap=16)
    adaptive_indices = select_adaptive_full_analysis_indices(candidates, base_limit=full_limit, hard_cap=dynamic_deep_cap)
    adaptive_indices, collector_coverage_added = add_collector_signal_coverage_indices(
        candidates,
        adaptive_indices,
        extra_slots=3,
        hard_cap=dynamic_deep_cap,
    )
    full_indices = diversify_full_analysis_indices(
        candidates,
        adaptive_indices,
        base_limit=full_limit,
        hard_cap=dynamic_deep_cap,
        coverage_slots=16,
        max_per_player=3,
    )
    full_indices, budget_added = add_budget_coverage_indices(
        candidates,
        full_indices,
        budget=max_price,
        extra_slots=3,
        hard_cap=dynamic_deep_cap,
        max_per_player=2,
    )
    full_indices, segment_added = add_segment_coverage_indices(
        candidates,
        full_indices,
        budget=max_price,
        extra_slots=6,
        hard_cap=dynamic_deep_cap,
        max_per_player=2,
    )
    # Spend remaining deep-analysis/external-research capacity on candidates
    # most likely to surface in Top 5, so asking-price guards cover the rows
    # where a false positive would hurt most.
    full_indices, top5_verification_added = add_top5_verification_indices(
        candidates,
        full_indices,
        hard_cap=dynamic_deep_cap,
        reserve_slots=5,
        max_per_player=2,
    )
    # Price-data coverage pass: reserve part of the bounded deep budget for
    # exact-identifiable rows that can receive official eBay active-price
    # context. This directly addresses the "480 analysed, no usable price
    # indication" failure mode.
    asking_candidates = []
    for idx, (original, fast, attention) in enumerate(candidates):
        merged = {**original, **fast}
        asking_candidates.append({"source_item": merged, "_candidate_index": idx})
    asking_routes = select_asking_price_research(asking_candidates, limit=12)
    asking_indices = []
    for routed in asking_routes:
        idx = routed.get("_candidate_index")
        if isinstance(idx, int) and idx not in full_indices:
            asking_indices.append(idx)
    # Keep hard CPU cap: replace weakest tail slots rather than expanding it.
    for idx in asking_indices:
        if idx in full_indices:
            continue
        if len(full_indices) < dynamic_deep_cap:
            full_indices.append(idx)
        elif full_indices:
            full_indices[-1] = idx
    full_indices = list(dict.fromkeys(full_indices))[:dynamic_deep_cap]

    full_index_set = set(full_indices)
    debug["asking_price_routed"] = len(asking_indices)
    debug["adaptive_full_selected"] = len(adaptive_indices)
    debug["collector_signal_coverage_added"] = len(collector_coverage_added)
    debug["dynamic_deep_cap"] = dynamic_deep_cap
    debug["adaptive_extra_full"] = max(0, len(adaptive_indices) - min(full_limit, len(candidates)))
    debug["coverage_full_selected"] = len(full_indices)
    debug["coverage_diversified_added"] = len(set(full_indices) - set(adaptive_indices))
    debug["budget_coverage_added"] = len(budget_added)
    debug["budget_coverage_bands"] = budget_coverage_summary(candidates, full_indices, max_price)
    debug["segment_coverage_added"] = len(segment_added)
    debug["segment_coverage"] = segment_coverage_summary(candidates, full_indices, max_price)
    debug["top5_verification_added"] = len(top5_verification_added)
    discovery_map = build_discovery_map(candidates)
    debug["discovery_hunter_counts"] = discovery_map.get("hunter_counts", {})
    market_sweep_map = build_market_sweep_map(candidates)
    debug["market_sweep_route_counts"] = market_sweep_map.get("route_counts", {})
    debug["market_sweep_deepened"] = 0
    debug["discovery_deepened"] = 0
    debug["second_pass_triggered"] = False
    debug["second_pass_full"] = 0

    def _run_full_analysis(idx):
        original, _fast, _attention = candidates[idx]
        signature = build_analysis_signature(
            original,
            data_size=len(data),
            mode=f"{sport}_{strategy}_{data_version}",
        )
        cached = get_cached_analysis(signature)
        if cached:
            debug["cache_hits"] += 1
            return cached

        full = analyze_item(
            original,
            all_items=market_items,
            mode="full",
            strategy_mode=strategy,
            sport=sport,
        )
        set_cached_analysis(signature, full)
        debug["full_analysis"] += 1
        return full

    full_started = time.perf_counter()
    full_by_index = {}
    for idx in full_indices:
        full_by_index[idx] = _run_full_analysis(idx)

    # Find More Cards: when the first deep pass yields no BUY, inspect more of
    # the already-filtered candidate pool. User filters and all BUY thresholds
    # remain unchanged; only more candidates receive the existing full analysis.
    first_pass_has_buy = any(
        str(item.get("beslut") or "").startswith("KÖP")
        for item in full_by_index.values()
    )
    if not first_pass_has_buy and len(candidates) > len(full_index_set):
        market_sweep_indices = select_market_sweep_indices(
            candidates,
            full_index_set,
            extra_limit=3,
            total_hard_cap=dynamic_deep_cap,
            max_per_player=2,
        )
        after_sweep = full_index_set.union(market_sweep_indices)
        discovery_indices = select_discovery_indices(
            candidates,
            after_sweep,
            extra_limit=8,
            total_hard_cap=dynamic_deep_cap,
            max_per_player=2,
        )
        remaining_room = max(0, dynamic_deep_cap - len(full_index_set) - len(market_sweep_indices) - len(discovery_indices))
        fallback_indices = select_second_pass_indices(
            len(candidates),
            after_sweep.union(discovery_indices),
            extra_limit=min(4, remaining_room),
            total_hard_cap=dynamic_deep_cap,
        )
        extra_indices = market_sweep_indices + discovery_indices + fallback_indices
        debug["market_sweep_deepened"] = len(market_sweep_indices)
        debug["discovery_deepened"] = len(discovery_indices)
        if extra_indices:
            debug["second_pass_triggered"] = True
            debug["second_pass_full"] = len(extra_indices)
            for idx in extra_indices:
                full_by_index[idx] = _run_full_analysis(idx)
                full_index_set.add(idx)

    for idx, (original, fast, _attention) in enumerate(candidates):
        analysed = full_by_index.get(idx, fast)
        # Asking-price acquisition is intentionally limited to the deep-analysis
        # budget. Fast-only rows keep discovery cheap; deep rows carry the
        # external/active-market context needed by Top 5's false-positive guard.
        # Preserve source URL/provenance even if a cached result predates those
        # fields.
        if isinstance(analysed, dict):
            analysed = dict(analysed)
            analysed["lank"] = (
                analysed.get("lank") or analysed.get("url")
                or original.get("lank") or original.get("url")
            )
            analysed["url"] = analysed.get("url") or analysed.get("lank")
        results.append(analysed)

    debug["asking_context_candidates"] = sum(
        1 for row in results
        if isinstance(row, dict) and isinstance(row.get("asking_price_opportunity"), dict)
    )
    debug["asking_context_covered"] = sum(
        1 for row in results
        if isinstance(row, dict)
        and isinstance(row.get("asking_price_opportunity"), dict)
        and (row.get("asking_price_opportunity") or {}).get("reference_asking_price")
    )

    results.sort(
        key=lambda item: (
            item.get(
                "rank_score",
                0,
            ),
            item.get(
                "player_market_score",
                0,
            ),
            item.get(
                "risk_adjusted_profit",
                0,
            ),
        ),
        reverse=True,
    )

    debug[
        "final_results"
    ] = len(
        results
    )
    debug["deep_analysed_candidates"] = len(full_by_index)
    debug["full_analysis_seconds"] = round(time.perf_counter() - full_started, 3)
    debug["total_analysis_seconds"] = round(time.perf_counter() - analysis_started, 3)

    return (
        results,
        debug,
    )


__all__=['analyze_data']
