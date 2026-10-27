#!/usr/bin/env python3
"""Pre-publish gate: validates site data and pages. Exit 1 on hard failure."""
import json, os, re, sys, base64, datetime as dt, glob
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ASSETS = {'8311': 6, '1120': 6, '4340': 6, 'GOOGL': 5, 'META': 5, 'AVGO': 5, 'TSM': 5, 'JPM': 5, 'LLY': 5, 'V': 5, 'BTC': 3, 'ETH': 3, 'XRP': 3}
errors, warns = [], []

def bad_bar(c):
    try:
        o, h, l, cl = float(c['o']), float(c['h']), float(c['l']), float(c['c'])
    except Exception:
        return 'not numeric'
    if min(o, h, l, cl) <= 0: return 'non-positive'
    if l > min(o, cl) + 1e-9 or h < max(o, cl) - 1e-9: return 'low/high inconsistent'
    return None

def check_data():
    p = os.path.join(ROOT, 'data.json')
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception as e:
        errors.append(f'data.json unreadable: {e}'); return
    for k in ('candles', 'weeks', 'news'):
        if k not in d: errors.append(f'data.json missing key "{k}"')
    last = {}
    for doc_id, v in d.get('candles', {}).items():
        a = v.get('asset')
        for day, c in (v.get('days') or {}).items():
            why = bad_bar(c)
            if why: errors.append(f'{doc_id} {day}: {why}')
            last[a] = max(last.get(a, ''), day)
    today = dt.date.today()
    for a, max_age in ASSETS.items():
        if a not in last:
            errors.append(f'asset {a} has no candles'); continue
        age = (today - dt.date.fromisoformat(last[a])).days
        if age > max_age + 3: warns.append(f'{a} data is {age} days old (last {last[a]})')
    for w in d.get('weeks', {}).values():
        lab = w.get('lab') or {}
        if lab and not (0 < float(lab.get('low', 0)) <= float(lab.get('high', 0))):
            errors.append(f'week {w.get("asset")}_{w.get("week")}: invalid zone')
    if not d.get('news'): warns.append('news is empty')

def check_pro():
    for f in glob.glob(os.path.join(ROOT, 'pro', '*', '*.json')):
        try:
            j = json.load(open(f))
        except Exception as e:
            errors.append(f'{f}: unreadable {e}'); continue
        for key, rows in j.items():
            if key not in ('d', 'm', '1h', '4h', '1d', '1w', '1M') or not isinstance(rows, list): continue
            for r in rows[-50:]:
                if len(r) < 5 or min(r[1:5]) <= 0 or r[3] > min(r[1], r[4]) + 1e-9 or r[2] < max(r[1], r[4]) - 1e-9:
                    errors.append(f'{os.path.basename(f)} {key}: bad row {r[:5]}'); break

def check_pages():
    for name in ('index.html', 'pro.html'):
        p = os.path.join(ROOT, name)
        if not os.path.exists(p):
            if name == 'index.html': errors.append('index.html missing')
            continue
        h = open(p, encoding='utf-8').read()
        if re.search(base64.b64decode('Y2xhdWRlfGFudGhyb3BpYw==').decode(), h, re.I): errors.append(f'{name}: contains a forbidden attribution word')
        if '<title>' not in h: errors.append(f'{name}: no <title>')
        if name == 'index.html' and 'id="gate"' not in h: errors.append(f'{name}: access gate missing')

check_data(); check_pro(); check_pages()
for w in warns: print('WARN', w)
for e in errors[:50]: print('FAIL', e)
print(f'{len(errors)} errors, {len(warns)} warnings')
sys.exit(1 if errors else 0)
