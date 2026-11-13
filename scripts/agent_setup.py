"""Create or update the platform's voice agent on ElevenLabs (the owner's cloned voice) and its client tools.
Runs from GitHub Actions only; the API key stays in GitHub Secrets. Writes pro/voice/agent.json with the public agent id."""
import json, os, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get('ELEVEN_KEY', '').strip()
VOICE = os.environ.get('ELEVEN_VOICE_ID', '').strip()
MODEL = (os.environ.get('AGENT_TTS') or 'eleven_v4').strip()
LLM = (os.environ.get('AGENT_LLM') or 'gpt-4.1').strip()
DAILY = int(os.environ.get('AGENT_DAILY') or 40)
MAXSEC = int(os.environ.get('AGENT_MAXSEC') or 300)
API = 'https://api.elevenlabs.io'
OUT = os.path.join(ROOT, 'pro', 'voice', 'agent.json')

def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'xi-api-key': KEY, 'Content-Type': 'application/json', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            t = r.read().decode() or '{}'
            return json.loads(t)
    except urllib.error.HTTPError as e:
        print(f'HTTP {e.code} {method} {path}: {e.read().decode()[:1500]}')
        raise

S = lambda d: {'type': 'string', 'description': d}
TOOLS = [
    ('get_asset_analysis', 'يجلب التحليل الفني الحالي لأصل من أصول المنصة: السعر، الاتجاه، المؤشرات، الدعم والمقاومة وسبب تحديدها، الخلاصة، توقع الأسبوع، وأهم الأخبار وأسباب الحركة. استدعه قبل ذكر أي رقم.',
     {'asset': S('اسم الأصل أو رمزه كما قاله الزائر، مثل: أرامكو، 2222، الإيثيريوم، ETH، الذهب، ميتا. اتركه فارغًا للأصل المعروض على الشاشة.')}, [], True, 25),
    ('get_radar_trade', 'يجلب صفقة الرادار السريعة للأصل: منطقة الشراء، البيع، الوقف، الربح والخسارة المتوقعة، والتوقيت، أو سبب عدم وجود صفقة.',
     {'asset': S('اسم الأصل أو رمزه. فارغ = الأصل المعروض على الشاشة.')}, [], True, 40),
    ('open_asset', 'يفتح الأصل على شاشة الزائر حتى يتقلب كل شيء عليه.',
     {'asset': S('اسم الأصل أو رمزه.')}, ['asset'], True, 10),
    ('highlight_chart_zone', 'يضيء على الشاشة الجزء الذي تتكلم عنه الآن.',
     {'zone': S('واحد من: price, trend, support, resistance, buy, sell, stop, news, forecast, radar')}, ['zone'], False, 5),
    ('list_assets', 'يجلب قائمة الأصول المتاحة في المنصة لكل سوق.', {'market': S('اختياري: crypto, saudi, us, commodities')}, [], True, 10),
    ('escalate_vip_inquiry', 'يحوّل طلب الزائر لاستشارة خاصة أو تواصل مباشر إلى صاحب المنصة.',
     {'summary': S('ملخص طلب الزائر بجملة أو جملتين.')}, ['summary'], True, 10),
]

def tool_cfg(name, desc, props, req, wait, tmo):
    return {'type': 'client', 'name': name, 'description': desc, 'expects_response': wait, 'response_timeout_secs': tmo,
            'parameters': {'type': 'object', 'properties': props, 'required': req}}

def main():
    if not KEY or not VOICE:
        sys.exit('ELEVEN_KEY / ELEVEN_VOICE_ID secrets are missing')
    prev = json.load(open(OUT)) if os.path.exists(OUT) else {}
    have = {}
    try:
        lst = call('GET', '/v1/convai/tools')
        for t in lst.get('tools', []):
            n = (t.get('tool_config') or {}).get('name')
            if n: have[n] = t.get('id')
    except Exception as e:
        print('tool list failed:', e)
    ids = []
    for spec in TOOLS:
        cfg = tool_cfg(*spec)
        if spec[0] in have:
            call('PATCH', f'/v1/convai/tools/{have[spec[0]]}', {'tool_config': cfg}); ids.append(have[spec[0]])
        else:
            r = call('POST', '/v1/convai/tools', {'tool_config': cfg}); ids.append(r['id'])
        print('tool ok', spec[0])
    prompt = open(os.path.join(ROOT, 'scripts', 'agent', 'prompt.md'), encoding='utf-8').read()
    dc = {
        'client_questions': {'type': 'string', 'description': 'أسئلة الزائر كما قالها، مفصولة بعلامة |'},
        'answer_summary': {'type': 'string', 'description': 'ملخص قصير لطريقة رد الوكيل وما قاله'},
        'assets_discussed': {'type': 'string', 'description': 'الأصول التي نوقشت، مفصولة بفاصلة'},
        'zones_discussed': {'type': 'string', 'description': 'المناطق التي ذُكرت مع أرقامها، مثل: شراء 2010 | هدف 2052 | وقف 1950'},
        'requires_followup': {'type': 'boolean', 'description': 'هل طلب الزائر استشارة خاصة أو تواصلًا مع صاحب المنصة'},
        'satisfaction': {'type': 'integer', 'description': 'تقدير رضا الزائر من 1 إلى 5 حسب كلامه ونبرته'},
    }
    body = {
        'name': 'Tiko voice agent',
        'conversation_config': {
            'agent': {'first_message': 'يا هلا والله! معك الوكيل الصوتي لمنصة تيكو. وش تبي نناقش؟ السهم اللي قدامك، ولا عندك سهم أو عملة ثانية في بالك؟',
                      'language': 'ar',
                      'dynamic_variables': {'dynamic_variable_placeholders': {'current_asset': 'غير محدد'}},
                      'prompt': {'prompt': prompt, 'llm': LLM, 'temperature': 0.4, 'tool_ids': ids, 'built_in_tools': {'end_call': {'name': 'end_call', 'description': '', 'params': {'system_tool_type': 'end_call'}}}}},
            'tts': {'model_id': MODEL, 'voice_id': VOICE},
            'conversation': {'max_duration_seconds': MAXSEC},
        },
        'platform_settings': {
            'auth': {'enable_auth': False, 'allowlist': [{'hostname': 'shaibanor.github.io'}]},
            'call_limits': {'agent_concurrency_limit': 3, 'daily_limit': DAILY},
            'data_collection': dc,
        },
    }
    aid = prev.get('agent_id')
    if aid:
        try:
            call('PATCH', f'/v1/convai/agents/{aid}', body); print('agent updated', aid)
        except urllib.error.HTTPError as e:
            if e.code != 404: raise
            aid = None
    if not aid:
        aid = call('POST', '/v1/convai/agents/create', body)['agent_id']; print('agent created', aid)
    json.dump({'agent_id': aid, 'tts': MODEL, 'daily_limit': DAILY, 'max_seconds': MAXSEC}, open(OUT, 'w'))

if __name__ == '__main__':
    main()
