#!/usr/bin/env python3
"""Fetch market data for the advanced section into pro/ (one JSON file per asset)."""
import json, os, time, urllib.request, urllib.error, datetime as dt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pro')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
SA = ['2222', '1120', '1211', '1180', '7010', '2010', '2082', '4013', '1010', '1150']
CX = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'BNB': 'BNBUSDT', 'XRP': 'XRPUSDT', 'SOL': 'SOLUSDT',
      'TRX': 'TRXUSDT', 'DOGE': 'DOGEUSDT', 'ZEC': 'ZECUSDT', 'LINK': 'LINKUSDT', 'ADA': 'ADAUSDT'}
CX_TF = {'1h': 500, '4h': 500, '1d': 1000, '1w': 400, '1M': 150}

def get(url, tries=2):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # network / rate limit
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f'{url}: {last}')

def num(x, nd):
    return None if x is None else round(float(x), nd)

def yahoo_all():
    """Daily (2y) and monthly (max) bars for all Saudi tickers via yfinance."""
    import yfinance as yf
    out = {}
    for c in SA:
        try:
            t = yf.Ticker(f'{c}.SR')
            res = {}
            for key, kw in (('d', dict(period='2y', interval='1d')), ('m', dict(period='max', interval='1mo'))):
                df = t.history(auto_adjust=False, actions=False, **kw)
                rows = []
                for idx, r in df.iterrows():
                    o, h, l, cl, v = (r.get(k) for k in ('Open', 'High', 'Low', 'Close', 'Volume'))
                    if any(x is None or x != x or x <= 0 for x in (o, h, l, cl)):
                        continue
                    day = idx.date()
                    t0 = int(dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc).timestamp())
                    rows.append([t0, num(o, 3), num(max(h, o, cl), 3), num(min(l, o, cl), 3), num(cl, 3), int(v if v == v else 0)])
                res[key] = rows
            out[c] = res
        except Exception as e:
            out[c] = {'err': str(e)[:160]}
        time.sleep(1)
    return out

def binance(sym, tf, limit):
    for base in ('https://data-api.binance.vision', 'https://api.binance.com', 'https://api1.binance.com'):
        try:
            rows = get(f'{base}/api/v3/klines?symbol={sym}&interval={tf}&limit={limit}', tries=2)
            return [[int(r[0]) // 1000, float(r[1]), float(r[2]), float(r[3]), float(r[4]), round(float(r[5]), 4)] for r in rows]
        except Exception as e:
            err = e
    raise RuntimeError(err)

def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    s = json.dumps(obj, separators=(',', ':'))
    old = open(path).read() if os.path.exists(path) else None
    if old != s:
        open(path, 'w').write(s)

def main():
    now = dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')
    status = {'updated': now, 'sa': {}, 'cx': {}}
    try:
        allsa = yahoo_all()
    except Exception as e:
        allsa = {c: {'err': str(e)[:160]} for c in SA}
    for c in SA:
        r = allsa.get(c, {})
        d, m = r.get('d') or [], r.get('m') or []
        if len(d) >= 60:
            write(f'{ROOT}/sa/{c}.json', {'id': c, 'updated': now, 'cur': 'SAR', 'd': d, 'm': m})
            status['sa'][c] = {'ok': True, 'last': dt.datetime.utcfromtimestamp(d[-1][0]).strftime('%Y-%m-%d'), 'n': len(d), 'nm': len(m)}
        else:
            status['sa'][c] = {'ok': False, 'err': r.get('err', f'only {len(d)} daily rows')}
    for k, sym in CX.items():
        try:
            obj = {'id': k, 'updated': now}
            for tf, lim in CX_TF.items():
                obj[tf] = binance(sym, tf, lim)
            write(f'{ROOT}/cx/{k}.json', obj)
            status['cx'][k] = {'ok': True, 'n': len(obj['1d'])}
        except Exception as e:
            status['cx'][k] = {'ok': False, 'err': str(e)[:160]}
    write(f'{ROOT}/status.json', status)
    print(json.dumps(status, indent=1))

if __name__ == '__main__':
    main()
