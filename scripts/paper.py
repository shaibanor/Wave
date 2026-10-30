#!/usr/bin/env python3
"""Unified paper portfolio. Replays deterministic rules from LAUNCH across all markets in
close-time order and writes the result encrypted to vault/book.json."""
import json, os, math, base64, datetime as dt
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
LAUNCH = os.environ.get('PAPER_LAUNCH', '2026-10-27')
START_USD = 87000.0
SAR = 3.75
FEE = {'sa': 0.0015, 'us': 0.0005, 'cx': 0.001}
SLIP = 0.0005
RISK = 0.01
MAX_W = 0.12
MAX_OPEN = 12
MAX_HOLD = 30
BUFFER = 0.01
SWEEP = 'SPY'
ASSETS = [
    ('8311', 'عناية', 'sa'), ('1120', 'مصرف الراجحي', 'sa'), ('4340', 'الراجحي ريت', 'sa'), ('2222', 'أرامكو السعودية', 'sa'),
    ('1211', 'معادن', 'sa'), ('1180', 'البنك الأهلي السعودي', 'sa'), ('7010', 'إس تي سي', 'sa'), ('2010', 'سابك', 'sa'),
    ('2082', 'أكوا باور', 'sa'), ('4013', 'سليمان الحبيب', 'sa'), ('1010', 'بنك الرياض', 'sa'), ('1150', 'مصرف الإنماء', 'sa'),
    ('2280', 'المراعي', 'sa'), ('4190', 'جرير', 'sa'), ('1060', 'البنك الأول', 'sa'), ('5110', 'الكهرباء السعودية', 'sa'),
    ('2050', 'صافولا', 'sa'), ('1050', 'البنك السعودي الفرنسي', 'sa'), ('2020', 'سابك للمغذيات', 'sa'), ('4280', 'المملكة القابضة', 'sa'),
    ('BTC', 'بيتكوين', 'cx'), ('ETH', 'إيثيريوم', 'cx'), ('XRP', 'ريبل', 'cx'), ('BNB', 'بي إن بي', 'cx'), ('SOL', 'سولانا', 'cx'),
    ('TRX', 'ترون', 'cx'), ('DOGE', 'دوجكوين', 'cx'), ('ZEC', 'زي كاش', 'cx'), ('LINK', 'تشين لينك', 'cx'), ('ADA', 'كاردانو', 'cx'),
    ('AVAX', 'أفالانش', 'cx'), ('DOT', 'بولكادوت', 'cx'), ('LTC', 'لايتكوين', 'cx'), ('BCH', 'بيتكوين كاش', 'cx'), ('NEAR', 'نير', 'cx'),
    ('GOOGL', 'ألفابت (جوجل)', 'us'), ('META', 'ميتا', 'us'), ('AVGO', 'برودكوم', 'us'), ('TSM', 'TSMC', 'us'),
    ('JPM', 'جي بي مورغان', 'us'), ('LLY', 'إيلي ليلي', 'us'), ('V', 'فيزا', 'us'),
    ('AAPL', 'آبل', 'us'), ('MSFT', 'مايكروسوفت', 'us'), ('NVDA', 'إنفيديا', 'us'), ('AMZN', 'أمازون', 'us'), ('TSLA', 'تسلا', 'us'),
    ('NFLX', 'نتفليكس', 'us'), ('AMD', 'إيه إم دي', 'us'), ('COST', 'كوستكو', 'us'), ('BRK-B', 'بيركشاير هاثاواي', 'us'), ('UNH', 'يونايتد هيلث', 'us'),
    ('XOM', 'إكسون موبيل', 'us'), ('WMT', 'وولمارت', 'us'), ('QQQ', 'صندوق ناسداك 100', 'us'), ('GLD', 'صندوق الذهب', 'us'),
    ('SPY', 'صندوق إس آند بي 500', 'us'),
]
TFN = {'M': 'الشهري', 'W': 'الأسبوعي', 'D': 'اليومي'}
DIRN = {'up': 'صاعد', 'down': 'هابط', 'flat': 'محايد'}
W = {'M': .25, 'W': .25, 'D': .2}

# ---------- indicators (same definitions as the site) ----------
def ema(v, n):
    out = [None] * len(v)
    if len(v) < n: return out
    e = sum(v[:n]) / n; out[n - 1] = e; k = 2 / (n + 1)
    for i in range(n, len(v)):
        e = v[i] * k + e * (1 - k); out[i] = e
    return out

def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n: return out
    g = l = 0.0
    for i in range(1, n + 1):
        d = c[i] - c[i - 1]; g += max(d, 0); l += max(-d, 0)
    g /= n; l /= n; out[n] = 100 if l == 0 else 100 - 100 / (1 + g / l)
    for i in range(n + 1, len(c)):
        d = c[i] - c[i - 1]; g = (g * (n - 1) + max(d, 0)) / n; l = (l * (n - 1) + max(-d, 0)) / n
        out[i] = 100 if l == 0 else 100 - 100 / (1 + g / l)
    return out

def macd_hist(c):
    a, b = ema(c, 12), ema(c, 26)
    line = [x - y if x is not None and y is not None else None for x, y in zip(a, b)]
    idx = next((i for i, x in enumerate(line) if x is not None), None)
    sig = [None] * len(c)
    if idx is not None:
        e = ema(line[idx:], 9)
        for i, x in enumerate(e): sig[idx + i] = x
    return [x - s if x is not None and s is not None else None for x, s in zip(line, sig)]

def atr(b, n=14):
    out = [None] * len(b)
    if len(b) <= n: return out
    tr = [b[0]['h'] - b[0]['l']] + [max(x['h'] - x['l'], abs(x['h'] - b[i - 1]['c']), abs(x['l'] - b[i - 1]['c'])) for i, x in enumerate(b) if i]
    a = sum(tr[1:n + 1]) / n; out[n] = a
    for i in range(n + 1, len(b)):
        a = (a * (n - 1) + tr[i]) / n; out[i] = a
    return out

def swings(b, k=3, upto=None):
    H, L = [], []
    last = len(b) - 1 if upto is None else upto
    for i in range(k, len(b) - k):
        if i + k > last: break
        hi = all(b[i - j]['h'] < b[i]['h'] and b[i + j]['h'] <= b[i]['h'] for j in range(1, k + 1))
        lo = all(b[i - j]['l'] > b[i]['l'] and b[i + j]['l'] >= b[i]['l'] for j in range(1, k + 1))
        if hi: H.append(i)
        if lo: L.append(i)
    return H, L

def structure(b, H, L):
    H, L = H[-2:], L[-2:]
    if len(H) < 2 or len(L) < 2: return 0
    hh, hl = b[H[1]]['h'] > b[H[0]]['h'], b[L[1]]['l'] > b[L[0]]['l']
    return 1 if hh and hl else -1 if (not hh and not hl) else 0

def score(b, I, i):
    if i < 30: return None
    c = b[i]['c']; P = []
    if I['e50'][i] is not None: P.append(1 if c > I['e50'][i] else -1)
    if I['e200'][i] is not None and I['e50'][i] is not None: P.append(1 if I['e50'][i] > I['e200'][i] else -1)
    H, L = swings(b, upto=i); P.append(structure(b, H, L))
    if I['hist'][i] is not None: P.append(1 if I['hist'][i] > 0 else -1)
    if I['rsi'][i] is not None: P.append(1 if I['rsi'][i] > 55 else -1 if I['rsi'][i] < 45 else 0)
    s = sum(P) / len(P)
    return {'s': s, 'dir': 'up' if s >= .35 else 'down' if s <= -.35 else 'flat'}

def ind(b):
    c = [x['c'] for x in b]
    return {'e50': ema(c, 50), 'e200': ema(c, 200), 'rsi': rsi(c), 'hist': macd_hist(c), 'atr': atr(b)}

# ---------- data ----------
def bars(rows):
    return [{'t': int(r[0]), 'o': float(r[1]), 'h': float(r[2]), 'l': float(r[3]), 'c': float(r[4])} for r in rows if r[4] and r[4] > 0]

def day(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).date()

def complete(kind, d, now):
    if kind == 'cx':
        return now >= dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc) + dt.timedelta(days=1)
    tz = ZoneInfo('Asia/Riyadh' if kind == 'sa' else 'America/New_York')
    close = dt.datetime(d.year, d.month, d.day, 15, 30, tzinfo=tz) if kind == 'sa' else dt.datetime(d.year, d.month, d.day, 16, 20, tzinfo=tz)
    return now >= close

def load(aid, kind):
    p = os.path.join(ROOT, 'pro', kind, f'{aid}.json')
    j = json.load(open(p))
    if kind == 'cx':
        d = bars(j['1d']); m = bars(j.get('1M', []))
        for x in d: x['t'] = int(dt.datetime.combine(day(x['t']), dt.time(), dt.timezone.utc).timestamp())
    else:
        d = bars(j['d']); m = bars(j.get('m', []))
    return d, m

def week_key(d, kind):
    wd = d.weekday()  # Mon=0
    back = (wd + 1) % 7 if kind == 'sa' else wd
    return d - dt.timedelta(days=back)

def agg(daily, keyf):
    out, cur, k0 = [], None, None
    for x in daily:
        k = keyf(day(x['t']))
        if k != k0:
            if cur: out.append(cur)
            cur, k0 = dict(x), k
        else:
            cur['h'] = max(cur['h'], x['h']); cur['l'] = min(cur['l'], x['l']); cur['c'] = x['c']
    if cur: out.append(cur)
    return out

# ---------- data ----------
def bars(rows):
    return [{'t': int(r[0]), 'o': float(r[1]), 'h': float(r[2]), 'l': float(r[3]), 'c': float(r[4])} for r in rows if r[4] and r[4] > 0]

def day(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).date()

def close_time(kind, d):
    if kind == 'cx':
        return dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc) + dt.timedelta(days=1)
    tz = ZoneInfo('Asia/Riyadh' if kind == 'sa' else 'America/New_York')
    return dt.datetime(d.year, d.month, d.day, 15, 30, tzinfo=tz) if kind == 'sa' else dt.datetime(d.year, d.month, d.day, 16, 20, tzinfo=tz)

def load(aid, kind):
    j = json.load(open(os.path.join(ROOT, 'pro', kind, f'{aid}.json')))
    if kind == 'cx':
        d = bars(j['1d']); m = bars(j.get('1M', []))
        for x in d: x['t'] = int(dt.datetime.combine(day(x['t']), dt.time(), dt.timezone.utc).timestamp())
    else:
        d = bars(j['d']); m = bars(j.get('m', []))
    return d, m

def week_key(d, kind):
    wd = d.weekday()
    return d - dt.timedelta(days=(wd + 1) % 7 if kind == 'sa' else wd)

def agg(daily, keyf):
    out, cur, k0 = [], None, None
    for x in daily:
        k = keyf(day(x['t']))
        if k != k0:
            if cur: out.append(cur)
            cur, k0 = dict(x), k
        else:
            cur['h'] = max(cur['h'], x['h']); cur['l'] = min(cur['l'], x['l']); cur['c'] = x['c']
    if cur: out.append(cur)
    return out

def signals(aid, kind, now):
    """Per completed daily bar on/after LAUNCH: bar, close time and the causal multi-timeframe signal."""
    d, m = load(aid, kind)
    d = [x for x in d if now >= close_time(kind, day(x['t']))]
    I = ind(d); out = []
    for i, x in enumerate(d):
        ds = day(x['t'])
        if ds.isoformat() < LAUNCH: continue
        Dsc = score(d, I, i)
        wk = agg(d[:i + 1], lambda q: week_key(q, kind)); Wsc = score(wk, ind(wk), len(wk) - 1)
        ym = (ds.year, ds.month)
        mb = [y for y in m if (day(y['t']).year, day(y['t']).month) < ym] + agg([y for y in d[:i + 1] if (day(y['t']).year, day(y['t']).month) == ym], lambda q: (q.year, q.month))
        Msc = score(mb, ind(mb), len(mb) - 1)
        sc = {'M': Msc, 'W': Wsc, 'D': Dsc}
        tw = sum(W[k] for k in sc if sc[k]); S = sum(W[k] * sc[k]['s'] for k in sc if sc[k]) / tw if tw else 0
        out.append({'i': i, 'bar': x, 'd': ds.isoformat(), 'T': close_time(kind, ds), 'sc': sc, 'dir': 'up' if S >= .25 else 'down' if S <= -.25 else 'flat',
                    'pct': round(abs(S) * 100), 'atr': I['atr'][i], 'e50': I['e50'][i], 'rsi': I['rsi'][i]})
    return out, d

# ---------- portfolio replay ----------
fx = lambda kind: (1 / SAR) if kind == 'sa' else 1.0

def run(now):
    names = {a: (n, k) for a, n, k in ASSETS}
    events, last, errs = [], {}, []
    for aid, name, kind in ASSETS:
        try:
            sig, d = signals(aid, kind, now)
            if d: last[aid] = d[-1]['c']
            for s in sig: s['aid'] = aid; s['kind'] = kind; events.append(s)
        except FileNotFoundError:
            errs.append(f'{aid}: no data yet')
        except Exception as e:
            errs.append(f'{aid}: {str(e)[:100]}')
    events.sort(key=lambda e: (e['T'], e['aid']))
    cash, sweep_q, pos, closed, curve, n = START_USD, 0.0, {}, [], {}, 0
    px = {}
    spy0 = None
    def mark(aid): return px.get(aid)
    def equity():
        v = cash + sweep_q * (px.get(SWEEP) or 0)
        for a, p in pos.items():
            v += p['left'] * (px.get(a) or p['entry']) * fx(p['kind'])
        return v
    def raise_cash(need_usd):
        nonlocal cash, sweep_q
        sp = px.get(SWEEP)
        if need_usd <= cash or not sp or sweep_q <= 0: return
        q = min(sweep_q, (need_usd - cash) / (sp * (1 - SLIP)) * (1 + FEE['us']))
        val = q * sp * (1 - SLIP); cash += val - val * FEE['us']; sweep_q -= q
    groups = {}
    for e in events: groups.setdefault(e['T'], []).append(e)
    for T in sorted(groups):
        G = groups[T]
        for e in G: px[e['aid']] = e['bar']['c']
        if spy0 is None and px.get(SWEEP): spy0 = px[SWEEP]
        # exits first
        for e in G:
            a = e['aid']; p = pos.get(a)
            if not p or p['opened_T'] >= T: continue
            x = e['bar']; ds = e['d']; f = FEE[e['kind']]
            def fill(q, price, why):
                nonlocal cash
                price = price * (1 - SLIP); val = q * price; fee = val * f
                cash += (val - fee) * fx(p['kind']); p['fees'] += fee; p['left'] -= q
                p['exits'].append({'d': ds, 'price': round(price, 6), 'qty': q, 'why': why})
            o, h, l, c = x['o'], x['h'], x['l'], x['c']
            if not p['t1_hit']:
                if l <= p['stop']: fill(p['left'], min(o, p['stop']), 'وقف الخسارة')
                elif h >= p['t1']:
                    fill(p['q1'], max(o, p['t1']), 'الهدف الأول'); p['t1_hit'] = True; p['stop'] = p['entry']
                    if h >= p['t2'] and p['left'] > 1e-12: fill(p['left'], max(o, p['t2']), 'الهدف الثاني')
            else:
                if l <= p['stop']: fill(p['left'], min(o, p['stop']), 'وقف عند سعر الدخول')
                elif h >= p['t2']: fill(p['left'], max(o, p['t2']), 'الهدف الثاني')
            p['bars'] += 1
            if p['left'] > 1e-12:
                if e['dir'] == 'down' and e['pct'] >= 40: fill(p['left'], c, 'انعكاس التوافق')
                elif p['bars'] >= MAX_HOLD: fill(p['left'], c, 'انتهاء مدة الصفقة')
            if p['left'] <= 1e-12:
                got = sum(z['qty'] * z['price'] for z in p['exits'])
                p['pnl'] = round(got - p['qty'] * p['entry'] - p['fees'], 4); p['pnl_usd'] = round(p['pnl'] * fx(p['kind']), 2)
                p['pnl_pct'] = round(p['pnl'] / (p['qty'] * p['entry']) * 100, 2); p['status'] = 'closed'; p['closed'] = ds
                for k in ('opened_T', 'left', 'bars'): p.pop(k, None)
                closed.append(p); del pos[a]
        # entries, strongest confluence first
        cands = [e for e in G if e['aid'] != SWEEP and e['aid'] not in pos and e['atr'] and e['sc']['D'] and e['dir'] == 'up' and e['pct'] >= 50
                 and e['sc']['D']['s'] >= .35 and e['e50'] and e['bar']['c'] > e['e50'] and e['rsi'] is not None and e['rsi'] < 75
                 and not any(z['asset'] == e['aid'] and z['closed'] == e['d'] for z in closed[-20:])]
        cands.sort(key=lambda e: (-e['pct'], -e['sc']['D']['s'], e['aid']))
        for e in cands:
            if len(pos) >= MAX_OPEN: break
            a, kind, x, atrv = e['aid'], e['kind'], e['bar'], e['atr']
            f = FEE[kind]; entry = x['c'] * (1 + SLIP); stop = entry - 1.5 * atrv
            eq = equity(); k = fx(kind)
            qty = RISK * eq / ((entry - stop) * k)
            qty = min(qty, MAX_W * eq / (entry * k))
            raise_cash(qty * entry * k * (1 + f))
            qty = min(qty, max(0.0, cash - BUFFER * eq) / (entry * k * (1 + f)))
            qty = math.floor(qty) if kind == 'sa' else math.floor(qty * 1e6) / 1e6
            if qty * entry * k < 100 or (kind == 'sa' and qty < 2): continue
            q1 = qty // 2 if kind == 'sa' else qty / 2
            n += 1; fee = qty * entry * f; cash -= (qty * entry + fee) * k
            sc = e['sc']
            why = f"توافق صاعد {e['pct']}% (" + '، '.join(f"{TFN[z]} {DIRN[sc[z]['dir']]}" for z in ('M', 'W', 'D') if sc[z]) + f")، السعر فوق متوسط 50 يومًا، RSI {e['rsi']:.0f}"
            pos[a] = {'id': f'P-{n}', 'asset': a, 'name': names[a][0], 'kind': kind, 'cur': 'ريال' if kind == 'sa' else 'دولار', 'opened': e['d'], 'opened_T': T,
                      'entry': round(entry, 6), 'qty': qty, 'value': round(qty * entry, 2), 'value_usd': round(qty * entry * k, 2), 'weight': round(qty * entry * k / eq * 100, 1),
                      'stop0': round(stop, 6), 'stop': stop, 't1': round(entry + 1.5 * atrv, 6), 't2': round(entry + 3 * atrv, 6), 'q1': q1, 'q2': qty - q1,
                      'atr': round(atrv, 6), 'conf': e['pct'], 'tf': {z: sc[z]['dir'] for z in sc if sc[z]}, 'why': why, 't1_hit': False, 'left': qty, 'bars': 0,
                      'exits': [], 'fees': fee, 'status': 'open'}
        # sweep idle cash into the index at its close
        if any(e['aid'] == SWEEP for e in G) and px.get(SWEEP):
            eq = equity(); idle = cash - BUFFER * eq
            if idle > 50:
                sp = px[SWEEP] * (1 + SLIP); q = idle / (sp * (1 + FEE['us'])); sweep_q += q; cash -= q * sp * (1 + FEE['us'])
        curve[max(e['d'] for e in G)] = round(equity(), 2)
    # final marks with the latest known prices
    for a, v in last.items(): px[a] = v
    eq = equity()
    opens = []
    for a, p in pos.items():
        o = dict(p); now_p = px.get(a, p['entry']); k = fx(p['kind'])
        done = sum(z['qty'] * z['price'] for z in o['exits']); done_q = sum(z['qty'] for z in o['exits'])
        o['upnl'] = round(o['left'] * (now_p - o['entry']) + done - done_q * o['entry'] - o['fees'], 4); o['upnl_usd'] = round(o['upnl'] * k, 2)
        o['now'] = now_p; o['now_usd'] = round(o['left'] * now_p * k, 2); o['stop'] = round(o['stop'], 6); o['fees'] = round(o['fees'], 4)
        for k2 in ('opened_T', 'bars'): o.pop(k2, None)
        opens.append(o)
    for t in closed: t['fees'] = round(t['fees'], 4); t['stop'] = round(t['stop'], 6)
    sweep_usd = sweep_q * (px.get(SWEEP) or 0); inv = sum(o['now_usd'] for o in opens)
    alloc = sorted([{'label': o['name'], 'usd': o['now_usd']} for o in opens], key=lambda z: -z['usd'])
    alloc += [{'label': 'صندوق المؤشر SPY', 'usd': round(sweep_usd, 2), 'sweep': True}, {'label': 'نقد', 'usd': round(cash, 2), 'cash': True}]
    for z in alloc: z['pct'] = round(z['usd'] / eq * 100, 1) if eq else 0
    stats = {}
    for t in closed:
        s = stats.setdefault(t['asset'], {'id': t['asset'], 'name': t['name'], 'kind': t['kind'], 'n': 0, 'wins': 0, 'pnl_usd': 0.0})
        s['n'] += 1; s['wins'] += t['pnl'] > 0; s['pnl_usd'] = round(s['pnl_usd'] + t['pnl_usd'], 2)
    wins = sum(1 for t in closed if t['pnl'] > 0)
    spy_now = px.get(SWEEP)
    return {
        'totals': {'start_usd': START_USD, 'equity_usd': round(eq, 2), 'pnl_usd': round(eq - START_USD, 2), 'pct': round((eq / START_USD - 1) * 100, 3),
                   'open_n': len(opens), 'closed_n': len(closed), 'win_rate': round(wins / len(closed) * 100, 1) if closed else None,
                   'cash_usd': round(cash, 2), 'sweep_usd': round(sweep_usd, 2), 'invested_usd': round(inv, 2),
                   'util': round((inv + sweep_usd) / eq * 100, 1) if eq else 0,
                   'bench_pct': round((spy_now / spy0 - 1) * 100, 3) if spy0 and spy_now else None},
        'open': sorted(opens, key=lambda o: o['opened'], reverse=True), 'closed': sorted(closed, key=lambda t: t['closed'], reverse=True),
        'curve': sorted(curve.items()), 'alloc': alloc, 'stats': sorted(stats.values(), key=lambda s: -s['pnl_usd']),
        'universe': len(ASSETS), 'errors': errs}

# ---------- encryption ----------
def encrypt(obj):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    kj = json.load(open(os.path.join(ROOT, 'vault', 'key.json')))
    pub = serialization.load_der_public_key(base64.b64decode(kj['pub']))
    k = os.urandom(32); iv = os.urandom(12)
    ct = AESGCM(k).encrypt(iv, json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode(), None)
    wk = pub.encrypt(k, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    b = lambda x: base64.b64encode(x).decode()
    return {'v': 1, 'wk': b(wk), 'iv': b(iv), 'ct': b(ct)}

def main():
    now = dt.datetime.now(dt.timezone.utc)
    r = run(now)
    book = {'updated': now.strftime('%Y-%m-%dT%H:%MZ'), 'launch': LAUNCH, 'mode': 'portfolio',
            'rules': {'risk': RISK, 'max_w': MAX_W, 'max_open': MAX_OPEN, 'stop_atr': 1.5, 't1_atr': 1.5, 't2_atr': 3, 'max_hold': MAX_HOLD,
                      'fees': FEE, 'slip': SLIP, 'sweep': SWEEP}, **r}
    os.makedirs(os.path.join(ROOT, 'vault'), exist_ok=True)
    json.dump(encrypt(book), open(os.path.join(ROOT, 'vault', 'book.json'), 'w'), separators=(',', ':'))
    T = r['totals']
    print(f"universe={r['universe']} open={T['open_n']} closed={T['closed_n']} equity={T['equity_usd']} util={T['util']}% bench={T['bench_pct']} errors={len(r['errors'])}")
    if os.environ.get('PAPER_DEBUG'):
        json.dump(book, open(os.environ['PAPER_DEBUG'], 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
