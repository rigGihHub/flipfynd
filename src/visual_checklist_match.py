"""Match visual card findings against curated official product/checklist knowledge."""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any
DEFAULT_KNOWLEDGE_PATH = Path(__file__).resolve().parents[1] / 'data' / 'card_market_knowledge.json'
def _norm(v): return re.sub(r'[^a-z0-9]+',' ',str(v or '').casefold()).strip()
def _contains(text, phrase):
    p=_norm(phrase); return bool(p and p in text)
def _tokens(f):
    parts=[f.get('set_or_product'),f.get('parallel_or_variant'),f.get('season_or_year'),f.get('card_number'),*(f.get('visual_clues') or [])]
    if f.get('rookie_marker_visible')=='yes': parts += ['rookie','young guns']
    if f.get('autograph_visible')=='yes': parts += ['autograph','auto']
    if f.get('relic_or_patch_visible')=='yes': parts += ['patch','relic','memorabilia']
    return _norm(' '.join(str(x) for x in parts if x))
def _load(path=None):
    p=Path(path) if path else DEFAULT_KNOWLEDGE_PATH
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return {'sources':[],'signals':[]}
def match_visual_to_checklist_knowledge(findings:dict,*,sport:str|None=None,knowledge_path=None,max_matches:int=4)->dict[str,Any]:
    knowledge=_load(knowledge_path); sources={str(s.get('id')):s for s in knowledge.get('sources',[]) if s.get('id')}; text=_tokens(findings or {})
    visual_product=_norm((findings or {}).get('set_or_product')); requested_sport=_norm(sport)
    den=(findings or {}).get('serial_denominator')
    try: den=int(den) if den not in (None,'') else None
    except (TypeError,ValueError): den=None
    matches=[]
    for sig in knowledge.get('signals',[]):
        ss=_norm(sig.get('sport'))
        if requested_sport and ss and requested_sport not in ss and ss not in requested_sport: continue
        pats=list(sig.get('patterns') or []); anyp=list(sig.get('patterns_any') or [])
        all_hit=bool(pats) and all(_contains(text,p) for p in pats); any_hit=bool(anyp) and any(_contains(text,p) for p in anyp)
        label_hit=_contains(text,sig.get('label')); program_hit=_contains(text,sig.get('program_family')); product_hit=_contains(text,sig.get('product_family'))
        if not (all_hit or any_hit or label_hit or program_hit): continue
        score=45; evidence=[]
        if all_hit: score+=22; evidence.append('visuella ord matchar checklistmönster')
        if any_hit: score+=14; evidence.append('variant/program matchar känd struktur')
        if label_hit: score+=15; evidence.append('variantnamnet matchar kunskapsbasen')
        if program_hit: score+=10; evidence.append('programfamilj matchar')
        if product_hit or (visual_product and _contains(_norm(sig.get('product_family')),visual_product)): score+=8; evidence.append('produktfamilj är kompatibel')
        expected=sig.get('print_run'); serial_status='unknown'; conflict=False
        # A print-run conflict is only meaningful when the *specific variant*
        # matched. A generic program-family hit (for example Young Guns) must
        # not make every other numbered Young Guns parallel look contradictory.
        specific_variant_hit = bool(label_hit or all_hit or any_hit)
        if expected not in (None,'') and den is not None and specific_variant_hit:
            try:
                expected=int(expected)
                if expected==den: score+=18; serial_status='match'; evidence.append(f'synlig /{den} matchar dokumenterad print run')
                else: score-=35; serial_status='conflict'; conflict=True; evidence.append(f'synlig /{den} avviker från dokumenterad /{expected}')
            except (TypeError,ValueError): pass
        src=sources.get(str(sig.get('source_id') or ''),{})
        status='Konflikt mot känd struktur' if conflict else ('Starkt strukturellt checkliststöd' if score>=80 and sig.get('source_id') else 'Möjlig känd variant/programstruktur')
        matches.append({'label':sig.get('label') or sig.get('program_family') or 'Känd struktur','status':status,'match_score':max(0,min(100,score)),'confidence':str(sig.get('confidence') or 'unknown'),'category':sig.get('category'),'rarity_signal':sig.get('rarity_signal'),'product_family':sig.get('product_family'),'program_family':sig.get('program_family'),'expected_print_run':expected,'observed_serial_denominator':den,'serial_status':serial_status,'conflict':conflict,'evidence':evidence,'importance_reason':sig.get('importance_reason'),'source_id':sig.get('source_id'),'source_url':src.get('url'),'source_publisher':src.get('publisher'),'source_notes':src.get('notes'),'specific_variant_match':specific_variant_hit})
    matches.sort(key=lambda m:(bool(m.get('specific_variant_match')),not m['conflict'],m['match_score'],bool(m['source_url'])),reverse=True); matches=matches[:max(1,int(max_matches))]
    conflicts=[m for m in matches if m['conflict']]; strong=[m for m in matches if not m['conflict'] and m['match_score']>=80 and m['source_url']]
    status='Bilddetalj krockar med checkliststruktur' if conflicts else ('Känd variant/program stöds av checklistkunskap' if strong else ('Möjlig checklistmatch – verifiera exakt kort' if matches else 'Ingen säker checklistmatch'))
    return {'status':status,'matches':matches,'strong_match_count':len(strong),'conflict_count':len(conflicts),'can_verify_exact_card':False,'safe_for_valuation':False,'note':'Checklistmatch verifierar endast struktur/variantprogram. Spelare, kortnummer och autenticitet måste fortfarande verifieras separat.'}
