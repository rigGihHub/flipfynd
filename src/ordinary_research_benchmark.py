"""Observed identity regressions, separate from unknown realised-trade accuracy."""
from src.card_parser import parse_card_features
from src.best_alternatives import build_best_alternatives, candidate_status


def evaluate_research_cases(cases):
    checks = []
    for case in cases:
        parsed = parse_card_features(case['title'])
        errors = [key for key, expected in case['expected_fields'].items() if parsed.get(key) != expected]
        # A fixed synthetic acquisition cost isolates candidate visibility.
        # It is not the historical listing price and never creates a price comp.
        rows = build_best_alternatives([{'titel': case['title'], 'pris': 100,
                                        'source_category': 'Fotboll'}])['rows']
        visible = bool(rows)
        buy = bool(rows and candidate_status(rows[0]) == 'Köpunderlag finns')
        checks.append({'id': case['id'], 'source_kind': case['source_kind'],
                       'field_errors': errors, 'review_missed': case['expected_review'] and not visible,
                       'excluded_product_visible': not case['expected_review'] and visible,
                       'unsupported_buy': buy})
    return {'case_count': len(checks), 'contract_passed': all(
        not row['field_errors'] and not row['review_missed'] and not row['excluded_product_visible']
        and not row['unsupported_buy'] for row in checks), 'cases': checks,
        'verified_real_trade_count': 0, 'real_find_precision': None, 'real_find_recall': None,
        'note': 'Verklig fyndträffsäkerhet kan inte beräknas utan verifierade köp- och försäljningsutfall.'}
