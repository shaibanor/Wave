#!/usr/bin/env python3
"""Append the latest completed daily bars from pro/<kind>/<id>.json to the monthly candles in data.json."""
import json, os, datetime as dt
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
KIND = {}
for k in ('sa', 'us', 'cx', 'ix'):
    p = os.path.join(ROOT, 'pro', k)
    if os.path.isdir(p):
        for f in os.listdir(p):
            if f.endswith('.json'): KIND.setdefault(f[:-5], k)
def main():
    path = os.path.join(ROOT, 'data.json'); D = json.load(open(path)); C = D['candles']
    assets = sorted({k.split('_')[0] for k in C}); now = dt.datetime.now(dt.timezone.utc); today = now.date().isoformat(); added = 0
    closed = {'cx': False, 'sa': now.hour >= 13, 'us': now.hour >= 21, 'ix': now.hour >= 21}
    for a in assets:
        kind = KIND.get(a)
        if not kind: continue
        j = json.load(open(os.path.join(ROOT, 'pro', kind, f'{a}.json')))
        rows = j.get('1d') if kind == 'cx' else j.get('d')
        if not rows: continue
        have = set(); 
        for k, v in C.items():
            if k.startswith(a + '_'): have |= set(v['days'])
        last = max(have) if have else '0000'
        for r in rows:
            d = dt.datetime.fromtimestamp(int(r[0]), dt.timezone.utc).date().isoformat()
            if d <= last or (d >= today and not closed[kind]) or not r[4]: continue
            m = d[:7]; key = f'{a}_{m}'
            C.setdefault(key, {'asset': a, 'month': m, 'days': {}})['days'][d] = {'c': round(float(r[4]), 6), 'h': round(float(r[2]), 6), 'l': round(float(r[3]), 6), 'o': round(float(r[1]), 6)}
            added += 1
    json.dump(D, open(path, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('added', added)
if __name__ == '__main__':
    main()
