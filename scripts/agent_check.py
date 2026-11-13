"""Check the voice agent: its stored settings, and one simulated text conversation in Arabic (tool results mocked)."""
import json, os, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get('ELEVEN_KEY', '').strip()
API = 'https://api.elevenlabs.io'
def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'xi-api-key': KEY, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=180) as r: return json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        print(f'HTTP {e.code} {path}: {e.read().decode()[:1200]}'); return None
aid = json.load(open(os.path.join(ROOT, 'pro', 'voice', 'agent.json')))['agent_id']
a = call('GET', f'/v1/convai/agents/{aid}') or {}
cc, ps = a.get('conversation_config') or {}, a.get('platform_settings') or {}
ag = cc.get('agent') or {}
print('CHECK language', ag.get('language'), '| llm', (ag.get('prompt') or {}).get('llm'), '| tools', len((ag.get('prompt') or {}).get('tool_ids') or []))
print('CHECK tts', (cc.get('tts') or {}).get('model_id'), (cc.get('tts') or {}).get('voice_id'))
print('CHECK auth', json.dumps(ps.get('auth'), ensure_ascii=False)[:300], '| limits', ps.get('call_limits'))
mock = json.dumps({'asset': 'أرامكو السعودية', 'price_now': '25.60 ر.س', 'daily_trend': 'نازل', 'rsi_4h': 39, 'support': '25.54 ر.س', 'resistance': '25.68 ر.س',
                   'takeaway': 'السعر قريب من الدعم، بس الاتجاه نازل، انتظر شمعة ارتداد', 'news_drivers': ['السبب الأبرز حسب الأخبار نتائج الشركة المالية']}, ensure_ascii=False)
body = {'simulation_specification': {
            'simulated_user_config': {'first_message': 'هلا، وش رأيك في سهم أرامكو الحين؟', 'language': 'ar',
                                      'prompt': {'prompt': 'أنت زائر سعودي مبتدئ في الأسهم، تسأل عن أرامكو ثم تشكر وتنهي.', 'llm': 'gpt-4.1', 'temperature': 0.3}},
            'tool_mock_config': {n: {'default_return_value': mock if n == 'get_asset_analysis' else '{"ok":true}'} for n in
                                 ['get_asset_analysis', 'get_radar_trade', 'open_asset', 'highlight_chart_zone', 'list_assets', 'escalate_vip_inquiry']},
            'dynamic_variables': {'current_asset': 'أرامكو السعودية (2222) من السوق السعودي'}},
        'new_turns_limit': 6}
r = call('POST', f'/v1/convai/agents/{aid}/simulate-conversation', body)
if r is None:
    body['simulation_specification'].pop('tool_mock_config'); r = call('POST', f'/v1/convai/agents/{aid}/simulate-conversation', body)
for t in (r or {}).get('simulated_conversation') or []:
    tc = [x.get('tool_name') for x in (t.get('tool_calls') or [])]
    print('SIM', t.get('role'), '|', (t.get('message') or '')[:400], '| tools:', tc if tc else '')
an = (r or {}).get('analysis') or {}
print('SIM summary:', (an.get('transcript_summary') or '')[:400])
print('SIM data:', json.dumps(an.get('data_collection_results') or {}, ensure_ascii=False)[:600])
