"""Quick paper desk: short "Up or Down" crypto markets, paper only (no real orders, no keys).

Reads public quotes of the short crypto "Up or Down" markets on Polymarket (BTC, ETH, SOL, XRP) and
the spot price from Coinbase, and runs a paper book with the two-sided method:
  - complete sets: when the cheapest Up + the cheapest Down (with the assumed fee) cost less than $1,
    buy both; one of them always pays $1 at settlement,
  - matching: when one side is held alone, buy the other side only if the pair still costs < $1,
  - directional residual: buy one side only when its price is clearly below our own fair probability
    (a simple volatility model on the spot price), in small clips.
Never sells; every position is held to settlement. Fills are taken at the best ask, limited to the
size shown at that level. The fee rate is an assumption (FEE below), shown in the report.

The open state (equity + open windows) is kept in the Actions cache between runs; the report is
encrypted with the vault public key (vault/key.json), so only the owner's vault code opens it."""
import json, math, os, sys, time, urllib.request, urllib.error, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
STATE = os.environ.get('QUICK_STATE', os.path.join(ROOT, '.quick', 'state.json'))
OUT = os.path.join(ROOT, 'vault', 'quick.json')
ASSETS = [('btc', 'BTC-USD', 'BTC'), ('eth', 'ETH-USD', 'ETH'), ('sol', 'SOL-USD', 'SOL'), ('xrp', 'XRP-USD', 'XRP')]
EQ0 = 10000.0          # starting paper equity ($)
CLIP = 0.006           # one buy = 0.6% of equity
MAX_MKT = 0.03         # at most 3% of equity per market window
FEE = 0.01             # assumed taker fee: 1% of the amount paid (assumption, shown in the report)
SET_MAX = 0.985        # a pair (Up + Down, fees included) must cost at most this
EDGE = 0.07            # one side alone only when it is this far below our fair probability
T_MIN, T_EDGE = 20, 60 # no buys in the last 20 s; no one-sided buys in the last 60 s
RUN_SEC = int(os.environ.get('QUICK_RUN_SEC', '1380'))
POLL = 15


def get(url, timeout=12):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (paper desk)', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def now_ts():
    return int(time.time())


class Desk:
    def __init__(self):
        try:
            self.s = json.load(open(STATE, encoding='utf-8'))
        except Exception:
            self.s = None
        if not self.s:
            self.s = {'since': now_ts(), 'eq0': EQ0, 'cash': EQ0, 'open': {}, 'trades': [], 'settled': [], 'trace': [], 'edge': [],
                      'curve': [], 'events': [], 'runs': 0, 'polls': 0, 'nomkt': 0, 'kind': None}
            self.ev('بداية دفتر جديد برأس مال ورقي %d$' % EQ0)
        self.s['runs'] += 1
        self.mkt = {}          # slug -> market info (cached)
        self.vol = {}          # asset -> (sigma per sqrt(second), at)
        self.start = {}        # window key -> start price

    # ---------- log helpers ----------
    def ev(self, t, lv='info'):
        self.s['events'] = (self.s['events'] + [{'t': now_ts(), 'm': t, 'lv': lv}])[-80:]

    def tr(self, k, m):
        self.s['trace'] = (self.s['trace'] + [{'t': now_ts(), 'k': k, 'm': m}])[-160:]

    def equity(self, marks=None):
        val = self.s['cash']
        for w in self.s['open'].values():
            if marks and w['key'] in marks:
                pu = marks[w['key']]; val += w['up'] * pu + w['dn'] * (1 - pu)
            else:
                val += w['cost']          # unknown mark: carry at cost
        return val

    # ---------- market discovery ----------
    def market(self, a, span):
        t = now_ts(); st = t - t % span
        slug = f"{a}-updown-{span // 60}m-{st}"
        if slug in self.mkt:
            return self.mkt[slug]
        info = None
        try:
            ev = get('https://gamma-api.polymarket.com/events?slug=' + slug)
            if ev:
                m = ev[0]['markets'][0]
                toks = json.loads(m['clobTokenIds']) if isinstance(m['clobTokenIds'], str) else m['clobTokenIds']
                outs = json.loads(m['outcomes']) if isinstance(m['outcomes'], str) else m['outcomes']
                up = toks[[o.lower() for o in outs].index('up')]; dn = toks[[o.lower() for o in outs].index('down')]
                info = {'slug': slug, 'start': st, 'end': st + span, 'up': up, 'dn': dn, 'q': m.get('question') or ev[0].get('title', slug), 'span': span}
        except Exception as e:
            info = None
        self.mkt[slug] = info
        return info

    def book(self, tok):
        b = get('https://clob.polymarket.com/book?token_id=' + tok)
        asks = [(float(x['price']), float(x['size'])) for x in b.get('asks', [])]
        bids = [(float(x['price']), float(x['size'])) for x in b.get('bids', [])]
        a = min(asks) if asks else None; bb = max(bids) if bids else None
        return a, bb

    # ---------- fair probability ----------
    def spot(self, prod):
        return float(get(f'https://api.exchange.coinbase.com/products/{prod}/ticker')['price'])

    def sigma(self, prod):
        v = self.vol.get(prod)
        if v and now_ts() - v[1] < 600:
            return v[0]
        c = get(f'https://api.exchange.coinbase.com/products/{prod}/candles?granularity=60')
        cl = [x[4] for x in sorted(c, key=lambda x: x[0])][-90:]
        r = [math.log(cl[i] / cl[i - 1]) for i in range(1, len(cl)) if cl[i - 1] > 0]
        sd = (sum((x - sum(r) / len(r)) ** 2 for x in r) / max(1, len(r) - 1)) ** 0.5 if len(r) > 5 else 0.001
        s = max(sd, 1e-5) / math.sqrt(60)
        self.vol[prod] = (s, now_ts())
        return s

    def open_price(self, prod, st):
        k = f'{prod}:{st}'
        if k in self.start:
            return self.start[k]
        p = None
        try:
            c = get(f'https://api.exchange.coinbase.com/products/{prod}/candles?granularity=60&start={st}&end={st + 120}')
            c = sorted(c, key=lambda x: x[0])
            hit = [x for x in c if x[0] == st]
            p = (hit[0] if hit else c[0])[3] if c else None
        except Exception:
            p = None
        self.start[k] = p
        return p

    # ---------- buying ----------
    def buy(self, w, side, price, size_avail, usd, why):
        if price is None or price <= 0 or price >= 1:
            return 0
        eq = self.equity()
        room = MAX_MKT * eq - w['cost']
        usd = min(usd, room, self.s['cash'] * 0.9)
        q = min(usd / (price * (1 + FEE)), size_avail)
        q = math.floor(q * 100) / 100
        if q < 1:
            return 0
        paid = q * price; fee = paid * FEE
        self.s['cash'] -= paid + fee
        w[side] += q; w['cost'] += paid + fee; w['c' + side] += paid + fee; w['n'] += 1
        self.s['trades'] = (self.s['trades'] + [{'t': now_ts(), 'a': w['a'], 'w': w['key'], 'side': side, 'p': round(price, 3), 'q': q,
                                                  'usd': round(paid + fee, 2), 'why': why}])[-500:]
        self.tr('order', f"{w['A']} {'UP' if side == 'up' else 'DN'} @ {price:.2f} ×{q:g} · {why}")
        return q

    def step(self, a, prod, A, span):
        m = self.market(a, span)
        if not m:
            return None
        t = now_ts(); left = m['end'] - t
        key = m['slug']
        w = self.s['open'].get(key)
        if not w:
            w = {'key': key, 'a': a, 'A': A, 'q': m['q'], 'start': m['start'], 'end': m['end'], 'prod': prod, 'up': 0.0, 'dn': 0.0,
                 'cost': 0.0, 'cup': 0.0, 'cdn': 0.0, 'n': 0, 'p0': None}
        aU, bU = self.book(m['up']); aD, bD = self.book(m['dn'])
        S = self.spot(prod); S0 = w['p0'] or self.open_price(prod, m['start'])
        if S0:
            w['p0'] = S0
        sg = self.sigma(prod)
        pu = ncdf(math.log(S / S0) / (sg * math.sqrt(max(left, 1)))) if S0 and left > 0 else None
        mid = ((aU[0] if aU else 1) + (bU[0] if bU else 0)) / 2
        if pu is not None:
            self.s['edge'] = (self.s['edge'] + [[t, A, round(pu, 3), round(mid, 3), round(aU[0], 3) if aU else None, round(aD[0], 3) if aD else None]])[-400:]
        self.tr('feed', f"{A} spot {S:,.4g} · fair P(UP) {pu:.2f}" if pu is not None else f"{A} spot {S:,.4g}")
        if left <= T_MIN or not aU or not aD:
            if w['n']:
                self.s['open'][key] = w
            return pu, mid, key
        clip = CLIP * self.equity()
        # 1) complete sets
        pair = (aU[0] + aD[0]) * (1 + FEE)
        if pair <= SET_MAX:
            self.tr('edge', f"{A} pair {aU[0]:.2f}+{aD[0]:.2f} = {pair:.3f} < 1 → both")
            q = min(aU[1], aD[1], clip / pair, max(0.0, MAX_MKT * self.equity() - w['cost']) / pair)
            qu = self.buy(w, 'up', aU[0], q, q * aU[0] * (1 + FEE) + 0.01, 'زوج كامل')
            if qu: self.buy(w, 'dn', aD[0], qu, qu * aD[0] * (1 + FEE) + 0.01, 'زوج كامل')
        # 2) match a lone side when the pair still pays
        if w['up'] > w['dn'] + 1 and w['up']:
            avg = w['cup'] / w['up']
            if avg + aD[0] * (1 + FEE) <= SET_MAX:
                self.buy(w, 'dn', aD[0], w['up'] - w['dn'], (w['up'] - w['dn']) * aD[0] * (1 + FEE), 'مطابقة الجهة الثانية')
        elif w['dn'] > w['up'] + 1 and w['dn']:
            avg = w['cdn'] / w['dn']
            if avg + aU[0] * (1 + FEE) <= SET_MAX:
                self.buy(w, 'up', aU[0], w['dn'] - w['up'], (w['dn'] - w['up']) * aU[0] * (1 + FEE), 'مطابقة الجهة الثانية')
        # 3) directional residual
        if pu is not None and left > T_EDGE:
            if pu - aU[0] >= EDGE and w['up'] - w['dn'] < 3 * clip:
                self.tr('edge', f"{A} UP {aU[0]:.2f} below fair {pu:.2f}")
                self.buy(w, 'up', aU[0], aU[1], clip / 2, f'أرخص من العادل {pu:.2f}')
            elif (1 - pu) - aD[0] >= EDGE and w['dn'] - w['up'] < 3 * clip:
                self.tr('edge', f"{A} DOWN {aD[0]:.2f} below fair {1 - pu:.2f}")
                self.buy(w, 'dn', aD[0], aD[1], clip / 2, f'أرخص من العادل {1 - pu:.2f}')
        if w['n']:
            self.s['open'][key] = w
        return pu, mid, key

    # ---------- settlement ----------
    def settle(self):
        t = now_ts()
        for key, w in list(self.s['open'].items()):
            if t < w['end'] + 60:
                continue
            win = None; src = None
            try:
                ev = get('https://gamma-api.polymarket.com/events?slug=' + key)
                m = ev[0]['markets'][0] if ev else None
                if m and m.get('closed'):
                    op = json.loads(m['outcomePrices']) if isinstance(m['outcomePrices'], str) else m['outcomePrices']
                    outs = json.loads(m['outcomes']) if isinstance(m['outcomes'], str) else m['outcomes']
                    lo = [o.lower() for o in outs]
                    if float(op[lo.index('up')]) >= 0.99: win, src = 'up', 'المنصة'
                    elif float(op[lo.index('down')]) >= 0.99: win, src = 'dn', 'المنصة'
            except Exception:
                pass
            if win is None and t > w['end'] + 900:
                try:
                    c = get(f"https://api.exchange.coinbase.com/products/{w['prod']}/candles?granularity=60&start={w['end'] - 120}&end={w['end'] + 60}")
                    c = sorted(c, key=lambda x: x[0]); e = [x for x in c if x[0] == w['end'] - 60]
                    pe = (e[0] if e else c[-1])[4]
                    if w.get('p0'):
                        win, src = ('up' if pe >= w['p0'] else 'dn'), 'سعر Coinbase (تقريبي)'
                except Exception:
                    pass
            if win is None:
                if t > w['end'] + 6 * 3600:
                    self.s['cash'] += w['cost']; self.ev(f"أُلغيت نافذة {w['A']} دون تسوية وأُعيدت تكلفتها", 'warn'); del self.s['open'][key]
                continue
            pay = w[win] * 1.0
            pnl = pay - w['cost']
            self.s['cash'] += pay
            pairs = min(w['up'], w['dn'])
            self.s['settled'] = (self.s['settled'] + [{'t': w['end'], 'a': w['A'], 'q': w['q'], 'win': win, 'src': src, 'up': round(w['up'], 2), 'dn': round(w['dn'], 2),
                                                        'cost': round(w['cost'], 2), 'pay': round(pay, 2), 'pnl': round(pnl, 2), 'n': w['n'],
                                                        'pairs': round(pairs, 2), 'vwap': round(w['cost'] / max(w['up'], w['dn'], 1e-9), 4) if pairs else None}])[-400:]
            self.tr('payout', f"{w['A']} {'UP' if win == 'up' else 'DOWN'} won · pays ${pay:,.2f} · pnl {pnl:+.2f}")
            del self.s['open'][key]

    # ---------- main loop ----------
    def run(self):
        t0 = time.time(); span_ok = None
        while time.time() - t0 < RUN_SEC:
            marks = {}; seen = 0
            for a, prod, A in ASSETS:
                for span in ((span_ok,) if span_ok else (300, 900)):
                    try:
                        r = self.step(a, prod, A, span)
                    except urllib.error.HTTPError as e:
                        self.ev(f'{A}: خطأ {e.code} من المصدر', 'warn'); r = None
                    except Exception as e:
                        self.ev(f'{A}: {type(e).__name__}', 'warn'); r = None
                    if r:
                        seen += 1; span_ok = span_ok or span
                        if r[0] is not None: marks[r[2]] = r[0]
                        break
            if not seen:
                self.s['nomkt'] += 1
                if self.s['nomkt'] % 20 == 1: self.ev('لم تُعثر على أسواق قصيرة متاحة الآن', 'warn')
            self.s['kind'] = f'{span_ok // 60} دقائق' if span_ok else self.s.get('kind')
            try: self.settle()
            except Exception as e: self.ev('التسوية: ' + type(e).__name__, 'warn')
            self.s['polls'] += 1
            if self.s['polls'] % 4 == 0:
                self.s['curve'] = (self.s['curve'] + [[now_ts(), round(self.equity(marks), 2)]])[-600:]
            time.sleep(POLL)
        self.settle()

    def report(self):
        S = self.s; st = S['settled']; tr = S['trades']
        hrs = max(1e-9, (now_ts() - S['since']) / 3600)
        wins = sum(1 for x in st if x['pnl'] > 0)
        both = [x for x in st if x['up'] > 0 and x['dn'] > 0]
        matched = sum(x['pairs'] for x in st); held = sum(max(x['up'], x['dn']) for x in st)
        vw = [x['vwap'] for x in st if x.get('vwap')]
        return {'at': now_ts(), 'since': S['since'], 'kind': S.get('kind'), 'eq0': S['eq0'], 'equity': round(self.equity(), 2), 'cash': round(S['cash'], 2),
                'pnl': round(self.equity() - S['eq0'], 2), 'trades': len(tr), 'trades_hr': round(len(tr) / hrs, 1), 'windows': len(st),
                'win_rate': round(wins / len(st) * 100, 1) if st else None, 'both_sided': round(len(both) / len(st) * 100, 1) if st else None,
                'matched_pct': round(matched / held * 100, 1) if held else None, 'vwap_pair': round(sorted(vw)[len(vw) // 2], 4) if vw else None,
                'open': list(S['open'].values()), 'recent': tr[-60:], 'settled': st[-120:], 'trace': S['trace'][-80:], 'edge': S['edge'][-300:],
                'curve': S['curve'][-400:], 'events': S['events'][-30:], 'runs': S['runs'], 'polls': S['polls'],
                'rules': {'fee': FEE, 'set_max': SET_MAX, 'edge': EDGE, 'clip': CLIP, 'max_mkt': MAX_MKT, 'eq0': EQ0},
                'by_asset': {A: {'n': len([x for x in st if x['a'] == A]), 'pnl': round(sum(x['pnl'] for x in st if x['a'] == A), 2)} for _, _, A in ASSETS}}


def encrypt(obj):
    import base64
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
    d = Desk()
    if '--once' in sys.argv:
        global RUN_SEC
        RUN_SEC = 1
    d.run()
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(d.s, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False)
    rep = d.report()
    json.dump(encrypt(rep), open(OUT, 'w'))
    # public heartbeat only: no amounts, no trades
    json.dump({'at': rep['at'], 'live': bool(d.s.get('kind')), 'kind': rep['kind'], 'runs': rep['runs']},
              open(os.path.join(ROOT, 'pro', 'quick_status.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(json.dumps({k: rep[k] for k in ('equity', 'pnl', 'trades', 'windows', 'win_rate', 'kind')}, ensure_ascii=False))
    print('events:', [e['m'] for e in rep['events'][-5:]])


if __name__ == '__main__':
    main()
