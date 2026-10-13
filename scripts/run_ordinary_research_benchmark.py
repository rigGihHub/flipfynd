"""Run with: python scripts/run_ordinary_research_benchmark.py"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ordinary_research_benchmark import evaluate_research_cases

if __name__ == '__main__':
    cases = json.loads((ROOT / 'data/ordinary_research_benchmark.json').read_text())['cases']
    result = evaluate_research_cases(cases)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['contract_passed'] else 1)
