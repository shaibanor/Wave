"""Weekly self-improvement of the paper bot.

Tries small one-step changes to the rolling rules, replays each on the full history and on the
last 90 days, and adopts at most ONE change, and only when:
  - the success rate rises (full history) by at least MIN_GAIN points,
  - total growth over the full history is not lower,
  - the deepest drawdown is not worse by more than 1 point,
  - over the last 90 days the success rate and growth are not lower.
Every run is logged in pro/opt_log.json, including weeks with no change."""
import copy, datetime as dt, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, 'pro', 'rules.json')
LOG = os.path.join(ROOT, 'pro', 'opt_log.json')
FULL_FROM = '2025-03-01'
MIN_GAIN = 0.5
R = json.load(open(RULES, encoding='utf-8'))
RO = R['rolling']

def get(d, path):
    for k in path[:-1]: d = d[k]
    return d[path[-1]]

def put(d, path, v):
    for k in path[:-1]: d = d.setdefault(k, {})
    d[path[-1]] = v

# (path inside rolling, label, step, low, high)
KNOBS = [(('trigger', 'rsi_below'), 'حد RSI للدخول', 5, 35, 60),
         (('stop', 'atr_k'), 'مسافة الوقف (ATR)', 0.5, 1.5, 4.5),
         (('breakeven_at_target_frac',), 'نقل الوقف للتعادل عند نسبة من الهدف', 0.1, 0.3, 0.9),
         (('max_hold_days',), 'أقصى مدة للصفقة (أيام)', 3, 5, 21),
         (('adaptive', 'max_atr'), 'أقصى هدف (ATR)', 1, 2, 6),
         (('adaptive', 'min_net_pct'), 'أقل ربح صافٍ مقبول %', 0.1, 0.4, 1.2)]

def candidates():
    out = []
    for path, label, step, lo, hi in KNOBS:
        try: cur = get(RO, path)
        except Exception: continue
        for v in (cur - step, cur + step):
            v = round(v, 4)
            if lo <= v <= hi: out.append((path, label, cur, v))
    return out

def replay(override, start):
    o = {'cycle': {'target_pct': 100000}, 'rolling': override}
    fd, out = tempfile.mkstemp(suffix='.json'); os.close(fd)
    env = dict(os.environ, RULES_OVERRIDE=json.dumps(o), PAPER2_LAUNCH=start, PAPER_DEBUG=out, PAPER_NOWRITE='1')
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'paper.py')], env=env, capture_output=True, timeout=1800)
    try: b = json.load(open(out))
    finally: os.remove(out)
    c = b['closed']; peak = dd = 0
    for _, v in b['curve']:
        peak = max(peak, v); dd = max(dd, 1 - v / peak if peak else 0)
    w = sum(1 for t in c if t['win'])
    return {'n': len(c), 'win': round(w / len(c) * 100, 1) if c else 0.0, 'pct': round(b['totals']['pct'], 1), 'dd': round(dd * 100, 1)}

def main():
    today = dt.date.today(); recent = (today - dt.timedelta(days=90)).isoformat()
    cands = candidates()
    jobs = [('base', None, {}, FULL_FROM), ('base', None, {}, recent)]
    for i, (path, label, cur, v) in enumerate(cands):
        ov = {}; put(ov, path, v)
        jobs += [(i, path, ov, FULL_FROM), (i, path, ov, recent)]
    with ThreadPoolExecutor(max_workers=max(2, os.cpu_count() or 2)) as ex:
        res = list(ex.map(lambda j: replay(j[2], j[3]), jobs))
    M = {}
    for (k, _, _, st), r in zip(jobs, res): M.setdefault(k, {})['full' if st == FULL_FROM else 'rec'] = r
    B = M['base']; ok = []
    for i, (path, label, cur, v) in enumerate(cands):
        F, Rc = M[i]['full'], M[i]['rec']
        if (F['win'] >= B['full']['win'] + MIN_GAIN and F['pct'] >= B['full']['pct'] and F['dd'] <= B['full']['dd'] + 1
                and Rc['win'] >= B['rec']['win'] and Rc['pct'] >= B['rec']['pct']):
            ok.append((F['win'], F['pct'], i))
    entry = {'date': today.isoformat(), 'tested': len(cands), 'before': B, 'rule': f'يُعتمد تغيير واحد فقط إذا ارتفعت نسبة النجاح {MIN_GAIN} نقطة على الأقل دون نقص الربح أو زيادة التراجع، وثبت ذلك في آخر 90 يومًا'}
    if ok:
        _, _, i = max(ok); path, label, cur, v = cands[i]
        put(RO, path, v)
        R['version'] = R.get('version', 0)
        RO.setdefault('auto_changes', []).append({'date': today.isoformat(), 'param': '.'.join(path), 'from': cur, 'to': v})
        json.dump(R, open(RULES, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        entry.update({'changed': True, 'param': label, 'path': '.'.join(path), 'from': cur, 'to': v, 'after': M[i]})
    else:
        best = max(range(len(cands)), key=lambda i: (M[i]['full']['win'], M[i]['full']['pct'])) if cands else None
        entry.update({'changed': False, 'note': 'لم يحقق أي تغيير شروط التحسين، فبقيت القواعد كما هي',
                      'best_try': {'param': cands[best][1], 'to': cands[best][3], 'result': M[best]} if best is not None else None})
    log = []
    try: log = json.load(open(LOG, encoding='utf-8'))
    except Exception: pass
    log.append(entry); json.dump(log[-52:], open(LOG, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(entry, ensure_ascii=False)[:600])

if __name__ == '__main__':
    main()
