"""Pull the voice agent's conversations from ElevenLabs and store them for the internal auditor only:
encrypted with the auditor's public key (vault/prof_key.json), so only the auditor code can open them."""
import base64, json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get('ELEVEN_KEY', '').strip()
API = 'https://api.elevenlabs.io'
OUT = os.path.join(ROOT, 'vault', 'agent_log.json')
CAP = 300

def get(path):
    req = urllib.request.Request(API + path, headers={'xi-api-key': KEY, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        print(f'HTTP {e.code} {path}: {e.read().decode()[:800]}'); raise

def encrypt(obj):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    kj = json.load(open(os.path.join(ROOT, 'vault', 'prof_key.json')))
    pub = serialization.load_der_public_key(base64.b64decode(kj['pub']))
    k = os.urandom(32); iv = os.urandom(12)
    ct = AESGCM(k).encrypt(iv, json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode(), None)
    wk = pub.encrypt(k, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    b = lambda x: base64.b64encode(x).decode()
    return {'v': 1, 'wk': b(wk), 'iv': b(iv), 'ct': b(ct)}

def val(dc, k):
    x = (dc or {}).get(k) or {}
    return x.get('value') if isinstance(x, dict) else x

def main():
    if not KEY: sys.exit('ELEVEN_KEY secret is missing')
    ag = os.path.join(ROOT, 'pro', 'voice', 'agent.json')
    if not os.path.exists(ag): print('no agent yet'); return
    aid = json.load(open(ag))['agent_id']
    conv, cur = [], None
    while len(conv) < CAP:
        q = f'/v1/convai/conversations?agent_id={aid}&page_size=100' + (f'&cursor={cur}' if cur else '')
        r = get(q); conv += r.get('conversations', [])
        cur = r.get('next_cursor')
        if not r.get('has_more') or not cur: break
    conv = conv[:CAP]
    ids = sorted(c['conversation_id'] for c in conv)
    prev = json.load(open(OUT)) if os.path.exists(OUT) else {}
    sig = str(len(ids)) + ':' + (ids[-1] if ids else '') + ':' + str(sum(1 for c in conv if c.get('status') == 'done'))
    if prev.get('sig') == sig: print('no new conversations'); return
    items = []
    for c in conv:
        cid = c['conversation_id']
        try: d = get(f'/v1/convai/conversations/{cid}')
        except Exception: continue
        tr = d.get('transcript') or []
        an = d.get('analysis') or {}
        dc = an.get('data_collection_results') or {}
        md = d.get('metadata') or {}
        items.append({
            'id': cid, 't': md.get('start_time_unix_secs') or c.get('start_time_unix_secs'), 'dur': md.get('call_duration_secs') or c.get('call_duration_secs'),
            'st': d.get('status') or c.get('status'),
            'q': [x.get('message') for x in tr if x.get('role') == 'user' and x.get('message')][:20],
            'a': [x.get('message') for x in tr if x.get('role') == 'agent' and x.get('message')][:20],
            'cq': val(dc, 'client_questions'), 'as': val(dc, 'answer_summary'), 'ad': val(dc, 'assets_discussed'),
            'zd': val(dc, 'zones_discussed'), 'fu': bool(val(dc, 'requires_followup')), 'sat': val(dc, 'satisfaction'),
            'sum': an.get('transcript_summary'), 'ok': an.get('call_successful'),
        })
        time.sleep(0.2)
    items.sort(key=lambda x: x['t'] or 0, reverse=True)
    out = encrypt({'at': int(time.time()), 'items': items}); out['sig'] = sig
    json.dump(out, open(OUT, 'w')); print('stored', len(items))

if __name__ == '__main__':
    main()
