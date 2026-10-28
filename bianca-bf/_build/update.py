#!/usr/bin/env python3
"""Atualiza o dashboard BF da Bianca a partir das respostas do Meta Ads.

Uso (dentro de bianca-bf/_build):
    python3 update.py raw/

raw/ precisa ter quatro arquivos, cada um com o valor do campo `ad_entities`
devolvido pelo ads_get_ad_entities (um array JSON):
  ads_daily.json   nível ad, time_increment="1", janela recente (ex.: last_3d ou today)
  ads_meta.json    nível ad, sem quebra diária: id, name, adset_id, effective_status
  adsets.json      nível adset: id, name, effective_status, daily_budget
  placements.json  nível adset, date_preset=maximum, breakdowns publisher_platform + platform_position

O histórico diário fica em data.json (acumulado). Cada rodada substitui os dias
que vieram em ads_daily.json e mantém os anteriores. Depois gera ../index.html.
"""
import json, os, sys, re
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ACCOUNT = '736602091732648'
TZ = timezone(timedelta(hours=-3))
WARM = re.compile(r'engaj|envolv|rmk|remarketing|retarget|visit|lista|seguidor|quente|clientes|compradores', re.I)


def load(path):
    with open(path, encoding='utf-8') as f:
        v = json.load(f)
    if isinstance(v, dict) and 'ad_entities' in v:
        v = v['ad_entities']
    if isinstance(v, str):
        v = json.loads(v)
    return v or []


def num(v):
    if v is None:
        return 0.0
    if isinstance(v, dict):
        v = v.get('value')
    if v is None:
        return 0.0
    s = str(v).strip().replace('%', '')
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


def place_key(r):
    pub, pos = r.get('publisher_platform', ''), r.get('platform_position', '')
    if pos == 'feed':
        return f'{pub}_feed'
    if pub == 'whatsapp':
        return 'whatsapp_status'
    if pub == 'audience_network':
        return 'audience_network'
    return pos.replace('instagram_explore_grid_home', 'instagram_explore')


def main(raw):
    data_path = os.path.join(HERE, 'data.json')
    data = json.load(open(data_path, encoding='utf-8')) if os.path.exists(data_path) else {'ads_daily': []}

    meta = {str(a['id']): a for a in load(os.path.join(raw, 'ads_meta.json'))}
    daily = load(os.path.join(raw, 'ads_daily.json'))
    sets_raw = load(os.path.join(raw, 'adsets.json'))
    plc = load(os.path.join(raw, 'placements.json'))

    # --- histórico diário: substitui os dias recebidos ---
    new_rows = []
    for r in daily:
        aid = str(r['id'])
        m = meta.get(aid, {})
        new_rows.append([r['date_start'], aid, r.get('name') or m.get('name', aid),
                         str(r.get('adset_id') or m.get('adset_id', '')),
                         round(num(r.get('amount_spent')), 2), int(num(r.get('impressions'))),
                         int(num(r.get('link_click'))), int(num(r.get('omni_landing_page_view'))),
                         int(num(r.get('lead')))])
    fresh_days = {r[0] for r in new_rows}
    rows = [r for r in data.get('ads_daily', []) if r[0] not in fresh_days] + new_rows
    rows = [r for r in rows if r[4] > 0 or r[5] > 0]
    rows.sort(key=lambda r: (r[0], r[2]))
    data['ads_daily'] = rows

    # --- conjuntos: rótulo A, B, C... por ordem de id (nomes se repetem) ---
    old_sets = data.get('adsets', {})
    ids = sorted({str(s['id']) for s in sets_raw} | {r[3] for r in rows} | set(old_sets))
    sets_by_id = {str(s['id']): s for s in sets_raw}
    adsets = {}
    for i, sid in enumerate(ids):
        s = sets_by_id.get(sid, {})
        name = s.get('name') or old_sets.get(sid, {}).get('name') or sid
        dup = sum(1 for x in ids if (sets_by_id.get(x, {}).get('name') or old_sets.get(x, {}).get('name')) == name) > 1
        letter = chr(65 + i) if i < 26 else str(i + 1)
        clean = re.sub(r'^\d+\s*-\s*', '', name)
        adsets[sid] = {
            'name': name,
            'label': f'{clean} · {letter}' if dup else clean,
            'status': s.get('effective_status') or old_sets.get(sid, {}).get('status', 'PAUSED'),
            'budget': num(s.get('daily_budget')) if s else old_sets.get(sid, {}).get('budget', 0),
            'temp': 'quente' if WARM.search(name) else 'frio',
        }
    data['adsets'] = adsets

    # --- status dos anúncios ---
    st = dict(data.get('ad_status', {}))
    for m in meta.values():
        st[m.get('name', str(m['id']))] = m.get('effective_status', '')
    data['ad_status'] = st

    # --- link do criativo (permalink da publicação) ---
    # creatives.json (opcional): resposta de ads_get_creatives com id e effective_object_story_id.
    # ads_meta.json precisa trazer creative_id para ligar anúncio -> criativo.
    links = dict(data.get('ad_links', {}))
    cpath = os.path.join(raw, 'creatives.json')
    if os.path.exists(cpath):
        with open(cpath, encoding='utf-8') as f:
            cr = json.load(f)
        if isinstance(cr, dict):
            cr = cr.get('ad_creatives', cr)
        story = {str(c['id']): c.get('effective_object_story_id') or c.get('object_story_id') for c in cr}
        for m in meta.values():
            sid = story.get(str(m.get('creative_id', '')))
            if sid and '_' in sid:
                page, post = sid.split('_', 1)
                links[m.get('name', str(m['id']))] = f'https://www.facebook.com/{page}/posts/{post}'
    data['ad_links'] = links

    # --- posicionamento (acumulado da campanha) ---
    if plc:
        data['placements'] = [[str(r['id']), place_key(r), round(num(r.get('amount_spent')), 2),
                               int(num(r.get('impressions'))), int(num(r.get('link_click'))),
                               int(num(r.get('omni_landing_page_view'))), int(num(r.get('lead')))]
                              for r in plc]

    camps = sorted({m.get('campaign_name') for m in meta.values() if m.get('campaign_name')})
    if camps:
        data['campaigns'] = camps
    now = datetime.now(TZ)
    data['account_id'] = ACCOUNT
    data['generated'] = now.isoformat(timespec='minutes')
    data['generated_label'] = now.strftime('%d/%m/%Y às %H:%M')

    json.dump(data, open(data_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    html = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    html = html.replace('/*__DATA__*/null', json.dumps(data, ensure_ascii=False))
    open(os.path.join(HERE, '..', 'index.html'), 'w', encoding='utf-8').write(html)

    tot = [sum(r[i] for r in rows) for i in range(4, 9)]
    print(f"ok · {len(rows)} linhas · dias {rows[0][0] if rows else '-'}..{rows[-1][0] if rows else '-'} · "
          f"invest R$ {tot[0]:.2f} · imp {tot[1]} · cliques {tot[2]} · PV {tot[3]} · leads {tot[4]} · "
          f"atualizado {data['generated_label']}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'raw'))
