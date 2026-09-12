from src.visual_checklist_match import match_visual_to_checklist_knowledge

def test_outburst_red_25_gets_source_backed_structural_match():
    r=match_visual_to_checklist_knowledge({'set_or_product':'Upper Deck Series 2','parallel_or_variant':'Young Guns Outburst Red','serial_numerator':7,'serial_denominator':25,'rookie_marker_visible':'yes','visual_clues':['Young Guns','Outburst Red']},sport='hockey')
    m=next(x for x in r['matches'] if x['label']=='Young Guns Outburst Red /25'); assert m['serial_status']=='match'; assert m['source_url']; assert r['safe_for_valuation'] is False; assert r['can_verify_exact_card'] is False

def test_wrong_serial_denominator_is_explicit_conflict():
    r=match_visual_to_checklist_knowledge({'set_or_product':'Upper Deck Series 2','parallel_or_variant':'Young Guns Outburst Red','serial_denominator':99,'rookie_marker_visible':'yes','visual_clues':['Young Guns','Outburst Red']},sport='hockey')
    m=next(x for x in r['matches'] if x['label']=='Young Guns Outburst Red /25'); assert m['conflict']; assert m['serial_status']=='conflict'; assert r['conflict_count']>=1

def test_generic_shiny_card_does_not_become_specific_parallel():
    r=match_visual_to_checklist_knowledge({'set_or_product':'Upper Deck','parallel_or_variant':None,'rookie_marker_visible':'unknown','visual_clues':['glossy foil pattern']},sport='hockey'); assert not r['matches']


def test_generic_program_hit_does_not_create_false_print_run_conflict():
    r=match_visual_to_checklist_knowledge({'set_or_product':'Upper Deck Series 2','parallel_or_variant':'Young Guns Outburst Red','serial_denominator':25,'rookie_marker_visible':'yes','visual_clues':['Young Guns','Outburst Red']},sport='hockey')
    bad=[m for m in r['matches'] if m.get('conflict') and m.get('label')=='Young Guns High Gloss']
    assert not bad
