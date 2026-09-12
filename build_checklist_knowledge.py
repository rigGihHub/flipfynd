"""Audit FlipFynd's curated checklist knowledge base.

Usage:
    python build_checklist_knowledge.py
    python build_checklist_knowledge.py --json
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from src.checklist_knowledge_pipeline import audit_knowledge, load_knowledge

p = argparse.ArgumentParser()
p.add_argument('--json', action='store_true')
a = p.parse_args()
path = Path('data/card_market_knowledge.json')
report = audit_knowledge(load_knowledge(path))
if a.json:
    print(json.dumps(report, ensure_ascii=False, indent=2))
else:
    print(f"sources={report['source_count']} signals={report['signal_count']} products={len(report['product_coverage'])}")
    print(f"invalid_sources={report['invalid_source_count']} invalid_signals={report['invalid_signal_count']} conflicts={report['conflict_count']}")
    for row in sorted(report['product_coverage'], key=lambda r: (r['objective_signals'], r['signals']))[:8]:
        print(f"GAP {row['product_family']}: {row['signals']} signals, {row['objective_signals']} objective")
