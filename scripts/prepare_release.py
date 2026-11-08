"""Prepare the selected measured campaign and every development attempt for review."""

import argparse
import json
from pathlib import Path
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('run', type=Path)
parser.add_argument('--attempt', type=Path, action='append', default=[])
parser.add_argument('--agent', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
public_roots = [root/'docs', root/'site/public']
campaigns = []
for folder in args.attempt + [args.run]:
    report_path = folder/'report.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else None
    entry = {'id': folder.name, 'status': 'complete' if report else 'failed before final audit',
             'evidence': f'evidence/{folder.name}/'}
    if report:
        entry.update(mode=report['manifest']['mode'], validation=report['validation_after']['detected'],
                     audit=report['audit_after']['detected'], denominator=report['audit_after']['total'],
                     false_rejections=report['audit_after']['false_rejections'], seconds=report['elapsed_seconds'])
    else:
        entry['reason'] = 'Invalid generated action JSON in proposal 3; this prompted the bounded-repair implementation.'
    campaigns.append(entry)
    for public in public_roots:
        destination = public/'evidence'/folder.name
        if destination.exists():
            if report and (destination/'report.json').read_bytes() != report_path.read_bytes():
                raise SystemExit(f'Refusing to replace different evidence: {destination}')
        else:
            shutil.copytree(folder, destination, ignore=shutil.ignore_patterns('__pycache__', '*.seed', '.env*'))

for public in public_roots:
    public.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.run/'report.json', public/'report.json')
    for name in ('mongodb-receipt.json', 'mongodb-verification.json'):
        if (args.run/name).exists():
            shutil.copy2(args.run/name, public/name)
    lab = public/'lab'
    lab.mkdir(exist_ok=True)
    for name in ('index.html', 'app.js', 'style.css', 'favicon.svg'):
        shutil.copy2(root/'web'/name, lab/name)
    shutil.copy2(args.run/'report.json', lab/'report.json')
    (public/'campaigns.json').write_text(json.dumps({
        'selected': args.run.name, 'attempts': campaigns,
        'historical_baseline': {'id': 'openai-live-001', 'validation': 7, 'audit': 6, 'denominator': 8},
        'note': 'Development history on public synthetic corpora. The expanded revision has 30 faults per split; prior runs have 8. Scores across revisions are not directly comparable. Prompts and providers changed during earlier development; this is not a controlled provider benchmark. All attempts are retained.'
    }, indent=2))
    if args.agent:
        agent_dest = public/'evidence'/args.agent.name
        agent_dest.mkdir(parents=True, exist_ok=True)
        names = ('agent-info.json', 'broken-receipt.json', 'correct-receipt.json')
        for name in names:
            shutil.copy2(args.agent/name, agent_dest/name)
        (public/'agent-demo.json').write_text(json.dumps({
            'evidence': f'evidence/{args.agent.name}/',
            'service': json.loads((args.agent/'agent-info.json').read_text()),
            'cases': {kind: json.loads((args.agent/f'{kind}-receipt.json').read_text()) for kind in ('broken', 'correct')}
        }, indent=2))
    if public != root/'docs':
        shutil.copytree(root/'docs/assets', public/'assets', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('*.js', '*.css'))
print(f'Prepared {args.run.name}, {len(campaigns)} development attempts, and signed agent receipts.')
