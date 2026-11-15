"""Install source-bound search questions and audit retrieval; no weight training.

Run from the repository root: python -m scripts.prepare_assistant --apply
Add --live-limit 12 to exercise the actual local answer/review models as well.
Live results are observations, never automatically approved answers.
"""
import argparse
import asyncio
import json
import sqlite3
import time
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from pathlib import Path

from backend import app as api
from backend.rule_assistant import RuleQuestion, knowledge, retrieve, source_fingerprint

ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / 'backend' / 'assistant_question_bank.json'


def prepare(games, bank):
    staged, cases = [], []
    by_id = {game['id']: game for game in games}
    for game_id, groups in bank.items():
        if game_id.startswith('_'):
            continue
        if game_id not in by_id:
            raise ValueError(f'Missing game: {game_id}')
        game = by_id[game_id]
        sources = {source.id: source for source in knowledge({**game, 'retrieval_hints': []})}
        questions = defaultdict(list)
        for source_id, examples, heldout in groups:
            source = sources.get(source_id)
            expected = bank['_source_hashes'][game_id][source_id]
            if source is None or source_fingerprint(source) != expected:
                raise ValueError(f'Source changed: {game_id}/{source_id}; inspect and update the bank first')
            questions[source_id].extend(examples)
            for question in examples:
                cases.append(dict(game_id=game_id, source_id=source_id, question=question, split='preparation'))
            cases.append(dict(game_id=game_id, source_id=source_id, question=heldout, split='heldout'))
        hints = [{'source_id': sid, 'source_hash': source_fingerprint(sources[sid]),
                  'questions': list(dict.fromkeys(values))} for sid, values in questions.items()]
        # Replace only the bank's own hints; preserve user-created associations.
        preserved = [h for h in game.get('retrieval_hints', [])
                     if isinstance(h, dict) and h.get('origin') != 'assistant-question-bank-v1']
        staged.append({**game, 'retrieval_hints': preserved + [
            {**hint, 'origin': 'assistant-question-bank-v1'} for hint in hints]})
    return staged, cases


def audit(games, staged, cases):
    baseline = {g['id']: knowledge({**g, 'retrieval_hints': []}) for g in games}
    expanded = {g['id']: knowledge(g) for g in staged}
    results = []
    for case in cases:
        row = dict(case)
        for label, catalog in [('before', baseline), ('after', expanded)]:
            ids = [s.id for s in retrieve(catalog[case['game_id']], case['question'], limit=5)]
            row[label] = ids
            row[label + '_found'] = case['source_id'] in ids
        results.append(row)
    metrics = {}
    for split in ('preparation', 'heldout'):
        subset = [r for r in results if r['split'] == split]
        metrics[split] = {'total': len(subset), **{
            label + '_recall_at_5': sum(r[label + '_found'] for r in subset)
            for label in ('before', 'after')}}
    return {'metrics': metrics, 'retrieval_cases': results}


async def live_audit(cases, limit):
    # Round-robin across games so a short smoke run still covers all six.
    grouped = defaultdict(list)
    for case in cases:
        if case['split'] == 'heldout':
            grouped[case['game_id']].append(case)
    ordered = [rows[i] for i in range(max(map(len, grouped.values())))
               for rows in grouped.values() if i < len(rows)]
    results = []
    for case in ordered[:limit]:
        started = time.monotonic()
        try:
            result = await api.ask_game_rule(case['game_id'], RuleQuestion(question=case['question']), None)
            row = {**case, **result.model_dump(), 'seconds': round(time.monotonic() - started, 2)}
        except Exception as error:
            row = {**case, 'error': str(getattr(error, 'detail', error)),
                   'seconds': round(time.monotonic() - started, 2)}
        results.append(row)
        print(json.dumps({k: v for k, v in row.items() if k not in ('sources',)}, ensure_ascii=False), flush=True)
        # Keep partial observations if the process is interrupted.
        (ROOT / 'state' / 'assistant-live-audit.json').write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Back up SQLite and install search questions')
    parser.add_argument('--live-limit', type=int, default=0)
    args = parser.parse_args()
    bank = json.loads(BANK_PATH.read_text(encoding='utf-8'))
    games = api.read_games()
    staged, cases = prepare(games, bank)
    report = audit(games, staged, cases)
    report['note'] = 'Search preparation, not model weight training. Recall measures retrieval only; live answers need content review.'
    report['applied'] = args.apply
    if args.apply:
        backup = api.DATABASE_PATH.with_name('games-before-ai-preparation-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.sqlite3')
        with closing(sqlite3.connect(api.DATABASE_PATH)) as original, closing(sqlite3.connect(backup)) as target:
            original.backup(target)
        # One transaction; no partially installed question bank.
        with closing(api.connect()) as connection, connection:
            for game in staged:
                validated = api.Game(**game).model_dump()
                connection.execute('UPDATE games SET payload = ? WHERE id = ?',
                                   (json.dumps(validated, ensure_ascii=False), game['id']))
        report['backup'] = str(backup)
    (ROOT / 'state').mkdir(exist_ok=True)
    report_path = ROOT / 'state' / 'assistant-preparation-report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['metrics'], ensure_ascii=False, indent=2), flush=True)
    if args.live_limit:
        if not args.apply:
            raise SystemExit('Use --apply for live checks against the installed bank.')
        report['live'] = asyncio.run(live_audit(cases, args.live_limit))
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
