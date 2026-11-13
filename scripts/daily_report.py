#!/usr/bin/env python3
"""Daily monitoring cycle: checks data freshness, workflows, QA, the live site and news feeds,
applies safe automatic fixes, and writes an Arabic technical report (HTML, rendered to PDF by the workflow)."""
import datetime as dt
import html
import json
import os
import subprocess
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REPO = os.environ.get('GITHUB_REPOSITORY', 'shaibanor/Wave')
TOKEN = os.environ.get('GITHUB_TOKEN', '')
NOW = dt.datetime.now(dt.timezone.utc)
RIYADH = NOW + dt.timedelta(hours=3)
SITE = 'https://shaibanor.github.io/Wave/'
NAMES = {'8311': 'عناية', '1120': 'الراجحي', '4340': 'الراجحي ريت', '2222': 'أرامكو', '1211': 'معادن', '1180': 'الأهلي', '7010': 'إس تي سي',
         '2010': 'سابك', '2082': 'أكوا باور', '4013': 'سليمان الحبيب', '1010': 'بنك الرياض', '1150': 'الإنماء', '1325': 'حديد وطني',
         'BTC': 'بيتكوين', 'ETH': 'إيثيريوم', 'XRP': 'ريبل', 'BNB': 'بي إن بي', 'SOL': 'سولانا', 'TRX': 'ترون', 'DOGE': 'دوجكوين', 'ZEC': 'زي كاش',
         'LINK': 'تشين لينك', 'ADA': 'كاردانو', 'LTC': 'لايتكوين', 'PARTI': 'بارتي', 'IMX': 'إيميوتبل', 'GOOGL': 'ألفابت', 'META': 'ميتا', 'AVGO': 'برودكوم', 'TSM': 'TSMC', 'JPM': 'جي بي مورغان',
         'LLY': 'إيلي ليلي', 'V': 'فيزا', 'TASI': 'تاسي', 'DJI': 'داو جونز', 'SPX': 'إس آند بي 500', 'NDX': 'ناسداك 100', 'GOLD': 'الذهب', 'SILVER': 'الفضة',
         'BRENT': 'برنت', 'US10Y': 'سندات 10 سنوات', 'DXY': 'مؤشر الدولار'}

issues, fixes, checks = [], [], []


def add(level, area, msg, detail=''):
    issues.append({'l': level, 'a': area, 'm': msg, 'd': detail})


def ok(area, msg, detail=''):
    checks.append({'a': area, 'm': msg, 'd': detail})


def api(path, method='GET', data=None):
    req = urllib.request.Request(f'https://api.github.com/repos/{REPO}{path}', method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json', 'User-Agent': 'wave-monitor'})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        return json.loads(body) if body else {}


def load(p, default=None):
    try:
        return json.load(open(os.path.join(ROOT, p)))
    except Exception:
        return default


def kind_of(i):
    for k in ('sa', 'us', 'cx', 'ix'):
        if os.path.exists(os.path.join(ROOT, 'pro', k, f'{i}.json')):
            return k
    return None


def expected_last(kind):
    """Most recent session that should already be closed for this market."""
    d = NOW
    if kind == 'cx':
        return (d - dt.timedelta(days=1)).date()
    days = {0, 1, 2, 3, 6} if kind == 'sa' else {0, 1, 2, 3, 4}
    close_h = 13 if kind == 'sa' else 21
    if d.weekday() not in days or d.hour < close_h:
        d -= dt.timedelta(days=1)
    while d.weekday() not in days:
        d -= dt.timedelta(days=1)
    return d.date()


def trading_gap(kind, last, exp):
    days = set(range(7)) if kind == 'cx' else ({0, 1, 2, 3, 6} if kind == 'sa' else {0, 1, 2, 3, 4})
    n, d = 0, last
    while d < exp:
        d += dt.timedelta(days=1)
        if d.weekday() in days:
            n += 1
    return n


def check_data():
    assets = load('assets.json', []) or []
    st = load('pro/status.json', {}) or {}
    stocks = st.get('stocks', {})
    stale = []
    for i in assets:
        k = kind_of(i)
        if not k:
            add('خطأ', 'البيانات', f'لا يوجد ملف بيانات للأصل {NAMES.get(i, i)} ({i})', f'pro/*/{i}.json غير موجود')
            continue
        j = load(f'pro/{k}/{i}.json', {}) or {}
        rows = j.get('1d') if k == 'cx' else j.get('d')
        if not rows:
            add('خطأ', 'البيانات', f'ملف {i} بلا شموع يومية', f'pro/{k}/{i}.json')
            continue
        last = dt.datetime.fromtimestamp(int(rows[-1][0]), dt.timezone.utc).date()
        cal = 'sa' if i == 'TASI' else k
        exp = expected_last(cal)
        gap = trading_gap(cal, last, exp)
        s = stocks.get(i, {})
        if s and s.get('ok') is False:
            add('خطأ', 'البيانات', f'فشل جلب {NAMES.get(i, i)} في آخر تحديث', json.dumps(s, ensure_ascii=False)[:160])
        if gap >= 3:
            add('خطأ', 'البيانات', f'{NAMES.get(i, i)} متأخر {gap} جلسات', f'آخر شمعة {last} والمتوقع {exp}')
            stale.append(i)
        elif gap >= 1:
            add('تنبيه', 'البيانات', f'{NAMES.get(i, i)} ينقصه {gap} جلسة (قد تكون عطلة)', f'آخر شمعة {last} والمتوقع {exp}')
    if not stale:
        ok('البيانات', f'جميع الأصول ({len(assets)}) محدثة ضمن الحد المقبول')
    upd = (st.get('updated') or '')
    ok('البيانات', f'آخر تحديث للبيانات: {upd}')
    return stale


def check_candles():
    D = load('data.json', {}) or {}
    C = D.get('candles', {})
    assets = load('assets.json', []) or []
    cut = (NOW - dt.timedelta(days=10)).date().isoformat()
    miss = []
    for i in assets:
        days = set()
        for k, v in C.items():
            if k.startswith(i + '_'):
                days |= set(v.get('days', {}))
        if not days or max(days) < cut:
            miss.append(i)
    if miss:
        add('تنبيه', 'تبويب الشموع', 'أصول بلا شموع حديثة في data.json: ' + '، '.join(NAMES.get(i, i) for i in miss), 'sync_candles.py')
    else:
        ok('تبويب الشموع', 'كل الأصول لها شموع حديثة')
    return miss


def check_validate():
    r = subprocess.run(['python3', os.path.join(ROOT, 'scripts', 'validate.py')], capture_output=True, text=True, cwd=ROOT)
    out = (r.stdout + r.stderr).strip()
    last = out.splitlines()[-1] if out else ''
    if r.returncode != 0 or ' 0 errors' not in ' ' + last:
        add('خطأ', 'سلامة الملفات', 'validate.py أبلغ عن أخطاء', out[-600:])
    elif '0 warnings' not in last:
        add('تنبيه', 'سلامة الملفات', 'validate.py أبلغ عن تحذيرات', '\n'.join(l for l in out.splitlines() if 'WARN' in l.upper())[:600] or last)
    else:
        ok('سلامة الملفات', 'validate.py: لا أخطاء ولا تحذيرات')


def check_qa():
    r = subprocess.run(['git', 'show', 'origin/qa:log.txt'], capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        add('تنبيه', 'الفحص الآلي', 'تعذر قراءة سجل الفحص الآلي (فرع qa)', r.stderr[:200])
        return
    log = r.stdout
    pe = [l for l in log.splitlines() if 'pageerror' in l]
    if pe:
        add('خطأ', 'الفحص الآلي', f'{len(pe)} خطأ JavaScript أثناء فتح الصفحة', '\n'.join(pe[:6]))
    else:
        ok('الفحص الآلي', 'لا أخطاء JavaScript في آخر فحص بالمتصفح (جوال وكمبيوتر)')


def check_runs():
    if not TOKEN:
        return
    since = (NOW - dt.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        runs = api(f'/actions/runs?per_page=100&created=>{since}').get('workflow_runs', [])
    except Exception as e:
        add('تنبيه', 'سير العمل', 'تعذر قراءة سجل سير العمل', str(e)[:200])
        return
    bad = [r for r in runs if r.get('conclusion') in ('failure', 'timed_out', 'startup_failure')]
    by = {}
    for r in runs:
        by.setdefault(r['name'], [0, 0])
        by[r['name']][0] += 1
        if r in bad:
            by[r['name']][1] += 1
    latest = {}
    for r in sorted(runs, key=lambda r: r['created_at']):
        latest[r['name']] = r.get('conclusion')
    for name, (n, f) in sorted(by.items()):
        if f and latest.get(name) == 'success' and f < n:
            ok('سير العمل', f'«{name}»: {f} تشغيل فاشل من {n}، وآخر تشغيل ناجح (لا أثر على الموقع)')
            continue
        if f:
            add('خطأ' if f == n else 'تنبيه', 'سير العمل', f'«{name}»: فشل {f} من {n} تشغيل خلال 24 ساعة',
                '\n'.join(r['html_url'] for r in bad if r['name'] == name)[:400])
    ok('سير العمل', f'{len(runs)} تشغيل خلال 24 ساعة، الفاشل منها {len(bad)}', '، '.join(f'{k}: {v[0]}' for k, v in sorted(by.items())))


def check_site():
    try:
        req = urllib.request.Request(SITE + '?monitor=' + NOW.strftime('%H%M'), headers={'User-Agent': 'wave-monitor'})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode('utf-8', 'ignore')
            code = r.status
        if code != 200:
            add('خطأ', 'الموقع المنشور', f'الموقع أعاد الحالة {code}', SITE)
        elif 'منصة تيكو' not in body or "var H='" not in body:
            add('خطأ', 'الموقع المنشور', 'الصفحة المنشورة ناقصة (العنوان أو بوابة الدخول غير موجودة)', f'الحجم {len(body)} بايت')
        else:
            ok('الموقع المنشور', f'الموقع يعمل (HTTP 200، الحجم {len(body)//1024} كيلوبايت)')
    except Exception as e:
        add('خطأ', 'الموقع المنشور', 'تعذر الوصول إلى الموقع', str(e)[:200])


def check_news():
    n = load('pro/news.json', {}) or {}
    a = n.get('a', {})
    empty = [i for i in (load('assets.json', []) or []) if not a.get(i)]
    m = (load('pro/mnews.json', {}) or {}).get('m', {})
    for k, lab in (('sa', 'السعودي'), ('us', 'الأمريكي'), ('cx', 'العملات'), ('ix', 'السلع')):
        if not m.get(k):
            add('تنبيه', 'الأخبار', f'أخبار السوق {lab} فارغة', 'pro/mnews.json')
    if empty:
        add('تنبيه', 'الأخبار', f'{len(empty)} أصل بلا أخبار حديثة: ' + '، '.join(NAMES.get(i, i) for i in empty[:12]), 'pro/news.json')
    ok('الأخبار', f'أخبار الأسواق: ' + '، '.join(f'{k}={len(v)}' for k, v in m.items()) + f' · أصول لها أخبار: {len(a)}')


def autofix(stale, miss):
    if miss:
        r = subprocess.run(['python3', os.path.join(ROOT, 'scripts', 'sync_candles.py')], capture_output=True, text=True, cwd=ROOT)
        fixes.append({'m': 'أعيدت مزامنة الشموع اليومية في data.json', 'd': (r.stdout + r.stderr).strip()[:200]})
    if stale and TOKEN:
        try:
            api('/actions/workflows/pro-data.yml/dispatches', 'POST', {'ref': 'main'})
            fixes.append({'m': 'أُعيد تشغيل تحديث البيانات (pro-data) بسبب أصول متأخرة', 'd': '، '.join(stale)})
        except Exception as e:
            fixes.append({'m': 'تعذر إعادة تشغيل pro-data', 'd': str(e)[:200]})


def render():
    E = sum(1 for i in issues if i['l'] == 'خطأ')
    W = sum(1 for i in issues if i['l'] == 'تنبيه')
    verdict, vc = (('سليم', 'g') if not E and not W else ('سليم مع تنبيهات', 'y') if not E else ('يحتاج تدخلًا', 'r'))
    e = html.escape
    rows = ''.join(f"<tr class='{'r' if i['l']=='خطأ' else 'y'}'><td>{e(i['l'])}</td><td>{e(i['a'])}</td><td>{e(i['m'])}</td><td><pre>{e(i['d'])}</pre></td></tr>" for i in issues) or "<tr><td colspan='4'>لا توجد مشكلات.</td></tr>"
    frows = ''.join(f"<tr><td>{e(f['m'])}</td><td><pre>{e(f['d'])}</pre></td></tr>" for f in fixes) or "<tr><td colspan='2'>لم تحتج أي إصلاحات تلقائية.</td></tr>"
    crows = ''.join(f"<tr><td>{e(c['a'])}</td><td>{e(c['m'])}</td><td><pre>{e(c['d'])}</pre></td></tr>" for c in checks)
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تقرير المراقبة اليومي</title><style>
@page{{size:A4;margin:16mm 14mm}}body{{font-family:'Noto Naskh Arabic','Noto Sans Arabic','DejaVu Sans',sans-serif;color:#1b2430;font-size:11pt;line-height:1.7}}
h1{{margin:0;font-size:20pt;color:#14506E}}.sub{{color:#5b6b7a;margin:2px 0 14px}}.top{{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #C9A55C;padding-bottom:10px;margin-bottom:14px}}
.v{{padding:6px 16px;border-radius:999px;font-weight:700}}.v.g{{background:#e3f6ec;color:#0f7a4a}}.v.y{{background:#fff4dc;color:#9a6a00}}.v.r{{background:#fde7e5;color:#b3261e}}
.k{{display:flex;gap:10px;margin:0 0 14px}}.k div{{flex:1;border:1px solid #d9e2ea;border-radius:10px;padding:8px 12px}}.k b{{display:block;font-size:16pt;color:#14506E}}
h2{{font-size:13pt;color:#14506E;border-inline-start:4px solid #27AAE2;padding-inline-start:8px;margin:18px 0 8px}}
table{{width:100%;border-collapse:collapse;font-size:9.5pt}}th{{background:#14506E;color:#fff;padding:6px;text-align:right}}td{{border-bottom:1px solid #e3e9ee;padding:5px 6px;vertical-align:top}}
tr.r td:first-child{{color:#b3261e;font-weight:700}}tr.y td:first-child{{color:#9a6a00;font-weight:700}}pre{{margin:0;white-space:pre-wrap;direction:ltr;text-align:left;font:8.5pt/1.5 'DejaVu Sans Mono',monospace;color:#44525f}}
.f{{margin-top:18px;color:#7a8794;font-size:8.5pt}}</style></head><body>
<div class="top"><div><h1>تقرير المراقبة اليومي · منصة تيكو</h1><p class="sub">{RIYADH:%Y-%m-%d %H:%M} بتوقيت الرياض · دورة المراقبة بعد تحديث الأسواق</p></div><span class="v {vc}">{verdict}</span></div>
<div class="k"><div>أخطاء<b>{E}</b></div><div>تنبيهات<b>{W}</b></div><div>إصلاحات تلقائية<b>{len(fixes)}</b></div><div>فحوص ناجحة<b>{len(checks)}</b></div></div>
<h2>المشكلات المكتشفة</h2><table><tr><th>المستوى</th><th>المجال</th><th>الوصف</th><th>التفاصيل التقنية</th></tr>{rows}</table>
<h2>الإصلاحات التلقائية</h2><table><tr><th>الإجراء</th><th>التفاصيل</th></tr>{frows}</table>
<h2>الفحوص الناجحة</h2><table><tr><th>المجال</th><th>النتيجة</th><th>التفاصيل</th></tr>{crows}</table>
<p class="f">يُولَّد هذا التقرير آليًا كل يوم. المستويات: «خطأ» يحتاج تدخلًا، «تنبيه» للمتابعة وقد يكون طبيعيًا (عطلة سوق مثلًا).</p></body></html>"""


def main():
    stale = check_data()
    miss = check_candles()
    check_validate()
    check_qa()
    check_runs()
    check_site()
    check_news()
    autofix(stale, miss)
    os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
    open(os.path.join(ROOT, 'out', 'report.html'), 'w').write(render())
    json.dump({'when': NOW.isoformat(), 'issues': issues, 'fixes': fixes, 'checks': checks},
              open(os.path.join(ROOT, 'out', 'report.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'errors={sum(1 for i in issues if i["l"]=="خطأ")} warnings={sum(1 for i in issues if i["l"]=="تنبيه")} fixes={len(fixes)}')


if __name__ == '__main__':
    main()
