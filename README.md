# nnd-azeco-bling

Integração com a **API v3 do Bling** para a galeria **NND | AZECO**: client Python, CLI e
scripts para consultar, relatar e ajustar dados financeiros (Pedidos de Venda, Contas a
Receber/Pagar, categorias, templates de histórico).

## Setup rápido

```bash
cp .env.example .env          # preencher BLING_CLIENT_ID/SECRET/REFRESH_TOKEN
python3 -m bling GET /produtos
```

Requisitos: **Python 3.8+ (testado no 3.14)**, sem dependências externas (só a biblioteca
padrão).

Para quem for operar via IA/agente, veja [`AGENTS.md`](AGENTS.md).

## Documentação (`specs/`)

| Arquivo | Conteúdo |
|---|---|
| [`specs/overview.md`](specs/overview.md) | CLI/client e estrutura de pastas. |
| [`specs/writing-scripts.md`](specs/writing-scripts.md) | Convenções pra escrever scripts novos (nomenclatura, boilerplate, dry-run). |
| [`specs/committing.md`](specs/committing.md) | Convenções de mensagem de commit. |
| [`specs/api-docs/api-cars.md`](specs/api-docs/api-cars.md) | Achados da API — CAR e `lancar-contas` (origens, destino, NF→CAR). |
| [`specs/api-docs/api-pv.md`](specs/api-docs/api-pv.md) | Achados da API — Pedido de Venda (recriação/edição, situação, vendedores). |
| [`specs/api-docs/api-cap.md`](specs/api-docs/api-cap.md) | Achados da API — Pedido de Compra → CAP. |
| [`specs/api-docs/api-baixas.md`](specs/api-docs/api-baixas.md) | Achados da API — baixa, estorno e exclusão de CAR/CAP. |
| [`specs/api-docs/api-limites.md`](specs/api-docs/api-limites.md) | Achados da API — webhooks e rate limit. |
| [`specs/loja-virtual.md`](specs/loja-virtual.md) | Loja virtual (Bling/Tray): acesso, temas, arquitetura do tema Padrão 3.0, Twig (o que funciona), edição via API do Studio e produtos ERP → loja. |
| [`specs/data.md`](specs/data.md) | Snapshots em `data/`, quem gera cada um, associação CAR→PV e gotchas de formato. |
| [`specs/templates.md`](specs/templates.md) | Templates canônicos de histórico. |
| [`specs/scripts.md`](specs/scripts.md) | **Referência de todos os scripts** + parâmetros (auto-gerado por `tools/gen_script_docs.py`). |

## Como navegar

- Vou usar/rodar um script: [`specs/scripts.md`](specs/scripts.md) + [`specs/overview.md`](specs/overview.md).
- Vou alterar dados na API: leia `specs/api-docs/` (CAR/PV/CAP/baixas) primeiro.
- Vou gerar/ler relatórios: [`specs/data.md`](specs/data.md) (formato) + [`specs/scripts.md`](specs/scripts.md).

> `specs/scripts.md` é gerado: edite a fonte (`META` em `tools/gen_script_docs.py` /
> docstrings dos scripts) e rode `python3 tools/gen_script_docs.py`.
