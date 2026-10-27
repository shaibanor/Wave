#!/usr/bin/env python3
"""Paper-trading book. Replays deterministic rules from LAUNCH on stored market data
and writes the result encrypted to vault/book.json (RSA-OAEP wrapped AES-256-GCM)."""
import json, os, math, base64, datetime as dt
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
LAUNCH = os.environ.get('PAPER_LAUNCH', '2026-10-27')
START_USD = 3000.0
SAR = 3.75
FEE = {'sa': 0.0015, 'us': 0.0005, 'cx': 0.001}
SLIP = 0.0005
RISK = 0.02
MAX_HOLD = 30
ASSETS = [
    ('8311', 'عناية', 'sa'), ('1120', 'مصرف الراجحي', 'sa'), ('4340', 'الراجحي ريت', 'sa'), ('2222', 'أرامكو السعودية', 'sa'),
    ('1211', 'معادن', 'sa'), ('1180', 'البنك الأهلي السعودي', 'sa'), ('7010', 'إس تي سي', 'sa'), ('2010', 'سابك', 'sa'),
    ('2082', 'أكوا باور', 'sa'), ('4013', 'سليمان الحبيب', 'sa'), ('1010', 'بنك الرياض', 'sa'), ('1150', 'مصرف الإنماء', 'sa'),
    ('BTC', 'بيتكوين', 'cx'), ('ETH', 'إيثيريوم', 'cx'), ('XRP', 'ريبل', 'cx'), ('BNB', 'بي إن بي', 'cx'), ('SOL', 'سولانا', 'cx'),
    ('TRX', 'ترون', 'cx'), ('DOGE', 'دوجكوين', 'cx'), ('ZEC', 'زي كاش', 'cx'), ('LINK', 'تشين لينك', 'cx'), ('ADA', 'كاردانو', 'cx'),
    ('GOOGL', 'ألفابت (جوجل)', 'us'), ('META', 'ميتا', 'us'), ('AVGO', 'برودكوم', 'us'), ('TSM', 'TSMC', 'us'),
    ('JPM', 'جي بي مورغان', 'us'), ('LLY', 'إيلي ليلي', 'us'), ('V', 'فيزا', 'us'),
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

# ---------- replay ----------
def replay(aid, name, kind, now):
    d, m = load(aid, kind)
    d = [x for x in d if complete(kind, day(x['t']), now)]
    I = ind(d)
    cur = 'ريال' if kind == 'sa' else 'دولار'
    cap = START_USD * (SAR if kind == 'sa' else 1)
    cash, pos, trades, curve, n = cap, None, [], [], 0
    start_i = next((i for i, x in enumerate(d) if day(x['t']).isoformat() >= LAUNCH), None)
    if start_i is None:
        last = d[-1]
        return {'id': aid, 'name': name, 'kind': kind, 'cur': cur, 'start': round(cap, 2), 'cash': round(cap, 2), 'equity': round(cap, 2),
                'equity_usd': START_USD, 'pnl': 0.0, 'pnl_pct': 0.0, 'closed_n': 0, 'wins': 0, 'open': None, 'trades': [],
                'last': {'d': day(last['t']).isoformat(), 'c': last['c']}, 'curve': []}
    fee = FEE[kind]
    frac = kind != 'sa'
    for i in range(start_i, len(d)):
        x, ds = d[i], day(d[i]['t']).isoformat()
        # --- confluence at close i (causal) ---
        Dsc = score(d, I, i)
        wk = agg(d[:i + 1], lambda q: week_key(q, kind)); WI = ind(wk); Wsc = score(wk, WI, len(wk) - 1)
        mon = [y for y in m if (day(y['t']).year, day(y['t']).month) < (day(x['t']).year, day(x['t']).month)]
        mcur = agg([y for y in d[:i + 1] if (day(y['t']).year, day(y['t']).month) == (day(x['t']).year, day(x['t']).month)], lambda q: (q.year, q.month))
        mb = mon + mcur; MI = ind(mb); Msc = score(mb, MI, len(mb) - 1)
        sc = {'M': Msc, 'W': Wsc, 'D': Dsc}
        tw = sum(W[k] for k in sc if sc[k]); S = sum(W[k] * sc[k]['s'] for k in sc if sc[k]) / tw if tw else 0
        cdir = 'up' if S >= .25 else 'down' if S <= -.25 else 'flat'; cpct = round(abs(S) * 100)
        # --- manage open position on bar i ---
        if pos and pos['opened_i'] < i:
            def fill(q, price, why):
                nonlocal cash
                price = price * (1 - SLIP); val = q * price; f = val * fee
                cash += val - f; pos['fees'] += f; pos['left'] -= q
                pos['exits'].append({'d': ds, 'price': round(price, 6), 'qty': q, 'why': why})
            o, h, l, c = x['o'], x['h'], x['l'], x['c']
            if not pos['t1_hit']:
                if l <= pos['stop']:
                    fill(pos['left'], min(o, pos['stop']), 'وقف الخسارة')
                elif h >= pos['t1']:
                    fill(pos['q1'], max(o, pos['t1']), 'الهدف الأول'); pos['t1_hit'] = True; pos['stop'] = pos['entry']
                    if h >= pos['t2'] and pos['left'] > 0: fill(pos['left'], max(o, pos['t2']), 'الهدف الثاني')
            else:
                if l <= pos['stop']: fill(pos['left'], min(o, pos['stop']), 'وقف عند سعر الدخول')
                elif h >= pos['t2']: fill(pos['left'], max(o, pos['t2']), 'الهدف الثاني')
            if pos['left'] > 1e-12:
                if cdir == 'down' and cpct >= 40: fill(pos['left'], c, 'انعكاس التوافق')
                elif i - pos['opened_i'] >= MAX_HOLD: fill(pos['left'], c, 'انتهاء مدة الصفقة')
            if pos['left'] <= 1e-12:
                got = sum(e['qty'] * e['price'] for e in pos['exits'])
                pos['pnl'] = round(got - pos['qty'] * pos['entry'] - pos['fees'], 4)
                pos['pnl_pct'] = round(pos['pnl'] / (pos['qty'] * pos['entry']) * 100, 2)
                pos['status'] = 'closed'; pos['closed'] = ds; pos.pop('opened_i', None); pos.pop('left', None)
                trades.append(pos); pos = None
        # --- entry at close i ---
        if pos is None and (not trades or trades[-1].get('closed') != ds):
            a = I['atr'][i]; e50 = I['e50'][i]; r = I['rsi'][i]
            if a and Dsc and cdir == 'up' and cpct >= 50 and Dsc['s'] >= .35 and e50 and x['c'] > e50 and r is not None and r < 75:
                entry = x['c'] * (1 + SLIP); stop = entry - 1.5 * a
                equity = cash
                qty = RISK * equity / (entry - stop)
                qty = min(qty, cash * .95 / (entry * (1 + fee)))
                if not frac: qty = math.floor(qty)
                else: qty = math.floor(qty * 1e6) / 1e6
                if qty * entry >= 50 and (frac or qty >= 2):
                    q1 = qty / 2 if frac else qty // 2
                    n += 1; f = qty * entry * fee; cash -= qty * entry + f
                    why = f"توافق صاعد {cpct}% (" + '، '.join(f"{TFN[k]} {DIRN[sc[k]['dir']]}" for k in ('M', 'W', 'D') if sc[k]) + f")، السعر فوق متوسط 50 يومًا، RSI {r:.0f}"
                    pos = {'id': f'{aid}-{n}', 'asset': aid, 'name': name, 'kind': kind, 'cur': cur, 'opened': ds, 'opened_i': i,
                           'entry': round(entry, 6), 'qty': qty, 'value': round(qty * entry, 2), 'stop0': round(stop, 6), 'stop': stop,
                           't1': round(entry + 1.5 * a, 6), 't2': round(entry + 3 * a, 6), 'q1': q1, 'q2': qty - q1, 'atr': round(a, 6),
                           'conf': cpct, 'tf': {k: sc[k]['dir'] for k in sc if sc[k]}, 'why': why, 't1_hit': False, 'left': qty,
                           'exits': [], 'fees': f, 'status': 'open'}
        held = pos['left'] * x['c'] if pos else 0
        curve.append([ds, round(cash + held, 2)])
    last = d[-1]
    eq = curve[-1][1] if curve else cap
    if pos:
        o = dict(pos); o['stop'] = round(o['stop'], 6); o['now'] = last['c']; o['now_d'] = day(last['t']).isoformat()
        o['upnl'] = round(o['left'] * last['c'] - o['left'] * o['entry'] + sum(e['qty'] * e['price'] for e in o['exits']) - sum(e['qty'] for e in o['exits']) * o['entry'] - o['fees'], 4)
        o.pop('opened_i', None); o['fees'] = round(o['fees'], 4); open_t = o
    else:
        open_t = None
    for t in trades: t['fees'] = round(t['fees'], 4); t['stop'] = round(t['stop'], 6)
    wins = sum(1 for t in trades if t['pnl'] > 0)
    usd = (lambda v: v / SAR) if kind == 'sa' else (lambda v: v)
    return {'id': aid, 'name': name, 'kind': kind, 'cur': cur, 'start': round(cap, 2), 'cash': round(cash, 2), 'equity': eq,
            'equity_usd': round(usd(eq), 2), 'pnl': round(eq - cap, 2), 'pnl_pct': round((eq / cap - 1) * 100, 2),
            'closed_n': len(trades), 'wins': wins, 'open': open_t, 'trades': trades, 'last': {'d': day(last['t']).isoformat(), 'c': last['c']},
            'curve': curve}

def total_curve(accts):
    dates = sorted({c[0] for a in accts for c in a['curve']})
    out = []
    for dte in dates:
        tot = 0
        for a in accts:
            v = START_USD
            for c in a['curve']:
                if c[0] <= dte: v = c[1] / (SAR if a['kind'] == 'sa' else 1)
                else: break
            tot += v
        out.append([dte, round(tot, 2)])
    return out

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
    accts, errs = [], []
    for aid, name, kind in ASSETS:
        try:
            r = replay(aid, name, kind, now)
            if r: accts.append(r)
        except Exception as e:
            errs.append(f'{aid}: {str(e)[:120]}')
    trades = [t for a in accts for t in a['trades']]
    opens = [a['open'] for a in accts if a['open']]
    eq = sum(a['equity_usd'] for a in accts); start = START_USD * len(accts)
    wins = sum(a['wins'] for a in accts)
    book = {'updated': now.strftime('%Y-%m-%dT%H:%MZ'), 'launch': LAUNCH, 'per_asset_usd': START_USD,
            'rules': {'risk': RISK, 'stop_atr': 1.5, 't1_atr': 1.5, 't2_atr': 3, 'max_hold': MAX_HOLD, 'fees': FEE, 'slip': SLIP},
            'totals': {'start_usd': start, 'equity_usd': round(eq, 2), 'pnl_usd': round(eq - start, 2), 'pct': round((eq / start - 1) * 100, 3) if start else 0,
                       'open_n': len(opens), 'closed_n': len(trades), 'win_rate': round(wins / len(trades) * 100, 1) if trades else None},
            'accounts': [{k: v for k, v in a.items() if k != 'trades'} for a in accts], 'open': opens,
            'closed': sorted(trades, key=lambda t: t['closed'], reverse=True), 'curve': total_curve(accts), 'errors': errs}
    os.makedirs(os.path.join(ROOT, 'vault'), exist_ok=True)
    json.dump(encrypt(book), open(os.path.join(ROOT, 'vault', 'book.json'), 'w'), separators=(',', ':'))
    print(f"accounts={len(accts)} open={len(opens)} closed={len(trades)} equity={eq:.2f} errors={len(errs)}")
    if os.environ.get('PAPER_DEBUG'):
        json.dump(book, open(os.environ['PAPER_DEBUG'], 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
