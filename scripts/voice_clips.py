#!/usr/bin/env python3
"""Builds the owner's voice clips for the radar's spoken explanation.
Reads pro/voice/clips.json (fixed phrases, names, number and time words), asks ElevenLabs to speak each item once
with the owner's cloned voice, trims the silence at both ends, and writes pro/voice/ar/<hash>.mp3 plus
pro/voice/ar/index.json (text -> file). Existing clips are kept, so a re-run only pays for new or changed items.
Needs the repository secrets ELEVEN_KEY and ELEVEN_VOICE_ID; neither is ever written to the site."""
import hashlib, json, os, subprocess, sys, time, urllib.request, urllib.error

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pro', 'voice')
OUT = os.path.join(ROOT, 'ar')
KEY, VOICE = os.environ.get('ELEVEN_KEY', '').strip(), os.environ.get('ELEVEN_VOICE_ID', '').strip()
MODEL = os.environ.get('VOICE_MODEL', '').strip() or 'eleven_multilingual_v2'
STAB = float(os.environ.get('VOICE_STABILITY', '') or 0.45)
FORCE = os.environ.get('VOICE_FORCE', '') == 'true'


def tts(text):
    body = json.dumps({'text': text, 'model_id': MODEL, 'language_code': 'ar',
                       'voice_settings': {'stability': STAB, 'similarity_boost': 0.85, 'style': 0.2, 'use_speaker_boost': True}}).encode()
    req = urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128', data=body,
                                 headers={'xi-api-key': KEY, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
    for k in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read()[:300]
            if e.code in (429, 500, 502, 503) and k < 3:
                time.sleep(4 * (k + 1)); continue
            # some models do not take language_code; retry once without it
            if e.code == 400 and b'language' in msg and k == 0:
                d = json.loads(body); d.pop('language_code', None); body = json.dumps(d).encode()
                req = urllib.request.Request(req.full_url, data=body, headers=dict(req.header_items())); continue
            raise SystemExit(f'ElevenLabs error {e.code}: {msg.decode(errors="ignore")}')


def trim(raw, dst):
    tmp = dst + '.in.mp3'
    open(tmp, 'wb').write(raw)
    f = 'silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.03,areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.06,areverse'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-af', f, '-ac', '1', '-b:a', '64k', dst], check=True)
    os.remove(tmp)


def main():
    if not KEY or not VOICE:
        sys.exit('Missing ELEVEN_KEY or ELEVEN_VOICE_ID secret.')
    inv = json.load(open(os.path.join(ROOT, 'clips.json'), encoding='utf-8'))
    items = inv['phrases'] + inv['words']
    os.makedirs(OUT, exist_ok=True)
    idx_p = os.path.join(OUT, 'index.json')
    idx = json.load(open(idx_p, encoding='utf-8')) if os.path.exists(idx_p) and not FORCE else {'clips': {}}
    tag = f'{MODEL}|{STAB}'
    made = 0
    for t in items:
        h = hashlib.sha1(f'{tag}|{t}'.encode()).hexdigest()[:12] + '.mp3'
        if not FORCE and idx['clips'].get(t) == h and os.path.exists(os.path.join(OUT, h)):
            continue
        trim(tts(t), os.path.join(OUT, h))
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
