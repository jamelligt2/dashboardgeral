#!/usr/bin/env python3
"""Atualiza os dados gravados do dash aurea-bf26/index.html.

Uso:
  python3 aurea-bf26/atualizar_dados.py ANUNCIOS.json POSICIONAMENTOS.json

ANUNCIOS.json        resultado de ads_get_ad_entities (level=ad, time_increment=1, com campaign_name)
POSICIONAMENTOS.json resultado de ads_get_ad_entities (level=adset, breakdown platform_position, time_increment=1)

Entram as campanhas cujo nome contém BLACKFRIDAY e LEAD, a partir de 04/11/2026.
Aceita o arquivo salvo pela ferramenta ({"ad_entities": "<json>"}) ou a lista pura.
"""
import json, re, sys, os
from datetime import datetime, timezone, timedelta

INICIO = '2026-11-04'
FILTRO = ('BLACKFRIDAY', 'LEAD')

def camp_ok(name):
    n = str(name or '').upper()
    return all(f in n for f in FILTRO)

def load(path):
    d = json.load(open(path))
    if isinstance(d, dict):
        d = d.get('ad_entities', d)
    if isinstance(d, str):
        d = json.loads(d)
    return d

def num(v):
    return float(v) if v not in (None, '') else 0.0

def spend(r):
    return num((r.get('amount_spent') or {}).get('value'))

def metrics(r):
    return [round(spend(r), 2), int(num(r.get('impressions'))), int(num(r.get('link_click'))),
            int(num(r.get('landing_page_view'))), int(num(r.get('lead')))]

def main(ads_path, place_path):
    ads, place = load(ads_path), load(place_path)
    rows, prow = [], []
    for r in ads:
        if r['date_start'] < INICIO or ('campaign_name' in r and not camp_ok(r['campaign_name'])):
            continue
        v = metrics(r)
        if any(v):
            rows.append([r['date_start'], r.get('adset_id', ''), r.get('adset_name', ''), r['name'], r['id'],
                         r.get('effective_status', '')] + v + [r.get('campaign_name', '')])
    for r in place:
        if r['date_start'] < INICIO:
            continue
        v = metrics(r)
        if any(v):
            prow.append([r['date_start'], r['id'], r['name'], r.get('publisher_platform', ''),
                         r.get('platform_position', '')] + v)
    if not rows:
        sys.exit('ERRO: nenhuma linha de anúncio com dados; o dash não foi alterado.')

    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    h = open(html_path, encoding='utf-8').read()
    snap = json.dumps({'rows': rows, 'place': prow}, separators=(',', ':'), ensure_ascii=False)
    now = datetime.now(timezone(timedelta(hours=-3)))
    stamp = now.strftime('%d/%m/%Y %Hh%M')
    h, n1 = re.subn(r'var SNAP = \{.*?\};\n', lambda m: 'var SNAP = ' + snap + ';\n', h, count=1, flags=re.S)
    h, n2 = re.subn(r"var SNAP_AT = '[^']*';", "var SNAP_AT = '" + stamp + "';", h)
    h = re.sub(r'extraídos em [0-9/]+ [0-9h]+\)', 'extraídos em ' + stamp + ')', h)
    if n1 != 1 or n2 != 1:
        sys.exit('ERRO: não achei SNAP/SNAP_AT no index.html; o dash não foi alterado.')
    open(html_path, 'w', encoding='utf-8').write(h)

    tot = [0, 0, 0, 0, 0]
    for r in rows:
        for i in range(5):
            tot[i] += r[6 + i]
    camps = sorted(set(r[11] for r in rows))
    print('OK %s | %d campanhas: %s' % (stamp, len(camps), ' / '.join(camps)))
    print('OK %s | %d linhas | invest R$ %.2f | imp %d | cliques %d | PV %d | leads %d | até %s'
          % (stamp, len(rows), tot[0], tot[1], tot[2], tot[3], tot[4], max(r[0] for r in rows)))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
