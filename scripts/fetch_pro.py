#!/usr/bin/env python3
"""Market data for the site: pro/<kind>/<id>.json (history) and pro/live/<id>.json (intraday).
Usage: fetch_pro.py            full refresh (stocks D/M/1h/4h + crypto snapshot)
       fetch_pro.py --intraday  5-minute bars of the latest session for stocks only
"""
import json, os, sys, time, urllib.request, datetime as dt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pro')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}
SA = ['8311', '1120', '4340', '2222', '1211', '1180', '7010', '2010', '2082', '4013', '1010', '1150', '1325']
US = ['GOOGL', 'META', 'AVGO', 'TSM', 'JPM', 'LLY', 'V']
SA_X = ['2280', '4190', '1060', '5110', '2050', '1050', '2020', '4280']
US_X = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'TSLA', 'NFLX', 'AMD', 'COST', 'BRK-B', 'UNH', 'XOM', 'WMT', 'SPY', 'QQQ', 'GLD']
IX = [('TASI', '^TASI.SR'), ('DJI', '^DJI'), ('SPX', '^GSPC'), ('NDX', '^NDX'), ('GOLD', 'GC=F'), ('SILVER', 'SI=F'),
      ('BRENT', 'BZ=F'), ('US10Y', '^TNX'), ('DXY', 'DX-Y.NYB')]
STOCKS = [(c, f'{c}.SR', 'sa') for c in SA] + [(c, c, 'us') for c in US] + [(c, sym, 'ix') for c, sym in IX]
EXTRA = [(c, f'{c}.SR', 'sa') for c in SA_X] + [(c, c, 'us') for c in US_X]
CX = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'BNB': 'BNBUSDT', 'XRP': 'XRPUSDT', 'SOL': 'SOLUSDT',
      'TRX': 'TRXUSDT', 'DOGE': 'DOGEUSDT', 'ZEC': 'ZECUSDT', 'LINK': 'LINKUSDT', 'ADA': 'ADAUSDT',
      'AVAX': 'AVAXUSDT', 'DOT': 'DOTUSDT', 'LTC': 'LTCUSDT', 'BCH': 'BCHUSDT', 'NEAR': 'NEARUSDT'}
CX_TF = {'1h': 500, '4h': 1000, '1d': 1000, '1w': 400, '1M': 150}
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


def daily_from(rows):
    out = {}
    for t, o, h, l, c, v, d in rows:
        if d not in out:
            y, mo, da = map(int, d.split('-'))
            out[d] = [int(dt.datetime(y, mo, da, tzinfo=dt.timezone.utc).timestamp()), o, h, l, c, v, d]
        else:
            x = out[d]; x[2], x[3], x[4], x[5] = max(x[2], h), min(x[3], l), c, x[5] + v
    return [out[k] for k in sorted(out)]


def monthly_from(rows):
    out = {}
    for t, o, h, l, c, v, *_ in rows:
        k = dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%Y-%m')
        if k not in out:
            y, mo = map(int, k.split('-'))
            out[k] = [int(dt.datetime(y, mo, 1, tzinfo=dt.timezone.utc).timestamp()), o, h, l, c, v]
        else:
            x = out[k]; x[2], x[3], x[4], x[5] = max(x[2], h), min(x[3], l), c, x[5] + v
    return [out[k] for k in sorted(out)]


def stocks_full(status):
    import yfinance as yf
    for c, sym, kind in STOCKS + EXTRA:
        extra = (c, sym, kind) in EXTRA
        try:
            t = yf.Ticker(sym)
            d = frame_rows(t.history(period='5y', interval='1d', auto_adjust=False, actions=False), True)
            if len(d) < 60:
                start = (NOW - dt.timedelta(days=1826)).date().isoformat()
                d = frame_rows(t.history(start=start, interval='1d', auto_adjust=False, actions=False), True) or d
            m = frame_rows(t.history(period='max', interval='1mo', auto_adjust=False, actions=False), True)
            h1 = []
            obj = {'id': c, 'updated': NOW.strftime('%Y-%m-%dT%H:%MZ'), 'd': [x[:6] for x in d], 'm': [x[:6] for x in m]}
            try:
                h1 = frame_rows(t.history(period='730d', interval='1h', auto_adjust=False, actions=False), False)
                if len(h1) >= 60:
                    obj['1h'] = [x[:6] for x in h1[-1500:]]
                    obj['4h'] = to4h(h1)[-800:]
            except StopIteration:
                pass
            except Exception as e:
                status.setdefault('notes', []).append(f'{c} 1h: {str(e)[:80]}')
            if len(d) < 60 and len(obj.get('1h', [])) >= 60:
                d = daily_from(h1)
                obj['d'] = [x[:6] for x in d]
            elif d and h1:
                # Yahoo sometimes publishes the latest daily bar late; rebuild finished sessions from hourly bars.
                last = d[-1][6]
                close_h = 13 if kind == 'sa' else 21
                fresh = [r for r in daily_from([x for x in h1 if dt.datetime.fromtimestamp(x[0], dt.timezone.utc).date().isoformat() > last])
                         if r[6] < NOW.date().isoformat() or NOW.hour >= close_h]
                if fresh:
                    d = d + fresh
                    obj['d'] = [x[:6] for x in d]
                    status.setdefault('notes', []).append(f'{c}: {len(fresh)} daily bar(s) rebuilt from 1h')
            if len(obj['m']) < 12 and len(d) >= 60:
                obj['m'] = monthly_from(d)
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


NEWS_Q = {
    '8311': ('عناية للتأمين', None), '1120': ('مصرف الراجحي', None), '4340': ('الراجحي ريت', None), '2222': ('أرامكو السعودية سهم', None),
    '1211': ('معادن السعودية', None), '1180': ('البنك الأهلي السعودي', None), '7010': ('اس تي سي السعودية سهم', None), '2010': ('سابك', None),
    '2082': ('أكوا باور', None), '4013': ('سليمان الحبيب الطبية', None), '1010': ('بنك الرياض', None), '1150': ('مصرف الإنماء', None), '1325': ('حديد وطني', None),
    'GOOGL': ('سهم ألفابت جوجل', 'Alphabet stock'), 'META': ('سهم ميتا', 'Meta Platforms stock'), 'AVGO': ('سهم برودكوم', 'Broadcom stock'),
    'TSM': ('سهم تايوان لأشباه الموصلات', 'TSMC stock'), 'JPM': ('جي بي مورغان', 'JPMorgan stock'), 'LLY': ('إيلي ليلي', 'Eli Lilly stock'), 'V': ('فيزا سهم', 'Visa stock'),
    'TASI': ('مؤشر تاسي السوق السعودية', None), 'DJI': ('مؤشر داو جونز', 'Dow Jones'), 'SPX': ('مؤشر اس اند بي 500', 'S&P 500'), 'NDX': ('مؤشر ناسداك', 'Nasdaq 100'),
    'GOLD': ('أسعار الذهب', 'gold price'), 'SILVER': ('أسعار الفضة', 'silver price'), 'BRENT': ('نفط برنت', 'Brent crude'), 'US10Y': ('عائد السندات الأمريكية', 'Treasury yields'),
    'DXY': ('مؤشر الدولار', 'dollar index'), 'BTC': ('بيتكوين', 'Bitcoin'), 'ETH': ('إيثريوم', 'Ethereum'), 'XRP': ('ريبل XRP', 'XRP Ripple'), 'BNB': ('عملة بينانس BNB', 'BNB coin'),
    'SOL': ('سولانا', 'Solana crypto'), 'TRX': ('ترون TRX', 'TRON TRX'), 'DOGE': ('دوجكوين', 'Dogecoin'), 'ZEC': ('زي كاش', 'Zcash'), 'LINK': ('تشين لينك', 'Chainlink LINK'),
    'ADA': ('كاردانو', 'Cardano ADA'), 'LTC': ('لايتكوين', 'Litecoin'),
}


CG_IDS = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'XRP': 'ripple', 'BNB': 'binancecoin', 'SOL': 'solana', 'TRX': 'tron', 'DOGE': 'dogecoin',
          'ZEC': 'zcash', 'LINK': 'chainlink', 'ADA': 'cardano', 'AVAX': 'avalanche-2', 'DOT': 'polkadot', 'LTC': 'litecoin',
          'BCH': 'bitcoin-cash', 'NEAR': 'near'}


def market_refs(status):
    """Independent reference data for crypto: price, 24h volume across all exchanges, market cap.
    CoinMarketCap when a CMC_KEY secret is set, otherwise CoinGecko's public API."""
    out = {'updated': NOW.strftime('%Y-%m-%dT%H:%MZ'), 'coins': {}}
    key = os.environ.get('CMC_KEY', '').strip()
    try:
        if key:
            req = urllib.request.Request('https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=' + ','.join(CG_IDS) + '&convert=USD',
                                         headers={**UA, 'X-CMC_PRO_API_KEY': key, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read().decode())['data']
            out['source'] = 'CoinMarketCap'
            for sym in CG_IDS:
                d = data.get(sym)
                d = d[0] if isinstance(d, list) else d
                if not d: continue
                q = d['quote']['USD']
                out['coins'][sym] = {'price': q.get('price'), 'vol24': q.get('volume_24h'), 'mcap': q.get('market_cap'), 'chg24': q.get('percent_change_24h'), 'rank': d.get('cmc_rank')}
        else:
            data = get('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=' + ','.join(CG_IDS.values()) + '&price_change_percentage=24h')
            out['source'] = 'CoinGecko'
            inv = {v: k for k, v in CG_IDS.items()}
            for d in data or []:
                sym = inv.get(d.get('id'))
                if sym:
                    out['coins'][sym] = {'price': d.get('current_price'), 'vol24': d.get('total_volume'), 'mcap': d.get('market_cap'),
                                         'chg24': d.get('price_change_percentage_24h'), 'rank': d.get('market_cap_rank')}
        status['refs'] = f"{out.get('source')}: {len(out['coins'])} coins"
    except Exception as e:
        status['refs_err'] = str(e)[:120]
        return
    if out['coins']:
        write(f'{ROOT}/refs.json', out)


def gnews(q, lang):
    import xml.etree.ElementTree as ET, urllib.parse, email.utils
    loc = 'hl=ar&gl=SA&ceid=SA:ar' if lang == 'ar' else 'hl=en-US&gl=US&ceid=US:en'
    url = f'https://news.google.com/rss/search?q={urllib.parse.quote(q + " when:30d")}&{loc}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        root = ET.fromstring(r.read())
    out = []
    for it in root.iter('item'):
        t = (it.findtext('title') or '').strip()
        src = (it.findtext('source') or '').strip()
        sname = src.split(' : ')[0].strip()
        if src and t.endswith(' - ' + src):
            t = t[: -len(src) - 3]
        try:
            d = email.utils.parsedate_to_datetime(it.findtext('pubDate')).date().isoformat()
        except Exception:
            d = ''
        if t and it.findtext('link'):
            out.append({'t': t[:220], 'u': it.findtext('link'), 's': sname[:40], 'd': d, 'lang': lang})
    return out


def news(status):
    """pro/news.json: recent headlines per asset from Google News (Arabic, plus English for global assets)."""
    out, errs = {}, 0
    for c, (qa, qe) in NEWS_Q.items():
        items = []
        for q, lang, n in ((qa, 'ar', 8), (qe, 'en', 6)):
            if not q:
                continue
            try:
                items += gnews(q, lang)[:n]
            except Exception as e:
                errs += 1
                if errs < 4:
                    status.setdefault('notes', []).append(f'{c} news: {str(e)[:60]}')
            time.sleep(0.6)
        items.sort(key=lambda x: x['d'], reverse=True)
        if items:
            out[c] = items[:14]
    write(f'{ROOT}/news.json', {'updated': NOW.strftime('%Y-%m-%dT%H:%MZ'), 'a': out})
    status['news'] = len(out)


MNEWS_Q = {
    'sa': [('اكتتاب تداول السوق السعودية', 'ar'), ('إدراج أسهم السوق الرئيسية تداول', 'ar'), ('السوق الموازية نمو إدراج', 'ar'),
           ('توزيعات أرباح الشركات السعودية', 'ar'), ('نتائج أرباح الشركات السعودية الربع', 'ar'), ('هيئة السوق المالية السعودية', 'ar'), ('مؤشر تاسي اليوم', 'ar')],
    'us': [('الأسهم الأمريكية وول ستريت', 'ar'), ('IPO Nasdaq NYSE debut', 'en'), ('S&P 500 stocks earnings', 'en'), ('Federal Reserve stocks', 'en')],
    'cx': [('العملات الرقمية بيتكوين', 'ar'), ('crypto exchange listing token', 'en'), ('crypto ETF SEC', 'en'), ('crypto regulation', 'en')],
    'ix': [('أسعار الذهب والنفط', 'ar'), ('OPEC oil prices', 'en'), ('gold price record', 'en'), ('dollar index Treasury yields', 'en')],
}


def mnews(status):
    """pro/mnews.json: market-wide headlines (listings, IPOs, results, dividends, regulation) for each market."""
    out = {}
    for mk, qs in MNEWS_Q.items():
        items, seen = [], set()
        for q, lang in qs:
            try:
                for it in gnews(q, lang)[:10]:
                    k = it['t'][:70]
                    if k not in seen:
                        seen.add(k); items.append(it)
            except Exception as e:
                status.setdefault('notes', []).append(f'{mk} mnews: {str(e)[:50]}')
            time.sleep(0.6)
        items.sort(key=lambda x: x['d'], reverse=True)
        out[mk] = items[:45]
    write(f'{ROOT}/mnews.json', {'updated': NOW.strftime('%Y-%m-%dT%H:%MZ'), 'm': out})
    status['mnews'] = {k: len(v) for k, v in out.items()}


def summary():
    """pro/summary.json: last price and daily change per asset, used to colour the menu."""
    out = {}
    for kind in ('sa', 'us', 'ix', 'cx'):
        folder = f'{ROOT}/{kind}'
        if not os.path.isdir(folder):
            continue
        for fn in sorted(os.listdir(folder)):
            if not fn.endswith('.json'):
                continue
            try:
                o = json.load(open(f'{folder}/{fn}'))
                d = o.get('d') or o.get('1d') or []
                if len(d) < 2:
                    continue
                c, prev, t = d[-1][4], d[-2][4], d[-1][0]
                lp = f'{ROOT}/live/{fn}'
                if kind != 'cx' and os.path.exists(lp):
                    lv = json.load(open(lp))
                    day = dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat()
                    if lv.get('bars') and lv.get('day', '') >= day:
                        c, prev = lv['bars'][-1][1], lv.get('prev') or prev
                out[fn[:-5]] = {'k': kind, 'c': round(c, 6), 'ch': round((c / prev - 1) * 100, 3) if prev else 0}
            except Exception:
                continue
    write(f'{ROOT}/summary.json', {'updated': NOW.strftime('%Y-%m-%dT%H:%MZ'), 'a': out})


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
        summary()
    else:
        stocks_full(status)
        stocks_live(status)
        crypto(status)
        market_refs(status)
        try:
            news(status)
        except Exception as e:
            status['news_err'] = str(e)[:120]
        try:
            mnews(status)
        except Exception as e:
            status['mnews_err'] = str(e)[:120]
        write(f'{ROOT}/status.json', status)
        summary()
    print(json.dumps(status, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    if '--summary' in sys.argv:
        summary()
    else:
        main()
