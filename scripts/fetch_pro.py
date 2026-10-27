#!/usr/bin/env python3
"""Market data for the site: pro/<kind>/<id>.json (history) and pro/live/<id>.json (intraday).
Usage: fetch_pro.py            full refresh (stocks D/M/1h/4h + crypto snapshot)
       fetch_pro.py --intraday  5-minute bars of the latest session for stocks only
"""
import json, os, sys, time, urllib.request, datetime as dt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pro')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}
SA = ['8311', '1120', '4340', '2222', '1211', '1180', '7010', '2010', '2082', '4013', '1010', '1150']
US = ['GOOGL', 'META', 'AVGO', 'TSM', 'JPM', 'LLY', 'V']
STOCKS = [(c, f'{c}.SR', 'sa') for c in SA] + [(c, c, 'us') for c in US]
CX = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'BNB': 'BNBUSDT', 'XRP': 'XRPUSDT', 'SOL': 'SOLUSDT',
      'TRX': 'TRXUSDT', 'DOGE': 'DOGEUSDT', 'ZEC': 'ZECUSDT', 'LINK': 'LINKUSDT', 'ADA': 'ADAUSDT'}
CX_TF = {'1h': 500, '4h': 500, '1d': 1000, '1w': 400, '1M': 150}
NOW = dt.datetime.now(dt.timezone.utc)


def r3(x, nd=4):
    return round(float(x), nd)


def ok(o, h, l, c):
    return all(x is not None and x == x and x > 0 for x in (o, h, l, c))


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    s = json.dumps(obj, separators=(',', ':'))
    if not os.path.exists(path) or open(path).read() != s:
        open(path, 'w').write(s)


def frame_rows(df, daily):
    rows = []
    for idx, r in df.iterrows():
        o, h, l, c, v = (r.get(k) for k in ('Open', 'High', 'Low', 'Close', 'Volume'))
        if not ok(o, h, l, c):
            continue
        if daily:
            d = idx.date()
            t = int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())
        else:
            t = int(idx.timestamp())
        rows.append([t, r3(o), r3(max(h, o, c)), r3(min(l, o, c)), r3(c), int(v) if v == v else 0, idx.date().isoformat()])
    return rows


def to4h(rows1h):
    """Group 1h bars into 4h bars, four consecutive bars per session day."""
    out, cur, day, k = [], None, None, 0
    for t, o, h, l, c, v, d in rows1h:
        if d != day:
            day, k = d, 0
        if k % 4 == 0:
            if cur:
                out.append(cur)
            cur = [t, o, h, l, c, v]
        else:
            cur[2], cur[3], cur[4], cur[5] = max(cur[2], h), min(cur[3], l), c, cur[5] + v
        k += 1
    if cur:
        out.append(cur)
    return out


def stocks_full(status):
    import yfinance as yf
    for c, sym, kind in STOCKS:
        try:
            t = yf.Ticker(sym)
            d = frame_rows(t.history(period='2y', interval='1d', auto_adjust=False, actions=False), True)
            m = frame_rows(t.history(period='max', interval='1mo', auto_adjust=False, actions=False), True)
            obj = {'id': c, 'updated': NOW.strftime('%Y-%m-%dT%H:%MZ'), 'd': [x[:6] for x in d], 'm': [x[:6] for x in m]}
            try:
                h1 = frame_rows(t.history(period='730d', interval='1h', auto_adjust=False, actions=False), False)
                if len(h1) >= 60:
                    obj['1h'] = [x[:6] for x in h1[-500:]]
                    obj['4h'] = to4h(h1)[-500:]
            except Exception as e:
                status.setdefault('notes', []).append(f'{c} 1h: {str(e)[:80]}')
            if len(d) < 60:
                raise RuntimeError(f'only {len(d)} daily rows')
            write(f'{ROOT}/{kind}/{c}.json', obj)
            status['stocks'][c] = {'ok': True, 'last': d[-1][6], 'n': len(d), 'h1': len(obj.get('1h', []))}
        except Exception as e:
            status['stocks'][c] = {'ok': False, 'err': str(e)[:160]}
        time.sleep(0.8)


def stocks_live(status):
    import yfinance as yf
    for c, sym, kind in STOCKS:
        try:
            t = yf.Ticker(sym)
            df = t.history(period='5d', interval='5m', auto_adjust=False, actions=False)
            rows = frame_rows(df, False)
            if not rows:
                raise RuntimeError('no intraday rows')
            last_day = rows[-1][6]
            sess = [r for r in rows if r[6] == last_day]
            prev_days = [r for r in rows if r[6] < last_day]
            daily = frame_rows(t.history(period='10d', interval='1d', auto_adjust=False, actions=False), True)
            prev = next((x[4] for x in reversed(daily) if x[6] < last_day), prev_days[-1][4] if prev_days else sess[0][1])
            write(f'{ROOT}/live/{c}.json', {'id': c, 'updated': NOW.strftime('%Y-%m-%dT%H:%MZ'), 'day': last_day,
                                            'prev': prev, 'bars': [[r[0], r[4]] for r in sess]})
            status['live'][c] = {'ok': True, 'day': last_day, 'n': len(sess)}
        except Exception as e:
            status['live'][c] = {'ok': False, 'err': str(e)[:160]}
        time.sleep(0.5)


def get(url, tries=2):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f'{url}: {last}')


def crypto(status):
    for k, sym in CX.items():
        try:
            obj = {'id': k, 'updated': NOW.strftime('%Y-%m-%dT%H:%MZ')}
            for tf, lim in CX_TF.items():
                for base in ('https://data-api.binance.vision', 'https://api.binance.com'):
                    try:
                        rows = get(f'{base}/api/v3/klines?symbol={sym}&interval={tf}&limit={lim}')
                        obj[tf] = [[int(r[0]) // 1000, float(r[1]), float(r[2]), float(r[3]), float(r[4]), round(float(r[5]), 4)] for r in rows]
                        break
                    except Exception as e:
                        err = e
                else:
                    raise RuntimeError(err)
            write(f'{ROOT}/cx/{k}.json', obj)
            status['cx'][k] = {'ok': True, 'n': len(obj['1d'])}
        except Exception as e:
            status['cx'][k] = {'ok': False, 'err': str(e)[:160]}


def main():
    live = '--intraday' in sys.argv
    status = {'updated': NOW.strftime('%Y-%m-%dT%H:%MZ'), 'stocks': {}, 'live': {}, 'cx': {}}
    try:
        import yfinance
        status['yf'] = yfinance.__version__
    except Exception as e:
        status['yf'] = 'missing: ' + str(e)[:80]
    if live:
        stocks_live(status)
        write(f'{ROOT}/live_status.json', status)
    else:
        stocks_full(status)
        stocks_live(status)
        crypto(status)
        write(f'{ROOT}/status.json', status)
    print(json.dumps(status, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
