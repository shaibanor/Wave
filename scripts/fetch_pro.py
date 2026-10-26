#!/usr/bin/env python3
"""Fetch market data for the advanced section into pro/ (one JSON file per asset)."""
import json, os, time, urllib.request, urllib.error, datetime as dt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pro')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
SA = ['2222', '1120', '1211', '1180', '7010', '2010', '2082', '4013', '1010', '1150']
CX = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'BNB': 'BNBUSDT', 'XRP': 'XRPUSDT', 'SOL': 'SOLUSDT',
      'TRX': 'TRXUSDT', 'DOGE': 'DOGEUSDT', 'ZEC': 'ZECUSDT', 'LINK': 'LINKUSDT', 'ADA': 'ADAUSDT'}
CX_TF = {'1h': 500, '4h': 500, '1d': 1000, '1w': 400, '1M': 150}

def get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # network / rate limit
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f'{url}: {last}')

def num(x, nd):
    return None if x is None else round(float(x), nd)

def yahoo(sym, interval, rng):
    for host in ('query1', 'query2'):
        try:
            d = get(f'https://{host}.finance.yahoo.com/v8/finance/chart/{sym}?interval={interval}&range={rng}&includePrePost=false')
            res = d['chart']['result'][0]
            break
        except Exception as e:
            err = e
    else:
        raise RuntimeError(err)
    ts = res.get('timestamp') or []
    q = res['indicators']['quote'][0]
    out = []
    for i, t in enumerate(ts):
        o, h, l, c, v = (q[k][i] for k in ('open', 'high', 'low', 'close', 'volume'))
        if None in (o, h, l, c) or min(o, h, l, c) <= 0:
            continue
        day = (dt.datetime.utcfromtimestamp(t) + dt.timedelta(hours=3)).date()
        t0 = int(dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc).timestamp())
        h, l = max(h, o, c), min(l, o, c)
        out.append([t0, num(o, 3), num(h, 3), num(l, 3), num(c, 3), int(v or 0)])
    dedup = {}
    for r in out:
        dedup[r[0]] = r
    return [dedup[k] for k in sorted(dedup)], res.get('meta', {})

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
    for c in SA:
        try:
            d, meta = yahoo(f'{c}.SR', '1d', '2y')
            m, _ = yahoo(f'{c}.SR', '1mo', 'max')
            if len(d) < 60:
                raise RuntimeError('too few daily rows')
            write(f'{ROOT}/sa/{c}.json', {'id': c, 'updated': now, 'cur': meta.get('currency', 'SAR'), 'd': d, 'm': m})
            status['sa'][c] = {'ok': True, 'last': dt.datetime.utcfromtimestamp(d[-1][0]).strftime('%Y-%m-%d'), 'n': len(d)}
        except Exception as e:
            status['sa'][c] = {'ok': False, 'err': str(e)[:160]}
        time.sleep(1.5)
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
