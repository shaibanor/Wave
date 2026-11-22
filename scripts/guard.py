"""Daily guard of the paper bot's self-improvement.

The bot may change its own rules without asking (scripts/optimize.py), but only forward.
Every day this guard replays the live record and checks two things:
  - the success rate of the last 20 closed trades has not fallen more than 5 points below what the
    current rules achieved in their test,
  - the portfolio has not fallen more than 5% since the last automatic change took effect.
If either happens: the most recent automatic change (if any, within 45 days) is rolled back, the
optimizer is paused, and the owner is alerted with a GitHub issue (a notification on his phone and
e-mail). When the record recovers, the alert closes itself and the optimizer resumes."""
import datetime as dt, json, os, subprocess, sys, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, 'pro', 'rules.json'); LOG = os.path.join(ROOT, 'pro', 'opt_log.json'); OUT = os.path.join(ROOT, 'pro', 'guard.json')
DROP_WIN = 5.0; DROP_DD = 5.0; WINDOW = 20; MIN_N = 10
REPO = os.environ.get('GITHUB_REPOSITORY', 'shaibanor/Wave'); TOKEN = os.environ.get('GITHUB_TOKEN', '')

def jload(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return d

def gh(method, path, body=None):
    if not TOKEN: return None
    req = urllib.request.Request('https://api.github.com/' + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read().decode() or 'null')
    except Exception as e:
        print('github api:', e); return None

def live_book():
    fd, out = tempfile.mkstemp(suffix='.json'); os.close(fd)
    env = dict(os.environ, PAPER_DEBUG=out, PAPER_NOWRITE='1')
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'paper.py')], env=env, capture_output=True, timeout=1800)
    try: return json.load(open(out))
    finally: os.remove(out)

def main():
    R = jload(RULES, {}); log = jload(LOG, []); prev = jload(OUT, {})
    b = live_book(); roll = [t for t in b['closed'] if t.get('roll')]
    last = roll[-WINDOW:]; n = len(last)
    win = round(sum(1 for t in last if t['win']) / n * 100, 1) if n else None
    peak = 0; dd = 0
    for _, v in b.get('curve') or []:
        peak = max(peak, v); dd = max(dd, (1 - v / peak) * 100 if peak else 0)
    cur_dd = round((1 - (b['curve'][-1][1] / max(v for _, v in b['curve']))) * 100, 1) if b.get('curve') else 0
    ref = None
    for e in reversed(log):
        if e.get('changed') and e.get('after'): ref = e['after']['full']['win']; break
        if e.get('before'): ref = e['before']['full']['win']; break
    if ref is None: ref = ((R.get('rolling') or {}).get('backtest') or {}).get('v4', {}).get('win_rate')
    reasons = []; now = dt.datetime.now(dt.timezone.utc); cut = (now.date() - dt.timedelta(days=45)).isoformat()
    if n >= MIN_N and ref is not None and win < ref - DROP_WIN:
        reasons.append(f'نسبة النجاح في آخر {n} صفقة {win}% أقل من نسبة القواعد الحالية في الاختبار ({ref}%) بأكثر من {DROP_WIN:g} نقاط')
    # a step back caused by an automatic change: the portfolio fell more than 5% since that change took effect
    lc = next((e for e in reversed(log) if e.get('changed') and not e.get('reverted') and e['date'] >= cut), None)
    since_change = None
    if lc and b.get('curve'):
        base = next((v for d_, v in b['curve'] if str(d_)[:10] >= lc['date']), None)
        if base: since_change = round((1 - b['curve'][-1][1] / base) * 100, 1)
        if since_change is not None and since_change > DROP_DD:
            reasons.append(f"المحفظة نزلت {since_change}% منذ التعديل التلقائي «{lc.get('param')}» في {lc['date']} (الحد {DROP_DD:g}%)")
    state = {'at': now.strftime('%Y-%m-%d %H:%M UTC'), 'state': 'alert' if reasons else 'ok', 'reasons': reasons,
             'win_last': win, 'n_last': n, 'ref_win': ref, 'drawdown_now': cur_dd, 'since_change': since_change, 'rolled_back': prev.get('rolled_back'), 'issue': prev.get('issue')}
    if reasons:
        # roll back the most recent automatic change that is still in force
        for e in reversed(log):
            if e.get('changed') and not e.get('reverted') and e['date'] >= cut and e.get('path'):
                node = R['rolling']; keys = e['path'].split('.')
                for k in keys[:-1]: node = node[k]
                node[keys[-1]] = e['from']; e['reverted'] = now.date().isoformat()
                R['rolling'].setdefault('auto_changes', []).append({'date': now.date().isoformat(), 'param': e['path'], 'from': e['to'], 'to': e['from'], 'why': 'تراجع الأداء'})
                json.dump(R, open(RULES, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); json.dump(log, open(LOG, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                state['rolled_back'] = {'date': now.date().isoformat(), 'param': e.get('param'), 'from': e['to'], 'to': e['from']}
                break
        if not state.get('issue'):
            body = ('تنبيه من حارس المحفظة التجريبية في منصة تيكو.\n\n' + '\n'.join('- ' + r for r in reasons) +
                    (f"\n\nتم التراجع تلقائيًا عن آخر تعديل: {state['rolled_back']['param']} من {state['rolled_back']['from']} إلى {state['rolled_back']['to']}." if state.get('rolled_back') else '\n\nلا يوجد تعديل تلقائي حديث للتراجع عنه؛ السبب على الأرجح حركة السوق نفسها.') +
                    '\n\nالتحسين التلقائي متوقف حتى يتعافى الأداء. يمكنك مراجعة التفاصيل في رادار النظام ← مكتب مدير المحفظة. هذا التنبيه يُغلق تلقائيًا عند التعافي.')
            r = gh('POST', f'repos/{REPO}/issues', {'title': 'تنبيه: تراجع أداء المحفظة التجريبية', 'body': body})
            if r and r.get('number'): state['issue'] = r['number']
    else:
        if prev.get('state') == 'alert' and prev.get('issue'):
            gh('POST', f"repos/{REPO}/issues/{prev['issue']}/comments", {'body': 'تعافى الأداء وعاد ضمن الحدود؛ استؤنف التحسين التلقائي.'})
            gh('PATCH', f"repos/{REPO}/issues/{prev['issue']}", {'state': 'closed'})
        state['issue'] = None
    json.dump(state, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(state, ensure_ascii=False))

if __name__ == '__main__':
    main()
