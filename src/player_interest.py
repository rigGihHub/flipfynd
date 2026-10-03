"""Bounded ranking context from sourced recent performances and player legacy.

Signals never alter a price estimate, profit, BUY evidence gate or max bid.
"""
from datetime import datetime, timezone
from functools import lru_cache
import json
from pathlib import Path

from src.player_market import normalize_player_name, get_player_context, match_player, _fold
from src.player_momentum import normalize_momentum_event, _parse_dt

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'


@lru_cache(maxsize=4)
def _read_data(filename, modified_ns):
    try:
        return json.loads((DATA_DIR / filename).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _load(filename):
    try:
        modified_ns = (DATA_DIR / filename).stat().st_mtime_ns
    except OSError:
        return {}
    return _read_data(filename, modified_ns)


@lru_cache(maxsize=4096)
def _identify_title(title):
    for sport in ('hockey', 'football'):
        match = match_player(title, sport)
        if match['confidence'] == 'high':
            return match['name']
    return None


def row_player(row):
    source = row.get('source_item') or {}
    name = row.get('player_name') or source.get('player_name')
    if not name:
        title = row.get('title') or source.get('titel') or source.get('title') or row.get('titel') or ''
        name = _identify_title(str(title))
    return normalize_player_name(name) if name else None


@lru_cache(maxsize=2048)
def player_key(name):
    return _fold(normalize_player_name(name))


def player_interest(name, sport=None, *, events=None, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    canonical = normalize_player_name(name)
    buckets = [sport] if sport in ('hockey', 'football') else ['hockey', 'football']
    legacy = None
    for bucket in buckets:
        legacy = _load('player_legacy.json').get(bucket, {}).get(canonical or '')
        if legacy:
            break
        context = get_player_context(canonical, bucket)
        if context.get('career_context_verified') and context.get('career_status') in {'active_legend', 'retired_legend'}:
            legacy = {'source_name': context.get('career_context_source'),
                      'source_url': context.get('career_context_source_url')}
            break
    feed = _load('player_form.json')
    recent = []
    seen = set()
    for raw in (feed.get('events') or []) if events is None else events:
        event = normalize_momentum_event(raw)
        if event.get('status') != 'READY' or not canonical:
            continue
        if player_key(event['player_name']) != player_key(canonical):
            continue
        if event.get('sport') not in buckets or event['event_type'] != 'performance_breakout':
            continue
        age = (now - _parse_dt(event['occurred_at'])).total_seconds() / 86400
        identity = (event['source_url'], event['occurred_at'])
        if not 0 <= age < 14 or identity in seen:
            continue
        seen.add(identity)
        recent.append(dict(event, age_days=round(age, 2), bonus=round(12 * (1-age/14), 2)))
    recent.sort(key=lambda e: e['occurred_at'], reverse=True)
    # A single performance adds up to 12 points; multiple distinct games up to 18.
    form = round(min(18, sum(e['bonus'] for e in recent)), 1)
    legend = 20 if legacy else 0
    return {'player_name': canonical, 'form_bonus': form, 'legend_bonus': legend,
            'ranking_bonus': min(30, round(form + legend, 1)),
            'legend': bool(legacy), 'legacy_source': legacy, 'recent_events': recent[:5],
            'feed_checked_at': feed.get('checked_at'), 'feed_sources': feed.get('sources') or []}


@lru_cache(maxsize=2048)
def _cached_row_interest(name, sport, minute, feed_revision, legacy_revision):
    return player_interest(name, sport, now=datetime.fromtimestamp(minute * 60, timezone.utc))


def row_interest(row):
    source = row.get('source_item') or {}
    def revision(filename):
        try:
            return (DATA_DIR / filename).stat().st_mtime_ns
        except OSError:
            return 0
    return _cached_row_interest(row_player(row), row.get('sport') or source.get('sport'),
                                int(datetime.now(timezone.utc).timestamp() // 60),
                                revision('player_form.json'), revision('player_legacy.json'))
