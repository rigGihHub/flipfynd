import json
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from src.player_knowledge import get_player_knowledge

DATA_FILE = Path(__file__).resolve().parents[1] / 'data' / 'player_market.json'


def _fold(text):
    text = str(text or '').casefold()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


@lru_cache(maxsize=1)
def load_player_market():
    try:
        data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    except Exception:
        data = {'hockey': {}, 'football': {}, 'aliases': {}}
    return data


def get_player_database(sport):
    data = load_player_market()
    raw = data.get('football' if sport == 'football' else 'hockey', {})
    return {
        name: (int(info.get('score', 45)), str(info.get('tier', 'medium')))
        for name, info in raw.items()
    }


def get_all_player_names():
    data = load_player_market()
    names = set(data.get('hockey', {})) | set(data.get('football', {}))
    names |= set(data.get('aliases', {}))
    return sorted(names)


def normalize_player_name(name):
    if not name:
        return None
    clean = str(name).strip()
    aliases = load_player_market().get('aliases', {})
    if clean in aliases:
        return aliases[clean]
    folded = _fold(clean)
    for alias, canonical in aliases.items():
        if _fold(alias) == folded:
            return canonical
    for sport in ('hockey', 'football'):
        for canonical in load_player_market().get(sport, {}):
            if _fold(canonical) == folded:
                return canonical
    return clean


def _candidate_ngrams(title, min_words=2, max_words=3):
    words = _fold(title).split()
    for size in range(min(max_words, len(words)), min_words - 1, -1):
        for i in range(0, len(words) - size + 1):
            yield ' '.join(words[i:i + size])


def match_player(title, sport):
    '''Conservative player identification with typo tolerance.'''
    folded_title = f' {_fold(title)} '
    database = get_player_database(sport)
    aliases = load_player_market().get('aliases', {})
    canonical_to_variants = {name: {name} for name in database}
    for alias, canonical in aliases.items():
        if canonical in database:
            canonical_to_variants.setdefault(canonical, {canonical}).add(alias)

    for canonical, variants in canonical_to_variants.items():
        for variant in variants:
            folded = _fold(variant)
            if folded and f' {folded} ' in folded_title:
                return {'name': canonical, 'confidence': 'high', 'match_type': 'exact', 'ratio': 1.0}

    ngrams = list(_candidate_ngrams(title))
    candidates = []
    for canonical in database:
        canonical_folded = _fold(canonical)
        if len(canonical_folded.split()) < 2:
            continue
        best = 0.0
        for ng in ngrams:
            if abs(len(ng) - len(canonical_folded)) > 4:
                continue
            best = max(best, SequenceMatcher(None, ng, canonical_folded).ratio())
        if best >= 0.92:
            candidates.append((best, canonical))

    if candidates:
        candidates.sort(reverse=True)
        best_ratio, best_name = candidates[0]
        if len(candidates) == 1 or best_ratio - candidates[1][0] >= 0.035:
            return {'name': best_name, 'confidence': 'medium', 'match_type': 'fuzzy', 'ratio': round(best_ratio, 3)}

    return {'name': None, 'confidence': 'low', 'match_type': 'none', 'ratio': 0.0}


def get_player_context(name, sport):
    """Return explicit source-backed context; never infer missing career status."""
    canonical = normalize_player_name(name)
    kb = get_player_knowledge(canonical, sport)
    raw = load_player_market().get('football' if sport == 'football' else 'hockey', {}).get(canonical or '', {})
    return {
        'career_status': kb.get('career_status') or raw.get('career_status'),
        'era': kb.get('era') or raw.get('era'),
        'activity_status': kb.get('activity_status'),
        'position': kb.get('position'),
        'team': kb.get('team'),
        'date_of_birth': kb.get('date_of_birth'),
        'career_context_source': kb.get('source_name') or raw.get('career_context_source'),
        'career_context_source_url': kb.get('source_url'),
        'career_context_verified': bool(kb.get('verified') or raw.get('career_context_verified', False)),
    }
