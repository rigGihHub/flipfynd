import json
from pathlib import Path
from src.ordinary_research_benchmark import evaluate_research_cases
from src.asking_price_opportunity import build_asking_price_opportunity
from src.asking_price_ui import practical_price_suggestions
from src.ebay_browse_context import match_active_rows
from src.asking_price_opportunity import asking_research_identity
from src.candidate_review import build_candidate_review


def test_observed_contract_does_not_claim_real_profit_accuracy():
    cases = json.loads((Path(__file__).resolve().parents[1]/'data/ordinary_research_benchmark.json').read_text())['cases']
    result = evaluate_research_cases(cases)
    assert result['contract_passed'] and result['case_count'] == 8
    assert result['verified_real_trade_count'] == 0
    assert result['real_find_precision'] is result['real_find_recall'] is None


def test_synthetic_price_controls_detect_find_and_loss_but_never_create_sold():
    title = '2024 Topps Chrome Euro Lionel Messi #17'
    identity = asking_research_identity({'titel': title})
    raw = [dict(title=title, price=200, currency='SEK', url=f'https://www.ebay.com/itm/{n}',
                buying_options=['FIXED_PRICE']) for n in range(2)]
    context = {'rows': match_active_rows(raw, identity)}
    found = []
    for price in [20, 200]:
        item = dict(titel=title, pris=price, frakt=22)
        scenario = build_asking_price_opportunity(item, context)
        assert not scenario['creates_sold_evidence']
        found.append(practical_price_suggestions([dict(item, asking_price_opportunity=scenario)]))
    assert found[0] and not found[1]
    # A high asking price for a different issue must not manufacture the gap.
    wrong = [dict(row, title=title.replace('2024', '2023'), price=10000) for row in raw]
    scenario = build_asking_price_opportunity({'titel':title, 'pris':20,'frakt':22},
                                             {'rows':match_active_rows(wrong, identity)})
    assert not scenario['possible_find']


def test_partial_messi_report_remains_review_with_reservation_check():
    row = {'titel': 'Messi autograf /25', 'raw_text':'Reservationspris ej uppnått', 'pris':150}
    checks = build_candidate_review(row)['checks']
    assert 'Reservationspriset är inte uppnått' in checks[0]
