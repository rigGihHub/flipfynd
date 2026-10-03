"""Resume bounded research using listing fingerprints, never cached eBay data."""
import hashlib
import json
import time


def listing_fingerprint(row):
    from src.analysis_scope import _listing_key
    payload = [_listing_key(row), row.get('titel') or row.get('title'),
               row.get('pris', row.get('price')), row.get('frakt', row.get('shipping'))]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, default=str).encode()).hexdigest()


def fresh_checkpoint(checkpoint, *, now=None):
    checkpoint = checkpoint or {}
    now = time.time() if now is None else now
    try:
        if not 0 <= now - float(checkpoint.get('created_at', checkpoint.get('updated_at', 0))) < 3600:
            return {}
    except (ValueError, TypeError):
        return {}
    return checkpoint


def extend_checkpoint(routes, assessed, previous=None, *, description_checked=()):
    from src.analysis_scope import _listing_key
    previous = fresh_checkpoint(previous)
    completed = set(previous.get('completed') or [])
    current = {_listing_key(row): row.get('asking_price_opportunity') or {} for row in assessed}
    for route in routes:
        row = route.get('source_item') or route
        scenario = current.get(_listing_key(row), {})
        status = scenario.get('status') or ''
        # Recheck profitable leads on every round. Errors remain retryable;
        # only successfully screened nonpositive listings can be skipped.
        if (status and not status.startswith('COMPARISON_') and not scenario.get('http_status')
                and scenario.get('comparison_failure_reason') != 'NO_CONVERTIBLE_PRICE_OR_FX'
                and not scenario.get('research_signal') and not scenario.get('possible_find')):
            completed.add(listing_fingerprint(row))
    return {'created_at': previous.get('created_at', previous.get('updated_at', time.time())),
            'updated_at': time.time(), 'completed': sorted(completed),
            'description_checked': sorted(set(previous.get('description_checked') or [])
                                          | set(description_checked))}
