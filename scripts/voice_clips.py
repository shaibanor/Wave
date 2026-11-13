#!/usr/bin/env python3
"""Builds the owner's voice clips for the radar's spoken explanation.
Reads pro/voice/clips.json (fixed phrases, names, number and time words), asks ElevenLabs to speak each item once
with the owner's cloned voice, trims the silence at both ends, and writes pro/voice/ar/<hash>.mp3 plus
pro/voice/ar/index.json (text -> file). Existing clips are kept, so a re-run only pays for new or changed items.
Needs the repository secrets ELEVEN_KEY and ELEVEN_VOICE_ID; neither is ever written to the site."""
import hashlib, json, os, shutil, subprocess, sys, time, urllib.request, urllib.error

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pro', 'voice')
OUT = os.path.join(ROOT, 'ar')
KEY, VOICE = os.environ.get('ELEVEN_KEY', '').strip(), os.environ.get('ELEVEN_VOICE_ID', '').strip()
_VF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent', 'voice_id')
if os.path.exists(_VF) and open(_VF).read().strip():
    VOICE = open(_VF).read().strip()  # the owner's current voice (a voice id is not a secret; the API key stays in Secrets)
MODEL = os.environ.get('VOICE_MODEL', '').strip() or 'eleven_v4'
STAB = float(os.environ.get('VOICE_STABILITY', '') or 0.45)
FORCE = os.environ.get('VOICE_FORCE', '') == 'true'


CTX = {'prev': 'السعر الحين', 'next': 'دُولار، والهدف قريب'}


def _post(text, model, settings, ctx):
    d = {'text': text, 'model_id': model, 'language_code': 'ar', 'voice_settings': settings}
    if ctx:
        d['previous_text'] = ctx[0]; d['next_text'] = ctx[1]
    req = urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128', data=json.dumps(d).encode(),
                                 headers={'xi-api-key': KEY, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def tts(text, short):
    """Speak one clip. Short chunks (numbers, currency, single words) get neighbouring context so they sound mid-sentence."""
    v3 = 'v3' in MODEL or 'v4' in MODEL
    settings = {'stability': 0.5 if v3 else STAB, 'similarity_boost': 0.9}
    if not v3:
        settings.update({'style': 0.25, 'use_speaker_boost': True})
    ctx = (CTX['prev'], CTX['next']) if short and not v3 else None
    for k in range(5):
        try:
            return _post(text, MODEL, settings, ctx)
        except urllib.error.HTTPError as e:
            msg = e.read()[:400].decode(errors='ignore')
            if e.code in (429, 500, 502, 503) and k < 4:
                time.sleep(4 * (k + 1)); continue
            if e.code in (400, 422) and ctx:
                ctx = None; continue
            if e.code in (400, 422) and len(settings) > 2:
                settings = {'stability': settings['stability'], 'similarity_boost': 0.9}; continue
            raise SystemExit(f'ElevenLabs error {e.code} ({MODEL}): {msg}')


def pick_model():
    """Use the requested model; if the account cannot use it, fall back to the next one."""
    global MODEL
    for m in [MODEL] + [x for x in ('eleven_v4', 'eleven_v3', 'eleven_multilingual_v2') if x != MODEL]:
        try:
            _post('تجربة', m, {'stability': 0.5, 'similarity_boost': 0.9}, None); MODEL = m; print('model', m); return
        except urllib.error.HTTPError as e:
            print('model', m, 'not usable:', e.code, e.read()[:160].decode(errors='ignore'))
    raise SystemExit('No usable model.')


def ffmpeg():
    exe = shutil.which('ffmpeg')
    if exe:
        return exe
    import imageio_ffmpeg  # static ffmpeg build installed by the workflow
    return imageio_ffmpeg.get_ffmpeg_exe()


def trim(raw, dst):
    tmp = dst + '.in.mp3'
    open(tmp, 'wb').write(raw)
    f = 'silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.03,areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.06,areverse'
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', tmp, '-af', f, '-ac', '1', '-b:a', '64k', dst], check=True)
    os.remove(tmp)


def probe():
    """Speak one sample sentence with each candidate model so the owner can pick the voice that sounds like him."""
    text = 'منطقة الشراء بين أربعة وسبعين ألف دُولار وأربعة وسبعين ألف وثلاث مية دُولار، وتبيع على خمسة وسبعين ألف دُولار، يعني ربحك اثنين بالمية. تقدر تشتري الحين.'
    pd = os.path.join(ROOT, 'probe'); os.makedirs(pd, exist_ok=True)
    cands = [('eleven_v4', ''), ('eleven_v3', ''), ('eleven_v3', '[Saudi accent] '), ('eleven_multilingual_v2', ''), ('eleven_turbo_v2_5', ''), ('eleven_flash_v2_5', '')]
    for i, (m, pre) in enumerate(cands):
        st = {'stability': 0.5, 'similarity_boost': 0.9}
        try:
            raw = _post(pre + text, m, st, None)
            open(f'{pd}/{i+1}_{m}{"_saudi_tag" if pre else ""}.mp3', 'wb').write(raw); print('probe ok', m, pre)
        except urllib.error.HTTPError as e:
            print('probe fail', m, e.code, e.read()[:160].decode(errors='ignore'))


def main():
    if os.environ.get('VOICE_PROBE') == 'true':
        if not KEY or not VOICE:
            sys.exit('Missing ELEVEN_KEY or ELEVEN_VOICE_ID secret.')
        return probe()
    if not KEY or not VOICE:
        sys.exit('Missing ELEVEN_KEY or ELEVEN_VOICE_ID secret.')
    global FF
    FF = ffmpeg()
    inv = json.load(open(os.path.join(ROOT, 'clips.json'), encoding='utf-8'))
    items = inv['phrases'] + inv.get('words', [])
    say = inv.get('say', {})
    say2 = inv.get('say2', {})  # pronunciation fixes: a clip is remade when one of these words is in it
    # coins listed on Binance that have no Arabic name yet: spoken as a word, not letter by letter
    try:
        with urllib.request.urlopen('https://data-api.binance.vision/api/v3/ticker/24hr?type=MINI', timeout=30) as r:
            tk = json.loads(r.read())
        skip = {'USDC', 'FDUSD', 'TUSD', 'USDP', 'DAI', 'EUR', 'AEUR', 'USDE', 'XUSD', 'BFUSD', 'RLUSD', 'USD1', 'PYUSD', 'EURI', 'BUSD'}
        for x in tk:
            sym = x.get('symbol', '')
            if not sym.endswith('USDT') or float(x.get('quoteVolume') or 0) < 3e6:
                continue
            b = sym[:-4]
            if b in skip or b.endswith(('UP', 'DOWN', 'BULL', 'BEAR')) or b in items:
                continue
            items.append(b); say.setdefault(b, b.capitalize())
        print('binance names', len(items))
    except Exception as e:
        print('binance list skipped:', e)
    pick_model()
    os.makedirs(OUT, exist_ok=True)
    idx_p = os.path.join(OUT, 'index.json')
    idx = json.load(open(idx_p, encoding='utf-8')) if os.path.exists(idx_p) and not FORCE else {'clips': {}}
    tag = f'{MODEL}|{STAB}|v2' + (f'|{VOICE}' if os.path.exists(_VF) else '')
    made = 0
    for t in items:
        fix = [w for w in t.replace('،', ' ').split() if w in say2]
        key = f'{tag}|{t}' + (('|p2|' + '|'.join(say2[w] for w in fix)) if fix else '')
        h = hashlib.sha1(key.encode()).hexdigest()[:12] + '.mp3'
        if not FORCE and idx['clips'].get(t) == h and os.path.exists(os.path.join(OUT, h)):
            continue
        spoken = ' '.join(say2.get(w.rstrip('،'), say.get(w, w)) + ('،' if w.endswith('،') and w.rstrip('،') in say2 else '') for w in t.split(' '))
        trim(tts(spoken, len(t) <= 28), os.path.join(OUT, h))
        idx['clips'][t] = h
        made += 1
        time.sleep(0.25)
    keep = set(idx['clips'].values())
    for f in os.listdir(OUT):
        if f.endswith('.mp3') and f not in keep:
            os.remove(os.path.join(OUT, f))
    idx.update({'model': MODEL, 'stability': STAB, 'count': len(idx['clips']), 'updated': time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())})
    json.dump(idx, open(idx_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('clips', len(idx['clips']), 'new', made)


if __name__ == '__main__':
    main()
