# Dashboard BF — Bianca Amorim (gerador)

Página publicada: https://dash.jamelligt.com.br/bianca-bf/

- `template.html`: layout (skill-dash-captacao-v2). Os dados entram no lugar de `/*__DATA__*/null`.
- `data.json`: histórico diário acumulado por anúncio. Cada atualização substitui os dias que vieram do Meta e mantém os anteriores.
- `update.py raw/`: lê as respostas do Meta Ads em `raw/` e regera `../index.html`.

## Como atualizar

Conta Meta Ads 736602091732648. Entram as campanhas com `[BF]` no nome (filtro `campaign.name` CONTAIN `[BF]`). Use `ads_get_ad_entities` e salve em `raw/` o array `ad_entities` de cada resposta:

| arquivo | level | período | campos / extras |
|---|---|---|---|
| `ads_daily.json` | ad | `last_3d`, `time_increment="1"` | id, name, adset_id, amount_spent, impressions, link_click, omni_landing_page_view, lead |
| `ads_meta.json` | ad | `maximum` | id, name, adset_id, campaign_name, effective_status |
| `adsets.json` | adset | `maximum` | id, name, effective_status, daily_budget |
| `placements.json` | adset | `maximum` | id, amount_spent, impressions, link_click, omni_landing_page_view, lead · breakdowns `publisher_platform`, `platform_position` |

Depois rode `python3 update.py raw/` e faça commit de `index.html` e `_build/data.json`. A pasta `raw/` não vai para o repositório.

Conjuntos com engajamento, remarketing, visitantes, lista etc. no nome contam como público quente; os demais, como frio.
