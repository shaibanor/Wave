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
MODE = R.get('mode', 'multi'); RO = R.get('rolling', {})
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
        d = bars(j['d']); m = bars(j.get('m', [])); h4 = bars(j.get('4h', []))
    return d, m, h4

def h4_close(kind, t):
    s = dt.datetime.fromtimestamp(t, dt.timezone.utc)
    e = s + dt.timedelta(hours=4)
    if kind == 'sa':
        dl = s.astimezone(TZ['sa']).date()
        e = min(e, dt.datetime(dl.year, dl.month, dl.day, 15, 0, tzinfo=TZ['sa']))
    elif kind == 'us':
        dl = s.astimezone(TZ['us']).date()
        e = min(e, dt.datetime(dl.year, dl.month, dl.day, 16, 0, tzinfo=TZ['us']))
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
                ld = local_date(kind, x['t']) if kind in ('sa', 'us') else day(x['t'])
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
    ticks, last, errs, prep, fresh = [], {}, [], {}, {}
    for aid, name, kind in ASSETS:
        try:
            P = prepare(aid, kind, now, launch)
        except FileNotFoundError:
            errs.append(f'{aid}: no data yet'); continue
        except Exception as e:
            errs.append(f'{aid}: {str(e)[:100]}'); continue
        if not P: errs.append(f'{aid}: not enough data'); continue
        prep[aid] = P; last[aid] = P['d'][-1]['c']
        fresh[aid] = {'name': name, 'kind': kind, 'd': day(P['d'][-1]['t']).isoformat(), 'h4': P['h4'][-1]['T'].strftime('%Y-%m-%d %H:%MZ') if P['h4'] else None}
        h4days = {z['date'] for z in P['h4']}
        for z in P['h4']: ticks.append((z['T'], 0, aid, kind, 'h4', z))
        for i, c in P['ctx'].items():
            ticks.append((close_time(kind, c['date']), 1, aid, kind, 'dsig' if c['date'] in h4days else 'day', c))
    ticks.sort(key=lambda e: (e[0], e[1], e[2]))
    cash, sweep_q = START_USD, 0.0
    pos, closed, curve, n = {}, [], {}, 0
    pw = [0.0]; sw_cost = [0.0]; px = {}; spy0 = None
    cyc = {'n': 1, 'start': None, 'cap0': START_USD, 'pnl': 0.0, 'sum_pct': 0.0, 'trades': [], 'frozen_until': None}; cycles = []
    rejects = {'monthly': 0, 'levels': 0, 'traps': 0, 'rr': 0}; audited = 0
    peak = [START_USD]; mdd = [0.0]; cyc['tot0'] = START_USD
    ctxD = {}

    def equity():
        v = cash + sweep_q * (px.get(SWEEP) or 0)
        for a, p in pos.items():
            if p.get('margin') is not None:
                v += (p['margin'] * p['left'] / p['qty'] + p.get('side', 1) * p['left'] * ((px.get(a) or p['entry']) - p['entry'])) * fx(p['kind'])
            else:
                v += p['left'] * (px.get(a) or p['entry']) * fx(p['kind'])
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
        sd = p.get('side', 1)
        p['pnl'] = round(sd * (got - p['qty'] * p['entry']) - p['fees'], 4); p['pnl_usd'] = round(p['pnl'] * fx(p['kind']), 2)
        p['px_pct'] = round(p['pnl'] / (p['qty'] * p['entry']) * 100, 3)
        p['pnl_pct'] = round(p['pnl'] / (p['margin'] if p.get('margin') else p['qty'] * p['entry']) * 100, 2); p['status'] = 'closed'; p['closed'] = ds
        p['exit'] = round(got / p['qty'], 6); p['win'] = p['pnl'] > 0
        p['r_mult'] = round(sd * (p['exit'] - p['entry']) / p['risk0'], 2) if p['risk0'] else None
        p['mfe_pct'] = round(sd * (p.get('mfe', p['entry']) / p['entry'] - 1) * 100, 2); p['mae_pct'] = round(sd * (p.get('mae', p['entry']) / p['entry'] - 1) * 100, 2)
        p['held_days'] = (dt.date.fromisoformat(ds) - dt.date.fromisoformat(p['opened'])).days
        cyc['pnl'] += p['pnl_usd']; cyc['sum_pct'] += p['pnl_pct']; cyc['trades'].append(p)
        if p.get('roll'): outcomes.append({'pnl_pct': p['px_pct'], 'win': p['win'], 'shadow': False, 'asset': p['asset'], 'side': 2 if p.get('setup') == 'oversold' else p.get('side', 1)})
        if p['pnl_usd'] > 0: pw[0] += p['pnl_usd']; cash -= p['pnl_usd']
        for k in ('opened_T', 'left', 'risk0_px'): p.pop(k, None)
        closed.append(p)

    def fill(p, q, price, why, ds):
        nonlocal cash
        sd = p.get('side', 1)
        f = FEE[p['kind']]; price = price * (1 - sd * SLIP); val = q * price; fee = val * f
        if p.get('margin') is not None:
            m = p['margin'] * q / p['qty']; gain = sd * q * (price - p['entry'])
            if gain < -m:   # liquidation: the margin is the most that can be lost
                gain = -m; price = p['entry'] - sd * m / q; why = 'تصفية (نفاد الهامش)'
            cash += (m + gain - fee) * fx(p['kind'])
        else:
            cash += (val - fee) * fx(p['kind'])
        p['fees'] += fee; p['left'] -= q
        p['exits'].append({'d': ds, 'price': round(price, 6), 'qty': q, 'why': why})

    def monitor(a, bar, ds, T):
        nonlocal cash
        p = pos.get(a)
        if not p or p['opened_T'] >= T: return
        o, h, l = bar['o'], bar['h'], bar['l']
        if p.get('side', 1) < 0:
            p['mfe'] = min(p.get('mfe', p['entry']), l); p['mae'] = max(p.get('mae', p['entry']), h)
        else:
            p['mfe'] = max(p.get('mfe', p['entry']), h); p['mae'] = min(p.get('mae', p['entry']), l)
        if p.get('lev', 1) > 1 and p['kind'] == 'cx':   # perpetual funding, about 0.01% of the position every 8 hours
            fc = p['left'] * bar['c'] * RO.get('funding_per_8h', .0001) / 2; p['fees'] += fc; cash -= fc
        if p.get('side', 1) < 0:
            cst = 2 * FEE[p['kind']] + 2 * SLIP + .001
            if h >= p['stop']: fill(p, p['left'], max(o, p['stop']), 'وقف التعادل' if p['be'] else 'وقف الخسارة', ds)
            elif l <= p['target']: fill(p, p['left'], min(o, p['target']), 'تحقق الهدف', ds)
            elif not p['be'] and l <= p['entry'] * (1 - RO['breakeven_at_target_frac'] * p['tp_pct'] / 100) and bar['c'] < p['entry'] * (1 - cst):
                p['stop'] = min(p['stop'], p['entry'] * (1 - cst)); p['be'] = True
            if p['left'] <= 1e-12: finish(p, ds); del pos[a]
            return
        if l <= p['stop']: fill(p, p['left'], min(o, p['stop']), 'وقف التعادل' if p['be'] else 'وقف الخسارة', ds)
        elif h >= p['target']: fill(p, p['left'], max(o, p['target']), 'تحقق الهدف', ds)
        elif not p['be'] and p.get('roll') and h >= p['entry'] * (1 + RO['breakeven_at_target_frac'] * p.get('tp_pct', RO['target_pct']) / 100) and bar['c'] > p['entry'] * (1 + 2 * FEE[p['kind']] + 2 * SLIP + .001):
            p['stop'] = max(p['stop'], p['entry'] * (1 + 2 * FEE[p['kind']] + 2 * SLIP + .001)); p['be'] = True
        elif not p['be'] and not p.get('roll') and h >= p['entry'] + RK['breakeven_at_r'] * p['risk0']:
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

    shadow, outcomes = {}, []   # paper-on-paper: setups blocked only by the edge check are still followed, so the check can recover

    def shadow_step(a, bar, T):
        q = shadow.get(a)
        if not q or q['T'] >= T: return
        fee = FEE[q['kind']] * 2 + SLIP * 2
        if q.get('side', 1) < 0:
            if bar['h'] >= q['stop']: r = (1 - max(bar['o'], q['stop']) / q['entry']) * 100 - fee * 100
            elif bar['l'] <= q['target']: r = (1 - min(bar['o'], q['target']) / q['entry']) * 100 - fee * 100
            else:
                if not q['be'] and bar['l'] <= q['entry'] * (1 - RO['breakeven_at_target_frac'] * q['tp'] / 100) and bar['c'] < q['entry'] * (1 - fee - .001):
                    q['stop'] = min(q['stop'], q['entry'] * (1 - fee - .001)); q['be'] = True
                if (T - q['T']).days >= RO['max_hold_days']: r = (1 - bar['c'] / q['entry']) * 100 - fee * 100
                else: return
            outcomes.append({'pnl_pct': round(r, 3), 'win': r > 0, 'shadow': True, 'asset': a, 'side': -1}); del shadow[a]; return
        if bar['l'] <= q['stop']: r = (min(bar['o'], q['stop']) / q['entry'] - 1) * 100 - fee * 100
        elif bar['h'] >= q['target']: r = (max(bar['o'], q['target']) / q['entry'] - 1) * 100 - fee * 100
        else:
            if not q['be'] and bar['h'] >= q['entry'] * (1 + RO['breakeven_at_target_frac'] * q['tp'] / 100) and bar['c'] > q['entry'] * (1 + fee + .001):
                q['stop'] = max(q['stop'], q['entry'] * (1 + fee + .001)); q['be'] = True
            if (T - q['T']).days >= RO['max_hold_days']: r = (bar['c'] / q['entry'] - 1) * 100 - fee * 100
            else: return
        outcomes.append({'pnl_pct': round(r, 3), 'win': r > 0, 'shadow': True, 'asset': a, 'side': q.get('side', 1)}); del shadow[a]

    def edge(side=1):
        L = [o for o in outcomes if o.get('side', 1) == side][-RO.get('edge_window', 30):]
        if len(L) < RO.get('edge_min_trades', 10): return True, None, len(L)
        wr = sum(1 for t in L if t['win']) / len(L) * 100
        aw = sum(t['pnl_pct'] for t in L if t['win']) / max(1, sum(1 for t in L if t['win']))
        al = -sum(t['pnl_pct'] for t in L if not t['win']) / max(1, sum(1 for t in L if not t['win']))
        be = al / (aw + al) * 100 if aw + al > 0 else 100
        return wr > be, {'win_rate': round(wr, 1), 'breakeven': round(be, 1), 'avg_win': round(aw, 3), 'avg_loss': round(al, 3)}, len(L)

    def try_roll(a, kind, z, c, T):
        nonlocal cash, n
        if a == SWEEP or a in pos or kind not in RO['markets'] or len(pos) >= RO['max_open']: return
        cost = (2 * FEE[kind] + 2 * SLIP) * 100
        if RO.get('target_mode', 'fixed') == 'fixed' and RO['target_pct'] - cost < RO.get('min_net_target_pct', 0): return   # costs would eat too much of a 1% target
        if RO.get('target_mode') == 'adaptive' and kind not in RO.get('adaptive_markets', RO['markets']): return
        x = z['bar']; atrv = z['atr']; ctxs = c['sc']
        tg = RO['trigger']; OS = RO.get('oversold') or {}
        if not atrv or not z['e50'] or z['rsi'] is None: return
        osb = bool(OS.get('enabled')) and kind in OS.get('markets', []) and z['rsi'] < OS.get('rsi_below', 30) and x['c'] > x['o']
        if not osb:
            if tg['above_ema50'] and x['c'] <= z['e50']: return
            if z['rsi'] >= tg['rsi_below']: return
            if tg['green_candle'] and x['c'] <= x['o']: return
        nonlocal_audit[0] += 1
        entry = x['c'] * (1 + SLIP); notes = []; ck = {}
        sD, sW, sM = ctxs.get('D'), ctxs.get('W'), ctxs.get('M')
        if osb:   # oversold bounce: only the monthly trend must not be down
            ck['monthly'] = bool(sM) and sM['dir'] != 'down'
        else:
            ck['monthly'] = bool(sD and sW and sM) and sD['dir'] == 'up' and sW['dir'] != 'down' and sM['dir'] != 'down'
        if not ck['monthly']: notes.append('السياق: ' + '، '.join(f"{TFN[t]} {DIRN[s_['dir']]}" for t, s_ in (('M', sM), ('W', sW), ('D', sD)) if s_))
        sp = min(max(RO['stop']['atr_k'] * atrv / entry * 100, RO['stop']['min_pct']), RO['stop']['max_pct'])
        if osb: sp = OS['stop_pct']
        stop = entry * (1 - sp / 100)
        if osb:
            tp = OS['target_pct']; room = tp >= RO['adaptive']['min_net_pct'] + cost
        elif RO.get('target_mode') == 'adaptive':
            # the bullish scenario's first target: nearest 4h/daily resistance that still leaves enough after costs, within reach of volatility
            AD = RO['adaptive']; floor = AD['min_net_pct'] + cost; cap = min(AD['max_atr'] * atrv / entry * 100, AD['max_pct'])
            cand = sorted(((r / entry - 1) * 100 - AD['below_res_atr'] * atrv / entry * 100) for r in z['res'] + c['res']['D'] if r > entry)
            cand = [q for q in cand if q >= floor]
            tp = min(cand[0], cap) if cand else cap
            room = tp >= floor
            if not room: notes.append(f'لا مساحة كافية للهدف بعد التكاليف (المتاح {tp:.2f}%)')
        else:
            tp = RO['target_pct']
            above = [r for r in z['res'] if r > entry * 1.0005]
            room = not RO.get('room_check') or not above or min(above) >= entry * (1 + tp / 100)
            if not room: notes.append(f'مقاومة 4 ساعات {min(above):.6g} قبل الهدف')
        tgt = entry * (1 + tp / 100)
        ck['levels'] = room
        rng = max(1e-12, x['h'] - x['l']); uw = (x['h'] - max(x['o'], x['c'])) / rng
        trap = any(x['h'] > q and x['c'] < q for q in z['prevH'][-6:]) and uw >= TR['failed_breakout_wick']
        ev = event_block(kind, z['date'])
        ck['traps'] = not trap and not ev
        if trap: notes.append('اختراق كاذب بذيل علوي')
        if ev: notes.append('حدث كبير قريب: ' + ev)
        okE, est, nE = edge(2 if osb else 1)
        ck['rr'] = okE
        if not okE: notes.append(f"التوقع سالب: نجاح {est['win_rate']}% أقل من التعادل {est['breakeven']}%")
        if not all(ck.values()):
            for k_, v in ck.items():
                if not v: rejects[k_] += 1
            if ck['monthly'] and ck['levels'] and ck['traps'] and a not in shadow:
                shadow[a] = {'kind': kind, 'entry': entry, 'stop': stop, 'target': tgt, 'tp': tp, 'be': False, 'T': T, 'side': 2 if osb else 1}
            return
        eq = equity(); k = fx(kind); f = FEE[kind]
        L = int(RO.get('leverage', {}).get(kind, 1))
        if L > 1:
            L = max(1, min(L, int(100 / (sp + RO.get('liq_buffer_pct', 1.0)))))   # the stop must come well before liquidation
            if peak[0] and (eq + pw[0]) < peak[0] * (1 - RO.get('dd_brake_pct', 20) / 100): L = max(1, L // 2)   # brake after a drawdown
        margin = RO['weight'] * eq
        raise_cash(margin * (1 + f * L))
        margin = min(margin, max(0.0, cash) / (1 + f * L))
        qty = margin * L / (entry * k)
        qty = math.floor(qty) if kind == 'sa' else math.floor(qty * 1e6) / 1e6
        if qty * entry * k < 100 or (kind == 'sa' and qty < 2): return
        margin = qty * entry * k / L
        n += 1; fee = qty * entry * f; cash -= margin + fee * k
        need = round(sp / (tp + sp) * 100, 1)
        why = (f"ارتداد من تشبع بيعي: شمعة 4 ساعات خضراء وRSI {z['rsi']:.0f} · الشهري {DIRN[sM['dir']]}" if osb else
               f"شمعة 4 ساعات خضراء فوق متوسط 50 بعد تهدئة (RSI {z['rsi']:.0f}) · اليومي {DIRN[sD['dir']]}، الأسبوعي {DIRN[sW['dir']]}، الشهري {DIRN[sM['dir']]}")
        pos[a] = {'id': f'P-{n}', 'asset': a, 'name': names[a][0], 'kind': kind, 'h': 'H4', 'hname': RO['name'], 'roll': True, 'setup': 'oversold' if osb else 'dip', 'cur': 'ريال' if kind == 'sa' else 'دولار',
                  'opened': z['date'].isoformat(), 'opened_at': z['T'].strftime('%Y-%m-%dT%H:%MZ') if hasattr(z['T'], 'strftime') else None, 'opened_T': T,
                  'entry': round(entry, 6), 'qty': qty, 'value': round(qty * entry, 2), 'value_usd': round(qty * entry * k, 2), 'weight': round(qty * entry * k / eq * 100, 1),
                  'stop0': round(stop, 6), 'stop': stop, 'target': round(tgt, 6), 'tp_pct': round(tp, 2), 'sl_pct': round(sp, 2), 'need_win': need,
                  'lev': L, 'margin': margin / k, 'rr': round(tp / sp, 2), 'risk0': entry - stop, 'atr': round(atrv, 6), 'tf': {t: s_['dir'] for t, s_ in (('M', sM), ('W', sW), ('D', sD))},
                  'audit': ck, 'notes': notes, 'why': why, 'left': qty, 'be': False, 'exits': [], 'fees': fee, 'status': 'open'}

    def try_short(a, kind, z, c, T):
        """Mirror of try_roll for falling markets: sell a bounce in a downtrend (perpetual futures)."""
        nonlocal cash, n
        SO = RO.get('short') or {}
        if not SO.get('enabled') or a == SWEEP or a in pos or kind not in SO.get('markets', []) or len(pos) >= RO['max_open']: return
        cost = (2 * FEE[kind] + 2 * SLIP) * 100
        x = z['bar']; atrv = z['atr']; ctxs = c['sc']
        if not atrv or not z['e50'] or z['rsi'] is None: return
        if x['c'] >= z['e50'] or z['rsi'] <= SO.get('rsi_above', 50) or x['c'] >= x['o']: return
        nonlocal_audit[0] += 1
        entry = x['c'] * (1 - SLIP); notes = []; ck = {}
        sD, sW, sM = ctxs.get('D'), ctxs.get('W'), ctxs.get('M')
        ck['monthly'] = bool(sD and sW and sM) and sD['dir'] == 'down' and sW['dir'] != 'up' and sM['dir'] != 'up'
        if not ck['monthly']: notes.append('السياق: ' + '، '.join(f"{TFN[t]} {DIRN[s_['dir']]}" for t, s_ in (('M', sM), ('W', sW), ('D', sD)) if s_))
        sp = min(max(RO['stop']['atr_k'] * atrv / entry * 100, RO['stop']['min_pct']), RO['stop']['max_pct'])
        stop = entry * (1 + sp / 100)
        AD = RO['adaptive']; floor = AD['min_net_pct'] + cost; cap = min(AD['max_atr'] * atrv / entry * 100, AD['max_pct'])
        cand = sorted(((1 - r / entry) * 100 - AD['below_res_atr'] * atrv / entry * 100) for r in z['sup'] + c['sup']['D'] if r < entry)
        cand = [q for q in cand if q >= floor]
        tp = min(cand[0], cap) if cand else cap
        ck['levels'] = tp >= floor
        if not ck['levels']: notes.append(f'لا مساحة كافية للهدف بعد التكاليف (المتاح {tp:.2f}%)')
        tgt = entry * (1 - tp / 100)
        rng = max(1e-12, x['h'] - x['l']); lw = (min(x['o'], x['c']) - x['l']) / rng
        trap = any(x['l'] < q and x['c'] > q for q in z['prevL'][-6:]) and lw >= TR['failed_breakout_wick']
        ev = event_block(kind, z['date'])
        ck['traps'] = not trap and not ev
        if trap: notes.append('كسر كاذب بذيل سفلي')
        if ev: notes.append('حدث كبير قريب: ' + ev)
        okE, est, nE = edge(-1)
        ck['rr'] = okE
        if not okE: notes.append(f"التوقع سالب: نجاح {est['win_rate']}% أقل من التعادل {est['breakeven']}%")
        if not all(ck.values()):
            for k_, v in ck.items():
                if not v: rejects[k_] += 1
            if ck['monthly'] and ck['levels'] and ck['traps'] and a not in shadow:
                shadow[a] = {'kind': kind, 'entry': entry, 'stop': stop, 'target': tgt, 'tp': tp, 'be': False, 'T': T, 'side': -1}
            return
        eq = equity(); k = fx(kind); f = FEE[kind]
        L = int(RO.get('leverage', {}).get(kind, 1))
        if L > 1:
            L = max(1, min(L, int(100 / (sp + RO.get('liq_buffer_pct', 1.0)))))
            if peak[0] and (eq + pw[0]) < peak[0] * (1 - RO.get('dd_brake_pct', 20) / 100): L = max(1, L // 2)
        margin = RO['weight'] * eq
        raise_cash(margin * (1 + f * L))
        margin = min(margin, max(0.0, cash) / (1 + f * L))
        qty = math.floor(margin * L / (entry * k) * 1e6) / 1e6
        if qty * entry * k < 100: return
        margin = qty * entry * k / L
        n += 1; fee = qty * entry * f; cash -= margin + fee * k
        why = f"بيع على المكشوف: شمعة 4 ساعات حمراء تحت متوسط 50 بعد ارتداد (RSI {z['rsi']:.0f}) · اليومي {DIRN[sD['dir']]}، الأسبوعي {DIRN[sW['dir']]}، الشهري {DIRN[sM['dir']]}"
        pos[a] = {'id': f'P-{n}', 'asset': a, 'name': names[a][0], 'kind': kind, 'h': 'H4', 'hname': RO['name'], 'roll': True, 'side': -1, 'cur': 'دولار',
                  'opened': z['date'].isoformat(), 'opened_at': z['T'].strftime('%Y-%m-%dT%H:%MZ') if hasattr(z['T'], 'strftime') else None, 'opened_T': T,
                  'entry': round(entry, 6), 'qty': qty, 'value': round(qty * entry, 2), 'value_usd': round(qty * entry * k, 2), 'weight': round(qty * entry * k / eq * 100, 1),
                  'stop0': round(stop, 6), 'stop': stop, 'target': round(tgt, 6), 'tp_pct': round(tp, 2), 'sl_pct': round(sp, 2), 'need_win': round(sp / (tp + sp) * 100, 1),
                  'lev': L, 'margin': margin / k, 'rr': round(tp / sp, 2), 'risk0': stop - entry, 'atr': round(atrv, 6), 'tf': {t: s_['dir'] for t, s_ in (('M', sM), ('W', sW), ('D', sD))},
                  'audit': ck, 'notes': notes, 'why': why, 'left': qty, 'be': False, 'exits': [], 'fees': fee, 'status': 'open'}

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
            cyc.update({'n': cyc['n'] + 1, 'start': ds_any, 'cap0': equity(), 'tot0': equity() + pw[0], 'pnl': 0.0, 'sum_pct': 0.0, 'trades': [], 'frozen_until': None, 'hit': None, 'hit_pct': None})
        # exits
        for (_, _, a, kind, typ, z) in G:
            ds = z['date'].isoformat()
            if typ in ('h4', 'day'): monitor(a, z['bar'], ds, T)
            if typ == 'h4': shadow_step(a, z['bar'], T)
            if typ in ('day', 'dsig'):
                ctxD[a] = z
                p = pos.get(a)
                if p and p['opened_T'] < T and p.get('roll'):
                    if (z['date'] - dt.date.fromisoformat(p['opened'])).days >= RO['max_hold_days']:
                        fill(p, p['left'], z['bar']['c'], 'انتهاء مدة الصفقة', ds); finish(p, ds); del pos[a]
                elif p and p['opened_T'] < T:
                    hz = HZ[p['h']]; par = hz['exit_on']; s = z['sc'].get(par)
                    if s and s['dir'] == 'down' and (par != 'M' or z['month_end']):
                        fill(p, p['left'], z['bar']['c'], f"انعكاس الاتجاه {TFN[par]}", ds)
                    elif (z['date'] - dt.date.fromisoformat(p['opened'])).days >= hz['max_hold_days']:
                        fill(p, p['left'], z['bar']['c'], 'انتهاء مدة الصفقة', ds)
                    if p['left'] <= 1e-12: finish(p, ds); del pos[a]
        # entries
        if not frozen and not cyc.get('hit'):
            cands = []
            if MODE == 'h4_rolling':
                for (_, _, a, kind, typ, z) in G:
                    if typ == 'h4' and ctxD.get(a):
                        try_roll(a, kind, z, ctxD[a], T)
                        try_short(a, kind, z, ctxD[a], T)
                G_ = []
            else:
                G_ = G
            for (_, _, a, kind, typ, z) in G_:
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
        tot = equity() + pw[0]; peak[0] = max(peak[0], tot); mdd[0] = max(mdd[0], (1 - tot / peak[0]) * 100)
        if CY.get('measure') == 'equity_double': prog = (tot / cyc['tot0'] - 1) * 100
        else: prog = cyc['sum_pct'] if CY.get('measure') == 'sum_trade_pct' else (cyc['pnl'] / cyc['cap0'] * 100 if cyc['cap0'] else 0)
        if not frozen and not cyc.get('hit') and prog >= CY['target_pct']:
            cyc['hit'] = ds_any; cyc['hit_pct'] = round(prog, 2)   # target reached: no new entries; open trades finish at their own target/stop
        if not frozen and cyc.get('hit') and not pos:
            ds = ds_any
            if sweep_q > 0 and px.get(SWEEP):
                val = sweep_q * px[SWEEP] * (1 - SLIP); cash += val - val * FEE['us']; sweep_q = 0.0; sw_cost[0] = 0.0
            fz = T + dt.timedelta(days=CY['freeze_days'])
            TT_ = cyc['trades']; W_ = [t for t in TT_ if t['win']]; L_ = [t for t in TT_ if not t['win']]
            bym = {}
            for t in TT_:
                m_ = bym.setdefault(t['kind'], {'n': 0, 'wins': 0, 'sum_pct': 0.0, 'pnl_usd': 0.0}); m_['n'] += 1; m_['wins'] += t['win']; m_['sum_pct'] = round(m_['sum_pct'] + t['pnl_pct'], 2); m_['pnl_usd'] = round(m_['pnl_usd'] + t['pnl_usd'], 2)
            cycles.append({'n': cyc['n'], 'start': cyc['start'], 'end': ds, 'hit': cyc['hit'], 'hit_pct': cyc['hit_pct'], 'days': (dt.date.fromisoformat(ds) - dt.date.fromisoformat(cyc['start'])).days, 'cap0': round(cyc['cap0'], 2),
                           'pnl_usd': round(cyc['pnl'], 2), 'pct': round(cyc['pnl'] / cyc['cap0'] * 100, 2), 'sum_pct': round(cyc['sum_pct'], 2), 'tot0': round(cyc['tot0'], 2), 'tot1': round(equity() + pw[0], 2), 'growth_pct': round((equity() + pw[0]) / cyc['tot0'] * 100 - 100, 2), 'max_dd_pct': round(mdd[0], 2), 'max_lev': max([t.get('lev', 1) for t in cyc['trades']] or [1]),
                           'trades': len(TT_), 'wins': len(W_), 'losses': len(L_), 'win_rate': round(len(W_) / len(TT_) * 100, 1) if TT_ else None,
                           'avg_win_pct': round(sum(t['pnl_pct'] for t in W_) / len(W_), 2) if W_ else None, 'avg_loss_pct': round(sum(t['pnl_pct'] for t in L_) / len(L_), 2) if L_ else None,
                           'gross_win_usd': round(sum(t['pnl_usd'] for t in W_), 2), 'gross_loss_usd': round(sum(t['pnl_usd'] for t in L_), 2),
                           'best': max(TT_, key=lambda t: t['pnl_pct'])['name'] if TT_ else None, 'worst': min(TT_, key=lambda t: t['pnl_pct'])['name'] if TT_ else None,
                           'by_market': bym, 'frozen_until': fz.date().isoformat()})
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
                  'progress_pct': round((equity() + pw[0]) / cyc['tot0'] * 100 - 100, 2) if CY.get('measure') == 'equity_double' else (round(cyc['sum_pct'], 2) if CY.get('measure') == 'sum_trade_pct' else (round(cyc['pnl'] / cyc['cap0'] * 100, 2) if cyc['cap0'] else 0)), 'tot0': round(cyc['tot0'], 2), 'max_dd_pct': round(mdd[0], 2),
                  'measure': CY.get('measure'), 'trades': len(cyc['trades']), 'wins': sum(1 for t in cyc['trades'] if t['win']), 'target_pct': CY['target_pct'], 'edge': edge()[1], 'edge_short': edge(-1)[1],
                  'frozen': frozen_now, 'hit': cyc.get('hit') if not frozen_now else None, 'hit_pct': cyc.get('hit_pct'), 'frozen_until': cyc['frozen_until'].date().isoformat() if frozen_now else None, 'history': cycles},
        'audit': {'audited': nonlocal_audit[0], 'opened': n, 'rejected': rejects},
        'by_h': sorted(byh.values(), key=lambda s: ['M', 'W', 'D', 'H4'].index(s['h'])),
        'open': sorted(opens, key=lambda o: o['opened'], reverse=True), 'closed': sorted(closed, key=lambda t: t['closed'], reverse=True),
        'sweep': {'asset': SWEEP, 'name': 'صندوق إس آند بي 500', 'qty': round(sweep_q, 6), 'avg': round(sw_cost[0] / sweep_q, 4) if sweep_q else None, 'now': px.get(SWEEP),
                  'cost_usd': round(sw_cost[0], 2), 'value_usd': round(sweep_usd, 2), 'pnl_usd': round(sweep_usd - sw_cost[0], 2)},
        'curve': sorted(curve.items()), 'alloc': alloc, 'stats': sorted(stats.values(), key=lambda s: -s['pnl_usd']),
        'universe': len(ASSETS), 'errors': errs, 'fresh': fresh, 'outcomes': outcomes[-40:]}

# ---------- encryption ----------
def encrypt(obj, keyfile='key.json'):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    kj = json.load(open(os.path.join(ROOT, 'vault', keyfile)))
    pub = serialization.load_der_public_key(base64.b64decode(kj['pub']))
    k = os.urandom(32); iv = os.urandom(12)
    ct = AESGCM(k).encrypt(iv, json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode(), None)
    wk = pub.encrypt(k, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    b = lambda x: base64.b64encode(x).decode()
    return {'v': 1, 'wk': b(wk), 'iv': b(iv), 'ct': b(ct)}

MK = {'sa': 'السوق السعودي', 'us': 'الأسهم الأمريكية', 'cx': 'العملات المشفرة'}

def stale_days(kind, d, now):
    """Market days missing between the last daily bar and the last finished session."""
    last = dt.date.fromisoformat(d); t = now.astimezone(TZ[kind]).date(); n = 0; x = last + dt.timedelta(days=1)
    while x < t:
        if mday(x, kind): n += 1
        x += dt.timedelta(days=1)
    return n

def prof_report(book, now):
    """The professor's check: plain summary points, detailed findings, and monitoring data."""
    C = book['cycle']; A = book['audit']; RO_ = R.get('rolling', {})
    roll = [t for t in book['closed'] if t.get('roll')]
    wins = [t for t in roll if t['win']]; losses = [t for t in roll if not t['win']]
    wr = round(len(wins) / len(roll) * 100, 1) if roll else None
    ed = C.get('edge'); goal = RO_.get('win_rate_goal', 80)
    pts, det = [], []
    if wr is None:
        pts.append({'lv': 'info', 't': 'لا توجد صفقات مغلقة بعد. تبدأ الصفقات عند إغلاق شموع 4 ساعات التي تجتاز التدقيق.'})
    else:
        pts.append({'lv': 'ok' if wr >= goal else 'warn', 't': f'نسبة النجاح {wr}% من {len(roll)} صفقة (الهدف {goal}% أو أكثر).'})
    if ed:
        if ed['win_rate'] > ed['breakeven']:
            pts.append({'lv': 'ok', 't': f"التوقع الرياضي موجب: النجاح {ed['win_rate']}% أعلى من نسبة التعادل {ed['breakeven']}%."})
        else:
            pts.append({'lv': 'bad', 't': f"التوقع الرياضي سالب: النجاح {ed['win_rate']}% أقل من نسبة التعادل {ed['breakeven']}%، لأن متوسط الخسارة {ed['avg_loss']}% أكبر بكثير من متوسط الربح {ed['avg_win']}%. البروفيسور أوقف الدخول الجديد حتى يتحسن."})
    else:
        pts.append({'lv': 'info', 't': f"التوقع الرياضي يُقاس بعد {RO_.get('edge_min_trades', 10)} نتائج على الأقل."})
    pts.append({'lv': 'info', 't': f"تقدم الدورة {C['n']}: مجموع نسب الصفقات {C['progress_pct']}% من {C['target_pct']}%."})
    stale = []
    for a, f in (book.get('fresh') or {}).items():
        lag = stale_days(f['kind'], f['d'], now)
        if lag >= (2 if f['kind'] == 'cx' else 3): stale.append((a, f, lag))
    pts.append({'lv': 'warn' if stale else 'ok', 't': f'بيانات متأخرة في {len(stale)} أصل.' if stale else 'كل البيانات محدثة.'})
    if book.get('errors'): pts.append({'lv': 'bad', 't': f"{len(book['errors'])} خطأ في قراءة البيانات."})
    rj = A.get('rejected', {}); top = max(rj, key=rj.get) if rj and any(rj.values()) else None
    RN = {'monthly': 'السياق (الشهري/الأسبوعي/اليومي)', 'levels': 'مقاومة قبل الهدف', 'traps': 'الفخاخ والأحداث', 'rr': 'التوقع الرياضي السالب'}
    if top: pts.append({'lv': 'info', 't': f"فُحصت {A.get('audited', 0)} فرصة، دخل منها {A.get('opened', 0)}. أكثر سبب للإلغاء: {RN[top]} ({rj[top]})."})
    for t in losses:
        if t.get('mfe_pct', 0) >= RO_.get('breakeven_at_target_frac', .6) * RO_.get('target_pct', 1):
            cause, fix = 'ربحت ثم عادت للوقف', 'السعر وصل قرب الهدف ولم يُحمَ الربح كاملًا؛ يُراقب نقل الوقف أبكر.'
        elif t.get('held_days', 0) <= 1:
            cause, fix = 'انعكاس فوري بعد الدخول', 'الدخول جاء في نهاية حركة؛ يُراقب هل يتكرر على نفس الأصل.'
        else:
            cause, fix = 'هبوط تدريجي حتى الوقف', 'الاتجاه الأكبر ضعف أثناء الصفقة؛ يُراقب انقلاب اليومي.'
        det.append({'k': 'loss', 'lv': 'bad', 'title': f"خسارة {t['name']}: {cause}", 'asset': t['asset'], 'when': t['closed'],
                    'props': {'الدخول': t['entry'], 'الخروج': t['exit'], 'النتيجة %': t['pnl_pct'], 'المبلغ $': t['pnl_usd'], 'أعلى ربح وصلته %': t.get('mfe_pct'),
                              'أسوأ نزول %': t.get('mae_pct'), 'مسافة الوقف %': t.get('sl_pct'), 'المدة بالأيام': t.get('held_days'), 'سبب الإغلاق': t['exits'][0]['why'] if t.get('exits') else ''},
                    'fix': fix})
    for t in roll:
        if t.get('exits') and t['exits'][0]['why'] == 'انتهاء مدة الصفقة':
            det.append({'k': 'time', 'lv': 'warn', 'title': f"{t['name']}: أُغلقت لانتهاء المدة دون هدف أو وقف", 'asset': t['asset'], 'when': t['closed'],
                        'props': {'النتيجة %': t['pnl_pct'], 'أعلى ربح وصلته %': t.get('mfe_pct')}, 'fix': 'الحركة كانت بطيئة؛ يُراقب تكرارها.'})
    for a, f, lag in stale:
        det.append({'k': 'data', 'lv': 'warn', 'title': f"بيانات {f['name']} متأخرة {lag} يوم تداول", 'asset': a, 'when': f['d'],
                    'props': {'السوق': MK[f['kind']], 'آخر شمعة يومية': f['d'], 'آخر شمعة 4 ساعات': f['h4'] or '—'}, 'fix': 'تُعاد محاولة الجلب تلقائيًا في الدورة التالية.'})
    for e in book.get('errors') or []:
        det.append({'k': 'engine', 'lv': 'bad', 'title': 'خطأ في قراءة بيانات أصل', 'asset': e.split(':')[0], 'when': now.date().isoformat(), 'props': {'النص': e}, 'fix': 'يُراجع ملف البيانات.'})
    if ed and ed['win_rate'] <= ed['breakeven']:
        det.append({'k': 'edge', 'lv': 'bad', 'title': 'إيقاف الدخول: التوقع الرياضي سالب', 'asset': '—', 'when': now.date().isoformat(),
                    'props': {'نسبة النجاح %': ed['win_rate'], 'نسبة التعادل اللازمة %': ed['breakeven'], 'متوسط الربح %': ed['avg_win'], 'متوسط الخسارة %': ed['avg_loss'],
                              'عينة القياس': f"آخر {RO_.get('edge_window', 30)} نتيجة (حقيقية وافتراضية)"},
                    'fix': 'متوسط الخسارة أكبر من متوسط الربح، فكل خسارة تمسح عدة أرباح. البروفيسور يتابع الفرص افتراضيًا، ويعود الدخول تلقائيًا عندما يصبح التوقع موجبًا.'})
    # independent reference source (CoinMarketCap / CoinGecko) versus the exchange data the analysis uses
    refs = None; cross = []
    try:
        refs = json.load(open(os.path.join(ROOT, 'pro', 'refs.json'), encoding='utf-8'))
    except Exception:
        refs = None
    if refs:
        age = (now - dt.datetime.strptime(refs['updated'], '%Y-%m-%dT%H:%MZ').replace(tzinfo=dt.timezone.utc)).total_seconds() / 3600
        for sym, r in refs.get('coins', {}).items():
            try:
                j = json.load(open(os.path.join(ROOT, 'pro', 'cx', f'{sym}.json')))
                h1 = j.get('1h') or []
                ex = float(h1[-1][4]) if h1 else None
                vol_ex = sum(float(x[5]) * float(x[4]) for x in h1[-24:]) if h1 and len(h1[-1]) > 5 else None
            except Exception:
                ex, vol_ex = None, None
            dev = round((ex / r['price'] - 1) * 100, 2) if ex and r.get('price') else None
            cross.append({'asset': sym, 'ref_price': r.get('price'), 'exchange_price': ex, 'dev_pct': dev, 'vol24_global': r.get('vol24'), 'vol24_exchange': round(vol_ex) if vol_ex else None,
                          'mcap': r.get('mcap'), 'rank': r.get('rank')})
            if dev is not None and abs(dev) > 1.5 and age < 6:
                det.append({'k': 'cross', 'lv': 'warn', 'title': f'سعر {sym} في بيانات التحليل يختلف عن المرجع العالمي بـ {dev}%', 'asset': sym, 'when': refs['updated'],
                            'props': {'المرجع': refs.get('source'), 'سعر المرجع': r.get('price'), 'سعر بيانات التحليل': ex, 'الفرق %': dev}, 'fix': 'قد يكون فرق توقيت بين المصدرين؛ إن تكرر يُراجع مصدر البيانات.'})
        bad = [c for c in cross if c['dev_pct'] is not None and abs(c['dev_pct']) > 1.5]
        pts.append({'lv': 'warn' if (bad and age < 6) or age > 12 else 'ok', 't': (f"مطابقة العملات مع {refs.get('source')}: " + (f'{len(bad)} عملة بفرق أكبر من 1.5%.' if bad else 'الأسعار متطابقة ضمن 1.5%.') + (f' (المرجع عمره {age:.0f} ساعة)' if age > 12 else ''))})
    else:
        pts.append({'lv': 'warn', 't': 'لم يصل المرجع العالمي للعملات بعد (CoinGecko / CoinMarketCap).'})
    rep_ = None
    try:
        import urllib.request
        with urllib.request.urlopen('https://raw.githubusercontent.com/shaibanor/Wave/reports/latest.json', timeout=10) as r:
            rep_ = json.loads(r.read().decode())
    except Exception:
        rep_ = None
    if rep_:
        iss = rep_.get('issues') or []
        for it in iss[:20]:
            d_ = it if isinstance(it, dict) else {'t': str(it)}
            det.append({'k': 'site', 'lv': 'warn', 'title': str(d_.get('m') or d_.get('t') or d_)[:160], 'asset': str(d_.get('a') or '—'), 'when': str(rep_.get('when', ''))[:16],
                        'props': {str(k): str(v)[:160] for k, v in d_.items()}, 'fix': str(d_.get('fix', ''))})
        pts.append({'lv': 'ok' if not iss else 'warn', 't': 'فحص الموقع اليومي سليم: لا أخطاء في الصفحات ولا في الملفات.' if not iss else f'فحص الموقع اليومي وجد {len(iss)} ملاحظة.'})
    mon = {'updated': now.strftime('%Y-%m-%d %H:%M UTC'), 'mode': R.get('mode'), 'rules_version': R.get('version'), 'universe': book.get('universe'),
           'with_4h': sum(1 for f in (book.get('fresh') or {}).values() if f['h4']), 'audited': A.get('audited'), 'opened': A.get('opened'), 'rejected': rj,
           'edge': ed, 'outcomes': book.get('outcomes'),
           'open': [{'asset': t['asset'], 'name': t['name'], 'entry': t['entry'], 'now': t['now'], 'target': t['target'], 'stop': t['stop'], 'upnl_usd': t['upnl_usd']} for t in book['open']],
           'cycle': {k: C.get(k) for k in ('n', 'start', 'progress_pct', 'target_pct', 'trades', 'wins', 'frozen', 'frozen_until')}, 'backtest': RO_.get('backtest'),
           'fresh': [{'asset': a, 'name': f['name'], 'market': MK[f['kind']], 'd': f['d'], 'h4': f['h4'], 'lag': stale_days(f['kind'], f['d'], now)} for a, f in (book.get('fresh') or {}).items()],
           'refs': {'source': refs.get('source'), 'updated': refs.get('updated'), 'coins': cross} if refs else None,
           'site_report': {'when': str(rep_.get('when', ''))[:16], 'issues': len(rep_.get('issues') or []), 'checks': [str(c.get('a', '')) + ': ' + str(c.get('m', '')) for c in (rep_.get('checks') or [])][:20]} if rep_ else None}
    lvl = 'bad' if any(p_['lv'] == 'bad' for p_ in pts) else 'warn' if any(p_['lv'] == 'warn' for p_ in pts) else 'ok'
    return {'v': 1, 'status': lvl, 'points': pts, 'findings': det, 'monitor': mon}

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
                      'checks': AU['checks'], 'news': R['news']['policy'], 'cycle': CY, 'rolling': RO if MODE == 'h4_rolling' else None, 'mode': MODE, 'fees': FEE, 'slip': SLIP, 'sweep': SWEEP}, **r}
    if os.environ.get('PAPER_DEBUG'):
        json.dump(book, open(os.environ['PAPER_DEBUG'], 'w'), ensure_ascii=False, indent=1, default=str)
        if os.environ.get('PAPER_PROF'): json.dump(prof_report(book, now), open(os.environ['PAPER_PROF'], 'w'), ensure_ascii=False, indent=1)
        if os.environ.get('PAPER_NOWRITE'):
            T = r['totals']; print(f"open={T['open_n']} closed={T['closed_n']} equity={T['equity_usd']} pct={T['pct']} win={T['win_rate']} audit={r['audit']} cycle={r['cycle']['n']},{r['cycle']['progress_pct']}% hist={len(r['cycle']['history'])}")
            return
    os.makedirs(os.path.join(ROOT, 'vault'), exist_ok=True)
    pr = prof_report(book, now)
    for k_ in ('fresh', 'outcomes'): book.pop(k_, None)
    json.dump(encrypt(book), open(os.path.join(ROOT, 'vault', 'book.json'), 'w'), separators=(',', ':'))
    if os.path.exists(os.path.join(ROOT, 'vault', 'prof_key.json')):
        json.dump(encrypt(pr, 'prof_key.json'), open(os.path.join(ROOT, 'vault', 'prof.json'), 'w'), separators=(',', ':'))
    T = r['totals']
    print(f"universe={r['universe']} open={T['open_n']} closed={T['closed_n']} equity={T['equity_usd']} util={T['util']}% cycle={r['cycle']['progress_pct']}% errors={len(r['errors'])}")

if __name__ == '__main__':
    main()
