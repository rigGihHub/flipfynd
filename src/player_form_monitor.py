"""Collect explicit match statistics. No prose interpretation or invented form."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import requests

NHL = 'https://api-web.nhle.com/v1'
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/soccer'
LEAGUES = ('eng.1', 'esp.1', 'ger.1', 'ita.1', 'fra.1', 'uefa.champions', 'usa.1', 'ksa.1')


def football_events(payload, source_url):
    out = []
    for game in payload.get('events') or []:
        for comp in game.get('competitions') or []:
            if not (comp.get('status') or {}).get('type', {}).get('completed'):
                continue
            goals = Counter()
            for play in comp.get('details') or []:
                if not play.get('scoringPlay') or play.get('ownGoal') or play.get('shootout'):
                    continue
                athletes = play.get('athletesInvolved') or []
                # Require one explicitly identified scorer; do not credit assists.
                if len(athletes) == 1 and athletes[0].get('displayName'):
                    goals[athletes[0]['displayName']] += 1
            for name, count in goals.items():
                if count >= 2:
                    out.append({'player_name': name, 'sport': 'football',
                                'event_type': 'performance_breakout', 'occurred_at': game.get('date'),
                                'source_name': 'ESPN matchstatistik', 'source_type': 'sports_statistics',
                                'source_url': source_url, 'detail': f'{count} mål i en avslutad match',
                                'metric_after': count})
    return out


def hockey_events(box, names):
    if box.get('gameState') not in {'OFF', 'FINAL'} or box.get('gameType') not in {2, 3}:
        return []
    out = []
    for team in (box.get('playerByGameStats') or {}).values():
        for group in ('forwards', 'defense', 'goalies'):
            for player in team.get(group) or []:
                points = int(player.get('points') or 0)
                goals = int(player.get('goals') or 0)
                saves = int(player.get('saves') or 0)
                strong_goalie = group == 'goalies' and player.get('decision') == 'W' and saves >= 30 and float(player.get('savePctg') or 0) >= .95
                if points < 3 and goals < 2 and not strong_goalie:
                    continue
                name = names.get(player.get('playerId'))
                if not name:
                    continue
                detail = f'{saves} räddningar, {float(player.get("savePctg"))*100:.1f}% och seger' if strong_goalie else f'{goals} mål och {points} poäng i en avslutad match'
                out.append({'player_name': name, 'sport': 'hockey', 'event_type': 'performance_breakout',
                            'occurred_at': box.get('startTimeUTC'), 'source_name': 'NHL matchstatistik',
                            'source_type': 'official_league',
                            'source_url': f'{NHL}/gamecenter/{box["id"]}/boxscore',
                            'detail': detail, 'metric_after': saves if strong_goalie else points})
    return out


def collect_form(previous=None, *, now=None, get=None):
    now = now or datetime.now(timezone.utc)
    if get is None:
        session = requests.Session()
        session.headers['User-Agent'] = 'FlipFynd/1.0 player-performance-monitor'
        def get(url):
            response = session.get(url, timeout=(5, 20))
            response.raise_for_status()
            return response.json()
    sources, fresh, names = [], [], {}
    # Each source fails independently. An outage must not remove still-fresh evidence.
    def football_day(pair):
        league, offset = pair
        day = (now-timedelta(days=offset)).date()
        url = f'{ESPN}/{league}/scoreboard?dates={day:%Y%m%d}&limit=100'
        try:
            return football_events(get(url), url), {'name': f'ESPN {league} {day}', 'ok': True}
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            return [], {'name': f'ESPN {league} {day}', 'ok': False, 'error': type(exc).__name__}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for events, status in pool.map(football_day, [(league, offset) for league in LEAGUES for offset in range(4)]):
            fresh.extend(events)
            sources.append(status)
    for offset in range(4):
        day = (now-timedelta(days=offset)).date()
        try:
            games = get(f'{NHL}/score/{day}')
            for game in games.get('games') or []:
                if game.get('gameState') not in {'OFF', 'FINAL'} or game.get('gameType') not in {2, 3}:
                    continue
                box = get(f'{NHL}/gamecenter/{game["id"]}/boxscore')
                for team in (box.get('playerByGameStats') or {}).values():
                    for group in ('forwards', 'defense', 'goalies'):
                        for p in team.get(group) or []:
                            strong_goalie = group == 'goalies' and p.get('decision') == 'W' and int(p.get('saves') or 0) >= 30 and float(p.get('savePctg') or 0) >= .95
                            if int(p.get('points') or 0) < 3 and int(p.get('goals') or 0) < 2 and not strong_goalie:
                                continue
                            pid = p['playerId']
                            if pid not in names:
                                player = get(f'{NHL}/player/{pid}/landing')
                                names[pid] = f'{player["firstName"]["default"]} {player["lastName"]["default"]}'
                fresh.extend(hockey_events(box, names))
            sources.append({'name': f'NHL {day}', 'ok': True})
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            sources.append({'name': f'NHL {day}', 'ok': False, 'error': type(exc).__name__})
    from src.player_momentum import normalize_momentum_event, _parse_dt
    merged = {}
    for raw in (previous or {}).get('events', []) + fresh:
        event = normalize_momentum_event(raw)
        if event.get('status') != 'READY':
            continue
        age = now - _parse_dt(event['occurred_at'])
        if timedelta(0) <= age < timedelta(days=14):
            # A changing ESPN query range must not duplicate the same performance.
            merged[(event['player_name'], event['sport'], event['occurred_at'])] = event
    return {'checked_at': now.isoformat(), 'sources': sources,
            'events': sorted(merged.values(), key=lambda e:e['occurred_at'], reverse=True)}
