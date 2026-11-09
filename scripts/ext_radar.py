#!/usr/bin/env python3
"""External Tiko Radar for stocks that are not listed on the site.
Every run downloads 1h bars (60 days) and daily bars for a wider US and Saudi universe, builds 4h session candles,
and applies the same rule as the in-site radar: a sharp 4h flush (RSI under 32, or 5%+ down over three candles),
target the first resistance between 1.8% and what one candle can reach (else 2%), stop under support or 3%.
Writes pro/ext_radar.json. Crypto is scanned live in the browser from Binance, so it is not here."""
import json, os, math, datetime as dt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pro')
NOW = dt.datetime.now(dt.timezone.utc)
US = {'AAPL': 'Apple', 'MSFT': 'Microsoft', 'NVDA': 'NVIDIA', 'AMZN': 'Amazon', 'TSLA': 'Tesla', 'NFLX': 'Netflix', 'AMD': 'AMD',
      'COST': 'Costco', 'UNH': 'UnitedHealth', 'XOM': 'Exxon Mobil', 'WMT': 'Walmart', 'ORCL': 'Oracle', 'CRM': 'Salesforce',
      'ADBE': 'Adobe', 'INTC': 'Intel', 'QCOM': 'Qualcomm', 'TXN': 'Texas Instruments', 'MU': 'Micron', 'AMAT': 'Applied Materials',
      'PLTR': 'Palantir', 'UBER': 'Uber', 'SHOP': 'Shopify', 'PYPL': 'PayPal', 'BAC': 'Bank of America', 'WFC': 'Wells Fargo',
      'GS': 'Goldman Sachs', 'MS': 'Morgan Stanley', 'C': 'Citigroup', 'KO': 'Coca-Cola', 'PEP': 'PepsiCo', 'MCD': "McDonald's",
      'NKE': 'Nike', 'DIS': 'Disney', 'HD': 'Home Depot', 'CVX': 'Chevron', 'PFE': 'Pfizer', 'MRK': 'Merck', 'ABBV': 'AbbVie',
      'JNJ': 'Johnson & Johnson', 'BA': 'Boeing', 'CAT': 'Caterpillar', 'GE': 'GE Aerospace', 'IBM': 'IBM', 'CSCO': 'Cisco',
      'ANET': 'Arista Networks', 'COIN': 'Coinbase', 'MSTR': 'Strategy', 'SMCI': 'Super Micro', 'ARM': 'Arm Holdings',
      'PANW': 'Palo Alto Networks', 'CRWD': 'CrowdStrike', 'SNOW': 'Snowflake', 'NOW': 'ServiceNow', 'INTU': 'Intuit', 'ABNB': 'Airbnb'}
SA = {'2280': ('المراعي', 'Almarai'), '4190': ('جرير', 'Jarir'), '1060': ('البنك الأول', 'SAB'), '5110': ('الكهرباء', 'Saudi Electricity'),
      '2050': ('صافولا', 'Savola'), '1050': ('البنك السعودي الفرنسي', 'Banque Saudi Fransi'), '2020': ('سابك للمغذيات', 'SABIC Agri-Nutrients'),
      '4280': ('المملكة القابضة', 'Kingdom Holding'), '2380': ('بترو رابغ', 'Petro Rabigh'), '2310': ('سبكيم', 'Sipchem'), '2290': ('ينساب', 'Yansab'),
      '1140': ('بنك البلاد', 'Bank Albilad'), '1030': ('البنك السعودي للاستثمار', 'Saudi Investment Bank'), '1080': ('البنك العربي الوطني', 'Arab National Bank'),
      '2330': ('المتقدمة', 'Advanced Petrochemical'), '4002': ('المواساة', 'Mouwasat'), '4004': ('دله الصحية', 'Dallah Health'), '4164': ('النهدي', 'Nahdi'),
      '7020': ('موبايلي', 'Mobily'), '7030': ('زين السعودية', 'Zain KSA'), '2350': ('كيان السعودية', 'Saudi Kayan'), '3030': ('أسمنت السعودية', 'Saudi Cement'),
      '3020': ('أسمنت اليمامة', 'Yamama Cement'), '4030': ('البحري', 'Bahri'), '4200': ('الدريس', 'Aldrees'), '4263': ('سال', 'SAL'),
      '2223': ('لوبريف', 'Luberef'), '1111': ('مجموعة تداول', 'Saudi Tadawul Group'), '4300': ('دار الأركان', 'Dar Al Arkan'), '4250': ('جبل عمر', 'Jabal Omar'),
      '2083': ('مرافق', 'Marafiq'), '7203': ('علم', 'Elm'), '7202': ('حلول', 'solutions'), '4001': ('أسواق العثيم', 'Othaim Markets'), '2270': ('سدافكو', 'SADAFCO')}
COST = {'us': 0.2, 'sa': 0.4}
TARGET, REACH = 2.0, 1.25


def ema(v, n):
    o, k, e = [None] * len(v), 2 / (n + 1), None
    if len(v) < n:
        return o
    e = sum(v[:n]) / n; o[n - 1] = e
    for i in range(n, len(v)):
        e = v[i] * k + e * (1 - k); o[i] = e
    return o


def rsi(c, n=14):
    o = [None] * len(c)
    if len(c) <= n:
        return o
    g = sum(max(c[i] - c[i - 1], 0) for i in range(1, n + 1)) / n
    l = sum(max(c[i - 1] - c[i], 0) for i in range(1, n + 1)) / n
    o[n] = 100 if l == 0 else 100 - 100 / (1 + g / l)
    for i in range(n + 1, len(c)):
        d = c[i] - c[i - 1]; g = (g * (n - 1) + max(d, 0)) / n; l = (l * (n - 1) + max(-d, 0)) / n
        o[i] = 100 if l == 0 else 100 - 100 / (1 + g / l)
    return o


def atr(b, n=14):
    o = [None] * len(b)
    if len(b) <= n:
        return o
    tr = [b[0][2] - b[0][3]] + [max(b[i][2] - b[i][3], abs(b[i][2] - b[i - 1][4]), abs(b[i][3] - b[i - 1][4])) for i in range(1, len(b))]
    a = sum(tr[1:n + 1]) / n; o[n] = a
    for i in range(n + 1, len(b)):
        a = (a * (n - 1) + tr[i]) / n; o[i] = a
    return o


def swings(b, k):
    H, L = [], []
    for i in range(k, len(b) - k):
        if all(b[i - j][2] < b[i][2] and b[i + j][2] <= b[i][2] for j in range(1, k + 1)):
            H.append(b[i][2])
        if all(b[i - j][3] > b[i][3] and b[i + j][3] >= b[i][3] for j in range(1, k + 1)):
            L.append(b[i][3])
    return H, L


def rows(df):
    out = []
    for idx, r in df.iterrows():
        o, h, l, c = (float(r.get(k, float('nan'))) for k in ('Open', 'High', 'Low', 'Close'))
        if not all(x == x and x > 0 for x in (o, h, l, c)):
            continue
        out.append([int(idx.timestamp()), o, max(h, o, c), min(l, o, c), c, idx.date().isoformat()])
    return out


def to4h(h1):
    out, cur, day, k = [], None, None, 0
    for t, o, h, l, c, d in h1:
        if d != day:
            day, k = d, 0
        if k % 4 == 0:
            if cur:
                out.append(cur)
            cur = [t, o, h, l, c]
        else:
            cur[2], cur[3], cur[4] = max(cur[2], h), min(cur[3], l), c
        k += 1
    if cur:
        out.append(cur)
    return out


def pc(v):
    return f"{'+' if v >= 0 else ''}{v:.2f}%"


def analyse(mk, sym, b, h1, d):
    if len(b) < 80:
        return None
    c = [x[4] for x in b]; e20, e50, e200, R, A = ema(c, 20), ema(c, 50), ema(c, 200), rsi(c), atr(b); n = len(b) - 1
    price, A4 = c[n], A[n]
    if not A4:
        return None
    atrP, r = A4 / price * 100, R[n]
    d3 = (c[n] / c[n - 3] - 1) * 100
    flush = (r is not None and r < 32) or d3 <= -5
    sH, sL = swings(b[-180:], 3)
    h1H, h1L = swings(h1[-120:], 2) if len(h1) > 40 else ([], [])
    dH, dL = swings(d[-250:], 3) if len(d) > 20 else ([], [])
    sups = [x for x in h1L + sL + dL + [e20[n], e50[n]] if x and x < price]
    S1 = max(sups) if sups else price - 1.5 * A4
    reach = REACH * atrP >= 1.8
    ress = sorted(x for x in h1H + sH + dH if x > price * 1.004)
    cap = max(2.5, REACH * atrP); tgt, tgt_why = None, ('مقاومة سابقة', 'prior resistance')
    for x in ress:
        g = (x / price - 1) * 100
        if 1.8 <= g <= cap:
            tgt = max(x - 0.05 * A4, price * 1.018); break
        if g > cap:
            break
    if not tgt:
        tgt, tgt_why = price * (1 + TARGET / 100), ('هدف 2%', '2% target')
    blocking = next((x for x in ress if (x / price - 1) * 100 < 1.8), None)
    tp = (tgt / price - 1) * 100
    s_stop = S1 - 0.25 * A4; sp = (1 - s_stop / price) * 100
    stop = s_stop if 1.5 <= sp <= 3 else price * 0.97
    sl = (1 - stop / price) * 100
    N = hit = stp = N0 = 0; tot = tot0 = 0.0
    for i in range(max(20, len(b) - 600), len(b)):
        p, x = i - 1, b[i]; o = x[1]
        up, dn = x[2] >= o * (1 + tp / 100), x[3] <= o * (1 - sl / 100)
        res = -sl if dn else tp if up else (x[4] / o - 1) * 100
        N0 += 1; tot0 += res
        f = (R[p] is not None and R[p] < 32) or (p >= 3 and (c[p] / c[p - 3] - 1) * 100 <= -5)
        if f:
            N += 1; tot += res; stp += dn; hit += (up and not dn)
    cost = COST[mk]
    ev = tot / N - cost if N else None; ev0 = tot0 / N0 - cost if N0 else None
    dtr = None
    if len(d) > 60:
        de = ema([x[4] for x in d], 50); dtr = 'up' if d[-1][4] > de[-1] else 'down'
    why, warn = [], []
    if flush:
        why.append(('تشبع بيعي: RSI %d على 4 ساعات' % r, 'Oversold: 4h RSI %d' % r) if r < 32 else
                   (f'هبوط حاد {pc(d3)} في آخر 3 شموع', f'Sharp drop of {pc(d3)} over the last 3 candles'))
    else:
        warn.append((f'لا يوجد هبوط حاد الآن (RSI {r:.0f}، آخر 3 شموع {pc(d3)})؛ الارتداد يحتاج RSI تحت 32 أو هبوط 5%.',
                     f'No sharp drop now (RSI {r:.0f}, last 3 candles {pc(d3)}); a bounce setup needs RSI under 32 or a 5% drop.'))
    if not reach:
        warn.append((f'حركة 2% أكبر من المعتاد لشمعة 4 ساعات هنا (المتوسط {atrP:.2f}%)', f'A 2% move is bigger than a typical 4h candle here (average {atrP:.2f}%)'))
    why.append((f'أقرب دعم {S1:.2f} على بعد {pc((S1 / price - 1) * 100)}', f'Nearest support {S1:.2f}, {pc((S1 / price - 1) * 100)} away'))
    a50 = price > e50[n]
    (why if a50 else warn).append((f"السعر {'فوق' if a50 else 'تحت'} متوسط 50 على 4 ساعات ({pc((price / e50[n] - 1) * 100)})",
                                   f"Price {'above' if a50 else 'below'} the 4h 50 average ({pc((price / e50[n] - 1) * 100)})"))
    if e200[n]:
        a2 = price > e200[n]
        (why if a2 else warn).append((f"السعر {'فوق' if a2 else 'تحت'} متوسط 200 ({pc((price / e200[n] - 1) * 100)})",
                                      f"Price {'above' if a2 else 'below'} the 200 average ({pc((price / e200[n] - 1) * 100)})"))
    if dtr:
        why.append((f"الاتجاه اليومي {'صاعد' if dtr == 'up' else 'هابط'}", f'Daily trend {dtr}'))
    if blocking:
        warn.append((f'مقاومة قريبة عند {blocking:.2f} قبل الهدف؛ قد يتوقف الصعود عندها.', f'Resistance at {blocking:.2f} before the target; the rise may stall there.'))
    if N >= 8 and ev < 0:
        warn.append((f'في تاريخ هذا السهم: {N} حالة هبوط حاد مشابهة، متوسطها {pc(ev)} بعد التكاليف.', f"In this stock's history: {N} similar sharp drops, averaging {pc(ev)} after costs."))
    score = (100 if flush else 0) + (20 if reach else 0) + (ev * 20 if N >= 8 else 0) + (50 - r) / 2 + max(0, -d3)
    rd = lambda v: None if v is None else round(v, 6 if v < 1 else 4)
    return {'id': sym, 'mk': mk, 'ok': bool(flush and reach), 'flush': flush, 'reach': reach, 'score': round(score, 2),
            'price': rd(price), 'buy': rd(price), 'tgt': rd(tgt), 'stop': rd(stop), 'tp': round(tp, 3), 'sl': round(sl, 3), 'rr': round(tp / sl, 3),
            'rsi': round(r, 1), 'd3': round(d3, 2), 'atrP': round(atrP, 3), 'S1': rd(S1), 'N': N, 'N0': N0,
            'pHit': round(hit / N, 3) if N else 0, 'pStop': round(stp / N, 3) if N else 0,
            'ev': None if ev is None else round(ev, 3), 'ev0': None if ev0 is None else round(ev0, 3),
            'trig': rd(c[n - 2] * 0.95), 'last_t': b[n][0], 'tgt_why': tgt_why, 'why': why, 'warn': warn,
            'bars': [[x[0], rd(x[1]), rd(x[2]), rd(x[3]), rd(x[4])] for x in b[-40:]],
            'e20s': [rd(x) for x in e20[-40:]], 'e50s': [rd(x) for x in e50[-40:]]}


def main():
    import yfinance as yf
    uni = [(s, s, 'us') for s in US] + [(c, c + '.SR', 'sa') for c in SA]
    syms = [y for _, y, _ in uni]
    out = {'updated': NOW.strftime('%Y-%m-%dT%H:%MZ'), 'items': [], 'scanned': 0, 'candles': 0, 'failed': []}
    h1 = yf.download(syms, period='60d', interval='1h', group_by='ticker', auto_adjust=False, progress=False, threads=True)
    dd = yf.download(syms, period='1y', interval='1d', group_by='ticker', auto_adjust=False, progress=False, threads=True)
    for c, y, mk in uni:
        try:
            r1 = rows(h1[y]); rd_ = rows(dd[y])
            b = to4h(r1)
            out['candles'] += len(b)
            a = analyse(mk, c, b, [[x[0], x[1], x[2], x[3], x[4]] for x in r1], [[x[0], x[1], x[2], x[3], x[4]] for x in rd_])
            out['scanned'] += 1
            if a:
                a['name'] = [SA[c][0], SA[c][1]] if mk == 'sa' else [US[c], US[c]]
                out['items'].append(a)
        except Exception as e:
            out['failed'].append(f'{c}: {str(e)[:60]}')
    out['items'].sort(key=lambda x: -x['score'])
    out['items'] = out['items'][:30]
    os.makedirs(ROOT, exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'ext_radar.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print('ext radar', out['scanned'], 'scanned,', sum(1 for x in out['items'] if x['ok']), 'setups,', len(out['failed']), 'failed')


if __name__ == '__main__':
    main()
