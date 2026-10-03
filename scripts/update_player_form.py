"""Scheduled performance feed updater; can also be run manually."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.player_form_monitor import collect_form

path = Path(__file__).resolve().parents[1] / 'data/player_form.json'
previous = json.loads(path.read_text()) if path.exists() else {}
result = collect_form(previous)
if not any(source['ok'] for source in result['sources']):
    raise SystemExit('All performance sources failed; retaining the previous feed.')
path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f"Performance monitor: {len(result['events'])} recent events; {sum(s['ok'] for s in result['sources'])}/{len(result['sources'])} sources available")
