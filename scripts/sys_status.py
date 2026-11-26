"""System radar: the live state of every automatic job behind the site, stored for the owner only.
Reads workflow runs and the last commit of each data file, then encrypts the result with the
auditor's public key (vault/prof_key.json) into vault/sys.json."""
import json, os, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from agent_log import encrypt  # same key: only the owner code opens it

REPO = os.environ.get('GITHUB_REPOSITORY', '')
TOKEN = os.environ.get('GITHUB_TOKEN', '').strip()
OUT = os.path.join(ROOT, 'vault', 'sys.json')
WF = ['intraday', 'pro-data', 'resync', 'daily-report', 'health', 'agent-log', 'voice', 'gate', 'qa', 'agent', 'lib', 'optimize', 'guard', 'quick']
PATHS = {'data': 'data.json', 'live': 'pro/live_status.json', 'pro': 'pro/summary.json', 'radar': 'pro/ext_radar.json',
         'news': 'pro/news.json', 'refs': 'pro/refs.json', 'paper': 'vault/prof.json', 'agent': 'vault/agent_log.json',
         'voice': 'pro/voice', 'cal': 'pro/calendar.json'}


def get(path):
    if TOKEN:
        req = urllib.request.Request('https://api.github.com/' + path, headers={
            'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode())
    return json.loads(subprocess.check_output(['gh', 'api', path], text=True))


def iso(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')) if s else None


def main():
    repo = REPO or 'shaibanor/Wave'
    now = datetime.now(timezone.utc)
    d1, d7 = now - timedelta(days=1), now - timedelta(days=7)
    states = {w['path'].split('/')[-1][:-4]: w['state'] for w in get(f'repos/{repo}/actions/workflows?per_page=100').get('workflows', [])}
    wf = {}
    for name in WF:
        if name not in states:
            continue
        try:
            runs = get(f'repos/{repo}/actions/workflows/{name}.yml/runs?per_page=100&created=>={d7.strftime("%Y-%m-%d")}').get('workflow_runs', [])
            if not runs:
                runs = get(f'repos/{repo}/actions/workflows/{name}.yml/runs?per_page=1').get('workflow_runs', [])
        except Exception as e:
            print('runs failed', name, e)
            runs = []
        def cnt(since):
            rs = [r for r in runs if r.get('status') == 'completed' and iso(r['created_at']) >= since]
            return [sum(1 for r in rs if r.get('conclusion') in ('success', 'skipped')), len(rs)]
        last = runs[0] if runs else None
        lastok = next((r for r in runs if r.get('conclusion') == 'success'), None)
        dur = None
        if last and last.get('run_started_at') and last.get('updated_at') and last.get('status') == 'completed':
            dur = int((iso(last['updated_at']) - iso(last['run_started_at'])).total_seconds())
        days = []
        for i in range(6, -1, -1):
            day = (now - timedelta(days=i)).date()
            rs = [r for r in runs if r.get('status') == 'completed' and iso(r['created_at']).date() == day]
            days.append([sum(1 for r in rs if r.get('conclusion') in ('success', 'skipped')), len(rs)])
        hist = []
        for r in runs[:8]:
            d = None
            if r.get('run_started_at') and r.get('updated_at') and r.get('status') == 'completed':
                d = int((iso(r['updated_at']) - iso(r['run_started_at'])).total_seconds())
            hist.append({'at': r['created_at'], 'c': r.get('conclusion') or r.get('status'), 'dur': d, 'ev': r.get('event')})
        wf[name] = {'state': 'on' if states[name] == 'active' else 'off', 'days': days, 'runs': hist,
                    'last': {'st': last.get('status'), 'c': last.get('conclusion'), 'at': last['created_at'], 'ev': last.get('event'), 'dur': dur} if last else None,
                    'ok_at': lastok['created_at'] if lastok else None, 'd1': cnt(d1), 'd7': cnt(d7)}
        time.sleep(0.1)
    commits = {}
    for k, p in PATHS.items():
        try:
            cs = get(f'repos/{repo}/commits?path={p}&per_page=30')
        except Exception:
            cs = []
        if not cs:
            continue
        commits[k] = {'at': cs[0]['commit']['committer']['date'], 'm': cs[0]['commit']['message'].split('\n')[0][:80]}
        if k == 'data':
            pub = next((c for c in cs if c['commit']['message'].startswith('تحديث البيانات 20')), None)
            commits['publish'] = {'at': pub['commit']['committer']['date'], 'm': pub['commit']['message'][:60]} if pub else None
    h = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read() if os.path.exists(os.path.join(ROOT, 'index.html')) else ''
    rep = {'at': int(time.time()), 'site': 'closed' if 'id="maint"' in h else 'open', 'wf': wf, 'commits': commits}
    if '--plain' in sys.argv:
        json.dump(rep, open(sys.argv[sys.argv.index('--plain') + 1], 'w'), ensure_ascii=False, indent=1)
    json.dump(encrypt(rep), open(OUT, 'w'))
    print('stored', len(wf), 'jobs,', len(commits), 'files')


if __name__ == '__main__':
    main()
