"""Research priorities and checks from observed card features; never prices a card."""
import re
from src.card_parser import parse_card_features, extract_serial_number, autograph_features, has_relic_material_evidence
from src.seller_collector_signals import collector_signals


def collector_research_priority(item, fast=None):
    """Prefer concrete variants over generic score/price guesses, across sports."""
    item, fast = item or {}, fast or {}
    title = str(item.get('titel') or item.get('title') or '')
    serial = extract_serial_number(title)
    scarcity = (4 if serial == 1 else 3 if serial and serial <= 25 else
                2 if serial and serial <= 99 else 1 if serial else 0)
    autograph = int(autograph_features(title)['is_auto'])
    material = int(bool(has_relic_material_evidence(title) or re.search(r'\b(?:patch|relic)\b', title, re.I)))
    signals = collector_signals(item)
    return (autograph + scarcity + material, int(signals.get('score') or 0),
            float(fast.get('player_card_demand_score') or item.get('player_card_demand_score') or 0))


def build_candidate_review(item):
    """Explain title claims, missing exact identity and the next evidence needed."""
    item = item or {}
    from src.card_explanation import build_card_identity_summary
    features = parse_card_features(str(item.get('titel') or item.get('title') or ''))
    identity = build_card_identity_summary(item)
    reasons = []
    checks = []
    if features.get('is_auto'):
        kind = features.get('autograph_type')
        reasons.append('Annonsen anger ' + ('on-card-autograf' if kind == 'on_card' else
                                           'sticker-autograf' if kind == 'sticker' else 'autograf'))
        checks.append('Kontrollera autografens äkthet och typ på fram- och baksida')
    serial = features.get('serial_number')
    if serial:
        copy = features.get('serial_copy_number')
        reasons.append('Annonsen anger numrering ' + (f'{copy}/{serial}' if copy else f'/{serial}'))
        checks.append(f'Bekräfta /{serial} på kortet; jämför samma numrerade variant')
    if features.get('is_patch') or features.get('is_jersey'):
        reasons.append('Annonsen anger relik/memorabilia')
        checks.append('Läs materialuppgiften på baksidan och kontrollera samma relikvariant')
    if features.get('is_rookie'):
        reasons.append('Rookie/RC-signal i annonsen')
        checks.append('Bekräfta rookieår och exakt rookieprogram')
    if features.get('set_name'):
        reasons.append('Identifierat program i titeln: ' + features['set_name'])
    if identity['missing']:
        checks.append('Identifiera ' + ', '.join(identity['missing']) + ' från kortet eller checklistan')
    if item.get('identity_conflicts') or item.get('detail_evidence_fusion_has_conflict'):
        checks.insert(0, 'Lös motstridiga identitetsuppgifter innan prisjämförelsen används')
    if not item.get('valuation_display_safe'):
        checks.append('Hitta sålda jämförelser med samma program, år, kortnummer och variant')
    checks.append('Kontrollera aktuellt pris, frakt, eventuellt reservationspris och skick')
    return {'reasons': reasons or ['Bland de återstående analyserade alternativen'],
            'checks': list(dict.fromkeys(checks)), 'identity': identity,
            'priority': collector_research_priority(item)}
