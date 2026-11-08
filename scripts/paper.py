#!/usr/bin/env python3
"""Paper portfolio v2 ("Tiko Professor"). Rules live in pro/rules.json.

Top-down: monthly -> weekly -> daily -> 4h. A trade is opened only when the final audit passes:
  1) monthly reviewed and not against the monthly trend
  2) support / resistance mapped, with room before the first resistance
  3) traps filtered (failed breakout with an upper wick, scheduled event blackout); news is never a trigger
  4) reward-to-risk >= rules.auditor.min_rr
Horizons: H4 (crypto and Saudi stocks that have 4h data), D, W (decided on the week's close), M (on the month's close).
Exits: stop, single target at the highest strong resistance within reach, breakeven after +1R, trend reversal on the
horizon's parent timeframe, time limit. Cycle: when realized net profit of the cycle reaches target_pct of the cycle's
starting capital, everything is closed and the portfolio is frozen for freeze_days, then a new cycle starts.
The book is written encrypted to vault/book.json."""
import json, os, sys, math, base64, datetime as dt
sys.dont_write_bytecode = True
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
R = json.load(open(os.path.join(ROOT, 'pro', 'rules.json'), encoding='utf-8'))
def _merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict): _merge(a[k], v)
        else: a[k] = v
if os.environ.get('RULES_OVERRIDE'): _merge(R, json.loads(os.environ['RULES_OVERRIDE']))
try:
    EVENTS = json.load(open(os.path.join(ROOT, 'pro', 'events.json'), encoding='utf-8'))['events']
except Exception:
    EVENTS = []
LAUNCH = os.environ.get('PAPER2_LAUNCH', '2026-11-09')
V1_END = dt.datetime(2026, 11, 8, 21, 0, tzinfo=dt.timezone.utc)  # the first version's record is frozen here
START_USD = 87000.0
SAR = 3.75
EX = R['execution']; FEE = EX['fees']; SLIP = EX['slip']; SWEEP = EX['sweep']
RK = R['risk']; HZ = R['horizons']; LV = R['levels']; TR = R['traps']; AU = R['auditor']; CY = R['cycle']; EF = R['entry_filters']
WGT = R['weights']
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
TFN = {'M': 'الشهري', 'W': 'الأسبوعي', 'D': 'اليومي', 'H4': '4 ساعات'}
DIRN = {'up': 'صاعد', 'down': 'هابط', 'flat': 'محايد'}

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

def ind(b):
    c = [x['c'] for x in b]
    return {'e50': ema(c, 50), 'e200': ema(c, 200), 'rsi': rsi(c), 'hist': macd_hist(c), 'atr': atr(b)}

def swings(b, k=3, lo=0, upto=None):
    """Confirmed swing highs/lows in b[lo..upto] (a swing needs k bars on each side, all at or before upto)."""
    H, L = [], []
    last = len(b) - 1 if upto is None else upto
    for i in range(max(k, lo), last - k + 1):
        hi = all(b[i - j]['h'] < b[i]['h'] and b[i + j]['h'] <= b[i]['h'] for j in range(1, k + 1))
        lw = all(b[i - j]['l'] > b[i]['l'] and b[i + j]['l'] >= b[i]['l'] for j in range(1, k + 1))
        if hi: H.append(i)
        if lw: L.append(i)
    return H, L

def structure(b, H, L):
    H, L = H[-2:], L[-2:]
    if len(H) < 2 or len(L) < 2: return 0
    hh, hl = b[H[1]]['h'] > b[H[0]]['h'], b[L[1]]['l'] > b[L[0]]['l']
    return 1 if hh and hl else -1 if (not hh and not hl) else 0

def score(b, I, i, H=None, L=None):
    if i < 30: return None
    c = b[i]['c']; P = []
    if I['e50'][i] is not None: P.append(1 if c > I['e50'][i] else -1)
    if I['e200'][i] is not None and I['e50'][i] is not None: P.append(1 if I['e50'][i] > I['e200'][i] else -1)
    if H is None: H, L = swings(b, lo=max(0, i - 120), upto=i)
    P.append(structure(b, H, L))
    if I['hist'][i] is not None: P.append(1 if I['hist'][i] > 0 else -1)
    if I['rsi'][i] is not None: P.append(1 if I['rsi'][i] > 55 else -1 if I['rsi'][i] < 45 else 0)
    s = sum(P) / len(P)
    return {'s': round(s, 3), 'dir': 'up' if s >= .35 else 'down' if s <= -.35 else 'flat'}

# ---------- data ----------
def bars(rows):
    return [{'t': int(r[0]), 'o': float(r[1]), 'h': float(r[2]), 'l': float(r[3]), 'c': float(r[4])} for r in rows if r[4] and r[4] > 0]

def day(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
TZ = {'sa': ZoneInfo('Asia/Riyadh'), 'us': ZoneInfo('America/New_York'), 'cx': dt.timezone.utc}

def close_time(kind, d):
    if kind == 'cx':
        return dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc) + dt.timedelta(days=1)
    return dt.datetime(d.year, d.month, d.day, 15, 30, tzinfo=TZ['sa']) if kind == 'sa' else dt.datetime(d.year, d.month, d.day, 16, 20, tzinfo=TZ['us'])

def mday(d, kind):
    return True if kind == 'cx' else (d.weekday() in (6, 0, 1, 2, 3) if kind == 'sa' else d.weekday() < 5)

def next_mday(d, kind):
    n = d + dt.timedelta(days=1)
    while not mday(n, kind): n += dt.timedelta(days=1)
    return n

def week_key(d, kind):
    wd = d.weekday()
    return d - dt.timedelta(days=(wd + 1) % 7 if kind == 'sa' else wd)

def load(aid, kind):
    j = json.load(open(os.path.join(ROOT, 'pro', kind, f'{aid}.json')))
    if kind == 'cx':
        d = bars(j['1d']); m = bars(j.get('1M', [])); h4 = bars(j.get('4h', []))
        for x in d: x['t'] = int(dt.datetime.combine(day(x['t']), dt.time(), dt.timezone.utc).timestamp())
    else:
        d = bars(j['d']); m = bars(j.get('m', [])); h4 = bars(j.get('4h', [])) if kind == 'sa' else []
    return d, m, h4

def h4_close(kind, t):
    s = dt.datetime.fromtimestamp(t, dt.timezone.utc)
    e = s + dt.timedelta(hours=4)
    if kind == 'sa':
        dl = s.astimezone(TZ['sa']).date()
        e = min(e, dt.datetime(dl.year, dl.month, dl.day, 15, 0, tzinfo=TZ['sa']))
    return e

def local_date(kind, t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).astimezone(TZ[kind]).date()

def event_block(kind, ds):
    """Scheduled high-impact event today or tomorrow -> no new short-horizon entries."""
    for e in EVENTS:
        if e.get('scope') not in ('all', kind): continue
        ed = dt.date.fromisoformat(e['d'])
        if 0 <= (ed - ds).days <= 1: return e['t'] + ' ' + e['d']
    return None

# ---------- per-asset preparation (causal) ----------
def prepare(aid, kind, now, launch):
    d, mN, h4 = load(aid, kind)
    d = [x for x in d if now >= close_time(kind, day(x['t']))]
    if len(d) < 60: return None
    I = ind(d)
    k = LV['swing_k']
    first_month = (day(d[0]['t']).year, day(d[0]['t']).month)
    native = [x for x in mN if (day(x['t']).year, day(x['t']).month) < first_month]
    wk, mo = [], list(native)
    ctx = {}
    for i, x in enumerate(d):
        ds = day(x['t'])
        # weekly bars up to and including today
        kw = week_key(ds, kind)
        if wk and wk[-1]['k'] == kw:
            w = wk[-1]; w['h'] = max(w['h'], x['h']); w['l'] = min(w['l'], x['l']); w['c'] = x['c']
        else:
            wk.append({'k': kw, 't': x['t'], 'o': x['o'], 'h': x['h'], 'l': x['l'], 'c': x['c']})
        km = (ds.year, ds.month)
        if mo and mo[-1].get('k') == km:
            m_ = mo[-1]; m_['h'] = max(m_['h'], x['h']); m_['l'] = min(m_['l'], x['l']); m_['c'] = x['c']
        else:
            mo.append({'k': km, 't': x['t'], 'o': x['o'], 'h': x['h'], 'l': x['l'], 'c': x['c']})
        if ds.isoformat() < launch: continue
        nx = day(d[i + 1]['t']) if i + 1 < len(d) else next_mday(ds, kind)
        IW, IM = ind(wk), ind(mo)
        HD, LD = swings(d, k, max(0, i - LV['lookback']['D']), i)
        HW, LW_ = swings(wk, k, max(0, len(wk) - 1 - LV['lookback']['W']), len(wk) - 1)
        HM, LM = swings(mo, 2, max(0, len(mo) - 1 - LV['lookback']['M']), len(mo) - 1)
        ctx[i] = {
            'd': ds.isoformat(), 'date': ds, 'bar': x,
            'sc': {'D': score(d, I, i, HD, LD), 'W': score(wk, IW, len(wk) - 1, HW, LW_), 'M': score(mo, IM, len(mo) - 1, HM, LM)},
            'atr': {'D': I['atr'][i], 'W': IW['atr'][-1], 'M': IM['atr'][-1]},
            'e50': {'D': I['e50'][i], 'W': IW['e50'][-1], 'M': IM['e50'][-1]},
            'rsi': {'D': I['rsi'][i], 'W': IW['rsi'][-1], 'M': IM['rsi'][-1]},
            'res': {'D': [d[j]['h'] for j in HD], 'W': [wk[j]['h'] for j in HW], 'M': [mo[j]['h'] for j in HM]},
            'sup': {'D': [d[j]['l'] for j in LD], 'W': [wk[j]['l'] for j in LW_], 'M': [mo[j]['l'] for j in LM]},
            'exec': {'D': x, 'W': wk[-1], 'M': mo[-1]},
            'prevH': {'D': [d[j]['h'] for j in HD if j < i], 'W': [wk[j]['h'] for j in HW if j < len(wk) - 1], 'M': [mo[j]['h'] for j in HM if j < len(mo) - 1]},
            'prevL': {'D': [d[j]['l'] for j in LD if j < i], 'W': [wk[j]['l'] for j in LW_ if j < len(wk) - 1], 'M': [mo[j]['l'] for j in LM if j < len(mo) - 1]},
            'week_end': week_key(nx, kind) != kw, 'month_end': (nx.year, nx.month) != km,
            'ath': max(z['h'] for z in mo),
        }
    # 4h bars (complete only), with their own causal score and levels
    H4 = []
    if h4:
        h4 = [x for x in h4 if now >= h4_close(kind, x['t'])]
        if len(h4) > 60:
            IH = ind(h4)
            for j, x in enumerate(h4):
                T = h4_close(kind, x['t'])
                ld = local_date(kind, x['t']) if kind == 'sa' else day(x['t'])
                if ld.isoformat() < launch: continue
                HH, LL = swings(h4, k, max(0, j - LV['lookback']['H4']), j)
                H4.append({'T': T, 'date': ld, 'bar': x, 'sc': score(h4, IH, j, HH, LL), 'atr': IH['atr'][j], 'e50': IH['e50'][j], 'rsi': IH['rsi'][j],
                           'res': [h4[q]['h'] for q in HH], 'sup': [h4[q]['l'] for q in LL],
                           'prevH': [h4[q]['h'] for q in HH if q < j], 'prevL': [h4[q]['l'] for q in LL if q < j]})
    return {'d': d, 'ctx': ctx, 'h4': H4}

# ---------- the audit ----------
def plan(h, entry, atrv, sup, res_all, bar, prevH, prevL, sc, kind, ds):
    """Returns (ok, details). details has stop, target, rr, checks and notes."""
    hz = HZ[h]; checks = {}; notes = []
    # 1) monthly reviewed, never against it; weekly veto for short horizons
    m = sc.get('M')
    checks['monthly'] = bool(m) and not (R['monthly_veto'] and m['dir'] == 'down')
    if h in R['weekly_veto_for'] and sc.get('W') and sc['W']['dir'] == 'down': checks['monthly'] = False; notes.append('الأسبوعي هابط')
    if not m: notes.append('لا يوجد شهري كافٍ')
    elif m['dir'] == 'down': notes.append('الشهري هابط')
    # 2) levels: stop below the nearest real support, room before the first resistance
    below = sorted([s for s in sup if s < entry - 0.3 * atrv], reverse=True)
    support = below[0] if below else None
    stop = support - LV['stop_buffer_atr'] * atrv if support else entry - hz['stop_atr'] * atrv
    risk = entry - stop
    if risk < hz['min_risk_atr'] * atrv: stop = entry - hz['stop_atr'] * atrv; risk = entry - stop
    above = sorted([r for r in res_all if r > entry * 1.0005])
    r1 = above[0] if above else None
    cap = entry + hz['target_cap_atr'] * atrv
    within = [r for r in above if r <= cap]
    target = (max(within) - LV['target_below_res_atr'] * atrv) if within else cap
    if target <= entry: target = cap
    room_ok = r1 is None or (r1 - entry) >= LV['min_room_r'] * risk
    risk_ok = risk <= hz['max_risk_atr'] * atrv
    checks['levels'] = room_ok and risk_ok
    if not room_ok: notes.append('مقاومة قريبة جدًا فوق الدخول')
    if not risk_ok: notes.append('الدعم بعيد والوقف واسع')
    # 3) traps: failed breakout (wick above a prior swing high, close back below), scheduled event
    rng = max(1e-12, bar['h'] - bar['l']); uw = (bar['h'] - max(bar['o'], bar['c'])) / rng
    trap = any(bar['h'] > p and bar['c'] < p for p in prevH[-6:]) and uw >= TR['failed_breakout_wick']
    ev = event_block(kind, ds) if h in ('H4', 'D') else None
    checks['traps'] = not trap and not ev
    if trap: notes.append('اختراق كاذب بذيل علوي (فخ سيولة)')
    if ev: notes.append('حدث كبير قريب: ' + ev)
    sweep = any(bar['l'] < p and bar['c'] > p for p in prevL[-6:])
    if sweep: notes.append('سحب سيولة تحت قاع سابق ثم عودة')
    # 4) reward to risk
    rr = (target - entry) / risk if risk > 0 else 0
    checks['rr'] = rr >= AU['min_rr']
    if not checks['rr']: notes.append(f'العائد إلى المخاطرة {rr:.2f} أقل من {AU["min_rr"]}')
    return all(checks.values()), {'stop': stop, 'target': target, 'rr': rr, 'risk': risk, 'support': support, 'r1': r1,
                                  'checks': checks, 'notes': notes, 'sweep': sweep}

def confluence(sc, tfs):
    tw = sum(WGT[t] for t in tfs if sc.get(t));
    if not tw: return 0, 'flat'
    S = sum(WGT[t] * sc[t]['s'] for t in tfs if sc.get(t)) / tw
    return S, ('up' if S >= .25 else 'down' if S <= -.25 else 'flat')

# ---------- replay ----------
fx = lambda kind: (1 / SAR) if kind == 'sa' else 1.0

def run(now, launch=LAUNCH):
    names = {a: (n, k) for a, n, k in ASSETS}
    ticks, last, errs, prep = [], {}, [], {}
    for aid, name, kind in ASSETS:
        try:
            P = prepare(aid, kind, now, launch)
        except FileNotFoundError:
            errs.append(f'{aid}: no data yet'); continue
        except Exception as e:
            errs.append(f'{aid}: {str(e)[:100]}'); continue
        if not P: errs.append(f'{aid}: not enough data'); continue
        prep[aid] = P; last[aid] = P['d'][-1]['c']
        h4days = {z['date'] for z in P['h4']}
        for z in P['h4']: ticks.append((z['T'], 0, aid, kind, 'h4', z))
        for i, c in P['ctx'].items():
            ticks.append((close_time(kind, c['date']), 1, aid, kind, 'dsig' if c['date'] in h4days else 'day', c))
    ticks.sort(key=lambda e: (e[0], e[1], e[2]))
    cash, sweep_q = START_USD, 0.0
    pos, closed, curve, n = {}, [], {}, 0
    pw = [0.0]; sw_cost = [0.0]; px = {}; spy0 = None
    cyc = {'n': 1, 'start': None, 'cap0': START_USD, 'pnl': 0.0, 'frozen_until': None}; cycles = []
    rejects = {'monthly': 0, 'levels': 0, 'traps': 0, 'rr': 0}; audited = 0
    ctxD = {}

    def equity():
        v = cash + sweep_q * (px.get(SWEEP) or 0)
        for a, p in pos.items(): v += p['left'] * (px.get(a) or p['entry']) * fx(p['kind'])
        return v

    def raise_cash(need):
        nonlocal cash, sweep_q
        sp = px.get(SWEEP)
        if need <= cash or not sp or sweep_q <= 0: return
        q = min(sweep_q, (need - cash) / (sp * (1 - SLIP)) * (1 + FEE['us']))
        sw_cost[0] *= (1 - q / sweep_q)
        val = q * sp * (1 - SLIP); cash += val - val * FEE['us']; sweep_q -= q

    def finish(p, ds):
        nonlocal cash
        got = sum(z['qty'] * z['price'] for z in p['exits'])
        p['pnl'] = round(got - p['qty'] * p['entry'] - p['fees'], 4); p['pnl_usd'] = round(p['pnl'] * fx(p['kind']), 2)
        p['pnl_pct'] = round(p['pnl'] / (p['qty'] * p['entry']) * 100, 2); p['status'] = 'closed'; p['closed'] = ds
        p['exit'] = round(got / p['qty'], 6); p['win'] = p['pnl'] > 0
        p['r_mult'] = round((p['exit'] - p['entry']) / p['risk0'], 2) if p['risk0'] else None
        cyc['pnl'] += p['pnl_usd']
        if p['pnl_usd'] > 0: pw[0] += p['pnl_usd']; cash -= p['pnl_usd']
        for k in ('opened_T', 'left', 'risk0_px'): p.pop(k, None)
        closed.append(p)

    def fill(p, q, price, why, ds):
        nonlocal cash
        f = FEE[p['kind']]; price = price * (1 - SLIP); val = q * price; fee = val * f
        cash += (val - fee) * fx(p['kind']); p['fees'] += fee; p['left'] -= q
        p['exits'].append({'d': ds, 'price': round(price, 6), 'qty': q, 'why': why})

    def monitor(a, bar, ds, T):
        p = pos.get(a)
        if not p or p['opened_T'] >= T: return
        o, h, l = bar['o'], bar['h'], bar['l']
        if l <= p['stop']: fill(p, p['left'], min(o, p['stop']), 'وقف التعادل' if p['be'] else 'وقف الخسارة', ds)
        elif h >= p['target']: fill(p, p['left'], max(o, p['target']), 'تحقق الهدف', ds)
        elif not p['be'] and h >= p['entry'] + RK['breakeven_at_r'] * p['risk0']:
            p['stop'] = max(p['stop'], p['entry'] * (1 + 2 * FEE[p['kind']] + 2 * SLIP)); p['be'] = True
        if p['left'] <= 1e-12: finish(p, ds); del pos[a]

    def try_enter(a, kind, h, bar, entry_px, atrv, e50, rsi_, sc, sup, res, prevH, prevL, ds, T):
        nonlocal cash, n
        hz = HZ[h]
        if a == SWEEP or a in pos or not atrv or len(pos) >= RK['max_open']: return
        if not sc.get(h) or sc[h]['s'] < EF['exec_score_min']: return
        if EF['above_ema50'] and (not e50 or bar['c'] <= e50): return
        if rsi_ is None or rsi_ >= EF['rsi_max']: return
        S, dr = confluence(sc, [t for t in R['hierarchy'] if t in hz['context'] + [h]])
        if dr != 'up': return
        nonlocal_audit[0] += 1
        entry = entry_px * (1 + SLIP)
        ok, P = plan(h, entry, atrv, sup, res, bar, prevH, prevL, sc, kind, dt.date.fromisoformat(ds))
        conf = round(abs(S) * 100) + (TR['sweep_bonus'] if P['sweep'] else 0)
        if conf < hz['min_conf']: return
        if not ok:
            for k_, v in P['checks'].items():
                if not v: rejects[k_] += 1
            return
        eq = equity(); k = fx(kind); f = FEE[kind]
        qty = RK['risk_per_trade'] * eq / (P['risk'] * k)
        qty = min(qty, RK['max_weight'] * eq / (entry * k))
        raise_cash(qty * entry * k * (1 + f))
        qty = min(qty, max(0.0, cash) / (entry * k * (1 + f)))
        qty = math.floor(qty) if kind == 'sa' else math.floor(qty * 1e6) / 1e6
        if qty * entry * k < 100 or (kind == 'sa' and qty < 2): return
        n += 1; fee = qty * entry * f; cash -= (qty * entry + fee) * k
        tfs = [t for t in ('M', 'W', 'D', 'H4') if sc.get(t)]
        why = f"صفقة {hz['name']} · توافق {conf}% (" + '، '.join(f"{TFN[t]} {DIRN[sc[t]['dir']]}" for t in tfs) + ")"
        if P['support']: why += f" · الوقف تحت دعم {P['support']:.6g}"
        pos[a] = {'id': f'P-{n}', 'asset': a, 'name': names[a][0], 'kind': kind, 'h': h, 'hname': hz['name'], 'cur': 'ريال' if kind == 'sa' else 'دولار',
                  'opened': ds, 'opened_T': T, 'entry': round(entry, 6), 'qty': qty, 'value': round(qty * entry, 2), 'value_usd': round(qty * entry * k, 2),
                  'weight': round(qty * entry * k / eq * 100, 1), 'stop0': round(P['stop'], 6), 'stop': P['stop'], 'target': round(P['target'], 6),
                  'rr': round(P['rr'], 2), 'risk0': P['risk'], 'r1': round(P['r1'], 6) if P['r1'] else None, 'support': round(P['support'], 6) if P['support'] else None,
                  'atr': round(atrv, 6), 'conf': conf, 'tf': {t: sc[t]['dir'] for t in tfs}, 'audit': P['checks'], 'notes': P['notes'], 'why': why,
                  'left': qty, 'be': False, 'exits': [], 'fees': fee, 'status': 'open'}

    nonlocal_audit = [0]
    groups = {}
    for e in ticks: groups.setdefault(e[0], []).append(e)
    for T in sorted(groups):
        G = groups[T]
        ds_any = None
        for (_, _, a, kind, typ, z) in G:
            px[a] = z['bar']['c']; ds_any = z['date'].isoformat() if typ != 'h4' else z['date'].isoformat()
        if spy0 is None and px.get(SWEEP): spy0 = px[SWEEP]
        if cyc['start'] is None: cyc['start'] = ds_any
        frozen = cyc['frozen_until'] is not None and T < cyc['frozen_until']
        if cyc['frozen_until'] is not None and not frozen:
            cyc.update({'n': cyc['n'] + 1, 'start': ds_any, 'cap0': equity(), 'pnl': 0.0, 'frozen_until': None})
        # exits
        for (_, _, a, kind, typ, z) in G:
            ds = z['date'].isoformat()
            if typ in ('h4', 'day'): monitor(a, z['bar'], ds, T)
            if typ in ('day', 'dsig'):
                ctxD[a] = z
                p = pos.get(a)
                if p and p['opened_T'] < T:
                    hz = HZ[p['h']]; par = hz['exit_on']; s = z['sc'].get(par)
                    if s and s['dir'] == 'down' and (par != 'M' or z['month_end']):
                        fill(p, p['left'], z['bar']['c'], f"انعكاس الاتجاه {TFN[par]}", ds)
                    elif (z['date'] - dt.date.fromisoformat(p['opened'])).days >= hz['max_hold_days']:
                        fill(p, p['left'], z['bar']['c'], 'انتهاء مدة الصفقة', ds)
                    if p['left'] <= 1e-12: finish(p, ds); del pos[a]
        # entries
        if not frozen:
            cands = []
            for (_, _, a, kind, typ, z) in G:
                if typ == 'h4':
                    c = ctxD.get(a)
                    if not c: continue
                    sc = dict(c['sc']); sc['H4'] = z['sc']
                    cands.append((a, kind, 'H4', z['bar'], z['bar']['c'], z['atr'], z['e50'], z['rsi'], sc, z['sup'], z['res'] + c['res']['D'] + c['res']['W'] + c['res']['M'], z['prevH'], z['prevL'], z['date'].isoformat()))
                else:
                    for h in ('M', 'W', 'D'):
                        if h == 'W' and not z['week_end']: continue
                        if h == 'M' and not z['month_end']: continue
                        res = z['res'][h] + ([] if h == 'M' else z['res']['M']) + (z['res']['W'] if h == 'D' else [])
                        cands.append((a, kind, h, z['exec'][h], z['bar']['c'], z['atr'][h], z['e50'][h], z['rsi'][h], z['sc'], z['sup'][h], res, z['prevH'][h], z['prevL'][h], z['d']))
            order = {'M': 0, 'W': 1, 'D': 2, 'H4': 3}
            cands.sort(key=lambda c: (order[c[2]], -(c[8].get(c[2]) or {'s': 0})['s'], c[0]))
            for c in cands: try_enter(*c, T)
        # sweep idle cash into the index (not while frozen)
        if not frozen and any(e[2] == SWEEP and e[4] != 'h4' for e in G) and px.get(SWEEP):
            if cash > 1:
                sp = px[SWEEP] * (1 + SLIP); q = cash / (sp * (1 + FEE['us'])); sweep_q += q; cost = q * sp * (1 + FEE['us']); cash -= cost; sw_cost[0] += cost
        # cycle target: close everything, freeze
        if not frozen and cyc['cap0'] and cyc['pnl'] / cyc['cap0'] * 100 >= CY['target_pct']:
            ds = ds_any
            for a in list(pos):
                p = pos[a]; fill(p, p['left'], px.get(a, p['entry']), 'تحقق هدف الدورة', ds); finish(p, ds); del pos[a]
            if sweep_q > 0 and px.get(SWEEP):
                val = sweep_q * px[SWEEP] * (1 - SLIP); cash += val - val * FEE['us']; sweep_q = 0.0; sw_cost[0] = 0.0
            fz = T + dt.timedelta(days=CY['freeze_days'])
            cycles.append({'n': cyc['n'], 'start': cyc['start'], 'end': ds, 'cap0': round(cyc['cap0'], 2), 'pnl_usd': round(cyc['pnl'], 2),
                           'pct': round(cyc['pnl'] / cyc['cap0'] * 100, 2), 'frozen_until': fz.date().isoformat()})
            cyc['frozen_until'] = fz
        curve[ds_any] = round(equity() + pw[0], 2)
    # final marks
    for a, v in last.items(): px[a] = v
    eq = equity(); opens = []
    for a, p in pos.items():
        o = dict(p); now_p = px.get(a, p['entry']); k = fx(p['kind'])
        done = sum(z['qty'] * z['price'] for z in o['exits']); done_q = sum(z['qty'] for z in o['exits'])
        o['upnl'] = round(o['left'] * (now_p - o['entry']) + done - done_q * o['entry'] - o['fees'], 4); o['upnl_usd'] = round(o['upnl'] * k, 2)
        o['now'] = now_p; o['now_usd'] = round(o['left'] * now_p * k, 2); o['stop'] = round(o['stop'], 6); o['fees'] = round(o['fees'], 4)
        o['risk0'] = round(o['risk0'], 6)
        for k2 in ('opened_T',): o.pop(k2, None)
        opens.append(o)
    for t in closed: t['fees'] = round(t['fees'], 4); t['stop'] = round(t['stop'], 6); t['risk0'] = round(t['risk0'], 6)
    sweep_usd = sweep_q * (px.get(SWEEP) or 0); inv = sum(o['now_usd'] for o in opens)
    alloc = sorted([{'label': o['name'], 'usd': o['now_usd']} for o in opens], key=lambda z: -z['usd'])
    alloc += [{'label': 'صندوق المؤشر SPY', 'usd': round(sweep_usd, 2), 'sweep': True}, {'label': 'نقد', 'usd': round(cash, 2), 'cash': True}]
    for z in alloc: z['pct'] = round(z['usd'] / eq * 100, 1) if eq else 0
    stats = {}
    for t in closed:
        s = stats.setdefault(t['asset'], {'id': t['asset'], 'name': t['name'], 'kind': t['kind'], 'n': 0, 'wins': 0, 'pnl_usd': 0.0})
        s['n'] += 1; s['wins'] += t['pnl'] > 0; s['pnl_usd'] = round(s['pnl_usd'] + t['pnl_usd'], 2)
    byh = {}
    for t in closed:
        s = byh.setdefault(t['h'], {'h': t['h'], 'name': HZ[t['h']]['name'], 'n': 0, 'wins': 0, 'pnl_usd': 0.0, 'r': 0.0})
        s['n'] += 1; s['wins'] += t['win']; s['pnl_usd'] = round(s['pnl_usd'] + t['pnl_usd'], 2); s['r'] = round(s['r'] + (t['r_mult'] or 0), 2)
    wins = sum(1 for t in closed if t['pnl'] > 0)
    gw = round(sum(t['pnl_usd'] for t in closed if t['pnl_usd'] > 0), 2); gl = round(sum(t['pnl_usd'] for t in closed if t['pnl_usd'] <= 0), 2)
    spy_now = px.get(SWEEP)
    frozen_now = cyc['frozen_until'] is not None and now < cyc['frozen_until']
    return {
        'totals': {'start_usd': START_USD, 'capital_usd': round(eq, 2), 'profit_wallet_usd': round(pw[0], 2), 'equity_usd': round(eq + pw[0], 2),
                   'pnl_usd': round(eq + pw[0] - START_USD, 2), 'pct': round((eq + pw[0]) / START_USD * 100 - 100, 3),
                   'wins': wins, 'losses': len(closed) - wins, 'gross_win_usd': gw, 'gross_loss_usd': gl,
                   'open_n': len(opens), 'closed_n': len(closed), 'win_rate': round(wins / len(closed) * 100, 1) if closed else None,
                   'cash_usd': round(cash, 2), 'sweep_usd': round(sweep_usd, 2), 'invested_usd': round(inv, 2),
                   'util': round((inv + sweep_usd) / eq * 100, 1) if eq else 0,
                   'bench_pct': round((spy_now / spy0 - 1) * 100, 3) if spy0 and spy_now else None},
        'cycle': {'n': cyc['n'], 'start': cyc['start'], 'cap0': round(cyc['cap0'], 2), 'pnl_usd': round(cyc['pnl'], 2),
                  'progress_pct': round(cyc['pnl'] / cyc['cap0'] * 100, 2) if cyc['cap0'] else 0, 'target_pct': CY['target_pct'],
                  'frozen': frozen_now, 'frozen_until': cyc['frozen_until'].date().isoformat() if frozen_now else None, 'history': cycles},
        'audit': {'audited': nonlocal_audit[0], 'opened': n, 'rejected': rejects},
        'by_h': sorted(byh.values(), key=lambda s: ['M', 'W', 'D', 'H4'].index(s['h'])),
        'open': sorted(opens, key=lambda o: o['opened'], reverse=True), 'closed': sorted(closed, key=lambda t: t['closed'], reverse=True),
        'sweep': {'asset': SWEEP, 'name': 'صندوق إس آند بي 500', 'qty': round(sweep_q, 6), 'avg': round(sw_cost[0] / sweep_q, 4) if sweep_q else None, 'now': px.get(SWEEP),
                  'cost_usd': round(sw_cost[0], 2), 'value_usd': round(sweep_usd, 2), 'pnl_usd': round(sweep_usd - sw_cost[0], 2)},
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

def archive_v1():
    """Final state of the first version (rules unchanged), frozen at V1_END."""
    try:
        import importlib.util
        sp = importlib.util.spec_from_file_location('paper_v1', os.path.join(HERE, 'paper_v1.py'))
        m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
        r = m.run(V1_END); T = r['totals']
        return {'name': 'الإصدار الأول', 'from': m.LAUNCH, 'to': V1_END.date().isoformat(), 'start_usd': T['start_usd'], 'equity_usd': T['equity_usd'], 'pct': T['pct'],
                'closed_n': T['closed_n'], 'wins': T['wins'], 'losses': T['losses'], 'win_rate': T['win_rate'], 'open_n': T['open_n'], 'bench_pct': T['bench_pct'],
                'closed': [{k: t.get(k) for k in ('asset', 'name', 'opened', 'closed', 'entry', 'exit', 'pnl_usd', 'pnl_pct', 'win')} for t in r['closed']],
                'open': [{k: t.get(k) for k in ('asset', 'name', 'opened', 'entry', 'now', 'upnl_usd')} for t in r['open']]}
    except Exception as e:
        return {'name': 'الإصدار الأول', 'error': str(e)[:120]}

def main():
    now = dt.datetime.now(dt.timezone.utc)
    r = run(now)
    r['archive'] = [archive_v1()]
    book = {'updated': now.strftime('%Y-%m-%dT%H:%MZ'), 'launch': LAUNCH, 'mode': 'professor', 'version': R['version'],
            'rules': {'risk': RK['risk_per_trade'], 'max_w': RK['max_weight'], 'max_open': RK['max_open'], 'min_rr': AU['min_rr'],
                      'breakeven_r': RK['breakeven_at_r'], 'horizons': {h: {'name': v['name'], 'max_hold_days': v['max_hold_days'], 'cap': v['target_cap_atr']} for h, v in HZ.items()},
                      'checks': AU['checks'], 'news': R['news']['policy'], 'cycle': CY, 'fees': FEE, 'slip': SLIP, 'sweep': SWEEP}, **r}
    if os.environ.get('PAPER_DEBUG'):
        json.dump(book, open(os.environ['PAPER_DEBUG'], 'w'), ensure_ascii=False, indent=1, default=str)
        if os.environ.get('PAPER_NOWRITE'):
            T = r['totals']; print(f"open={T['open_n']} closed={T['closed_n']} equity={T['equity_usd']} pct={T['pct']} win={T['win_rate']} audit={r['audit']} cycle={r['cycle']['n']},{r['cycle']['progress_pct']}% hist={len(r['cycle']['history'])}")
            return
    os.makedirs(os.path.join(ROOT, 'vault'), exist_ok=True)
    json.dump(encrypt(book), open(os.path.join(ROOT, 'vault', 'book.json'), 'w'), separators=(',', ':'))
    T = r['totals']
    print(f"universe={r['universe']} open={T['open_n']} closed={T['closed_n']} equity={T['equity_usd']} util={T['util']}% cycle={r['cycle']['progress_pct']}% errors={len(r['errors'])}")

if __name__ == '__main__':
    main()
