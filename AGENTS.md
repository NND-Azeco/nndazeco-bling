# AGENTS.md — nnd-azeco-bling

**Documentação:** índice humano no [`README.md`](README.md); a IA navega pelo mapa abaixo.
**Contexto local não versionado** (PDFs, docs de apoio): `_context/`.

## Regras críticas (leia sempre)

- Credenciais vêm do `.env`. Token renova sozinho (`python3 -m bling` / `BlingClient`).
- **Revalidar ao vivo** antes de decisões — snapshots são referência.
- Ações que mutam dados são **dry-run por padrão**; rodar o dry-run, revisar e só então
  `--execute`. **Pedir confirmação antes de ações destrutivas** (excluir/estornar/recategorizar).

## Comandos rápidos

```bash
python3 scripts/fetch_all.py                # atualiza snapshots em data/
python3 scripts/report_cars.py              # relatórios de CARs por PV
python3 tools/gen_script_docs.py            # regenera specs/scripts.md
```

## Scripts (`scripts/`)

- `fetch_*`: `fetch_all`, `fetch_pedidos_venda`, `fetch_notas_fiscais`, `fetch_contas_receber`,
  `fetch_contas_pagar`, `fetch_formas_pagamento`, `fetch_categorias`, `fetch_artista`
- `report_*`: `report_cars`, `report_artista`
- `apply_*`: `apply_categorias`, `apply_categorias_cars`, `apply_categorias_cap`, `apply_template1_cars`, `apply_renomear_pv_historico`
- `check_*`: `check_lancamentos_artistas`, `check_duplicacao_lancamentos`
- outros: `recreate_pv`, `enrich_snapshot` · helper interno: `_common`

## Mapa de leitura (abra sob demanda — não leia tudo)

| Precisa de... | Abrir |
|---|---|
| Visão geral, setup, CLI | `specs/overview.md` |
| Convenções pra escrever um script novo | `specs/writing-scripts.md` |
| Convenções de mensagem de commit | `specs/committing.md` |
| Campos/formato dos JSON em `data/` e associação CAR→PV | `specs/data.md` |
| API (`specs/api-docs/`) | `api-cars.md` CAR/`lancar-contas`/NF · `api-pv.md` recriar/editar PV · `api-cap.md` pedido de compra→CAP · `api-baixas.md` baixa/estorno/exclusão · `api-limites.md` webhooks/rate limit |
| Textos de histórico (templates) | `specs/templates.md` |
| Flags/args de um script | a seção dele em `specs/scripts.md` (comando abaixo) |

`specs/scripts.md` é auto-gerado: cada script vai do heading `### nome.py` até o `---`
seguinte — extraia só a seção:

```bash
sed -n '/^### `report_cars.py`$/,/^---$/p' specs/scripts.md
```

Abra spec só quando a tarefa exigir; evite abrir "por precaução".
**Alvo conhecido → leia direto** (mapa acima); **varredura ampla/desconhecida** no código →
subagente `explore` (isola o contexto; só o resumo volta).
