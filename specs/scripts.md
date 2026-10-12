# Referência dos scripts

> Gerado por `tools/gen_script_docs.py` — **não editar à mão**.
> Os parâmetros são extraídos do `argparse` de cada script (`--help`).
> Cada script vai do heading `### nome.py` até o `---` seguinte.

Convenção de nome dos scripts: ver [`writing-scripts.md`](writing-scripts.md#nomenclatura).

## `fetch_` — coleta / snapshots

### `fetch_all.py`

Orquestra a coleta de todos os snapshots.

**Entidade:** — (orquestrador) · **API:** leitura · **Muta dados:** não
- **Saída:** `data/pedidos_venda.json`, `data/notas_fiscais.json`, `data/contas_receber.json`, `data/formas_pagamento.json`, `data/categorias_com_situacao.json`
- **Exemplo:**

  ```bash
  python3 scripts/fetch_all.py
  ```

**Parâmetros:** _(nenhum — comportamento fixo)_

---

### `fetch_artista.py`

Coleta os dados de um artista (obras, pedidos de venda e contas a pagar).

**Entidade:** artista (obras + PV + CAP) · **API:** leitura · **Muta dados:** não
- **Saída:** `data/artista_<slug>.json`
- **Status:** ⚠ pendente (filtro de janela em /contas/pagar retorna 400)
- **Exemplo:**

  ```bash
  python3 scripts/fetch_artista.py --nome "Lázaro Roberto" \
    --contato 18220750384 --categoria 14734724294 --codigo-regex '^LRO?[\-0-9]'
  ```

**Parâmetros:**

```text
usage: fetch_artista.py [-h] --nome NOME [--contato CONTATO]
                        [--categoria CATEGORIA] [--codigo-regex CODIGO_REGEX]
                        [--desde DESDE] [--output OUTPUT] [--sleep SLEEP]

Coleta dados de um artista no Bling.

options:
  -h, --help            show this help message and exit
  --nome NOME           nome do artista (busca textual)
  --contato CONTATO     id do contato do artista
  --categoria CATEGORIA
                        id de categoria de repasse (repetível)
  --codigo-regex CODIGO_REGEX
                        regex para código de produto/item
  --desde DESDE         início da janela de CAPs (YYYY-MM-DD)
  --output OUTPUT       arquivo de saída (default: data/artista_<slug>.json)
  --sleep SLEEP         pausa entre chamadas (s)
```

---

### `fetch_categorias.py`

Busca as categorias de receitas/despesas (lista + detalhe com `situacao`).

**Entidade:** categorias de receitas/despesas · **API:** leitura · **Muta dados:** não
- **Saída:** `data/categorias_com_situacao.json`
- **Exemplo:**

  ```bash
  python3 scripts/fetch_categorias.py
  ```

**Parâmetros:** _(nenhum — comportamento fixo)_

---

### `fetch_contas_pagar.py`

Salva lançamentos de contas a pagar (incremental, retomável).

**Entidade:** contas a pagar · **API:** leitura · **Muta dados:** não
- **Saída:** `data/contas_pagar.json`
- **Status:** ⚠ legado (não usa `BlingClient`; migrar)
- **Exemplo:**

  ```bash
  python3 scripts/fetch_contas_pagar.py
  ```

**Parâmetros:** _(nenhum — comportamento fixo)_

---

### `fetch_contas_receber.py`

Busca contas a receber (lista + detalhe) e grava data/contas_receber.json.

**Entidade:** contas a receber · **API:** leitura · **Muta dados:** não
- **Saída:** `data/contas_receber.json`
- **Exemplo:**

  ```bash
  python3 scripts/fetch_contas_receber.py
  ```

**Parâmetros:** _(nenhum — comportamento fixo)_

---

### `fetch_contatos.py`

Salva os contatos citados em CARs/CAPs (incremental, retomável).


**Parâmetros:** _(nenhum — comportamento fixo)_

---

### `fetch_formas_pagamento.py`

Busca as formas de pagamento (lista + detalhe com `destino`) em data/formas_pagamento.json.

**Entidade:** formas de pagamento · **API:** leitura · **Muta dados:** não
- **Saída:** `data/formas_pagamento.json`
- **Exemplo:**

  ```bash
  python3 scripts/fetch_formas_pagamento.py
  ```

**Parâmetros:** _(nenhum — comportamento fixo)_

---

### `fetch_notas_fiscais.py`

Extrai o vínculo PV -> Nota Fiscal e grava data/notas_fiscais.json.

**Entidade:** notas fiscais (PV → NF) · **API:** offline (leitura com `--live`) · **Muta dados:** não
- **Saída:** `data/notas_fiscais.json`
- **Exemplo:**

  ```bash
  python3 scripts/fetch_notas_fiscais.py
  python3 scripts/fetch_notas_fiscais.py --live
  ```

**Parâmetros:**

`--live` — reconsulta cada PV na API (default: deriva do snapshot).

_(sem argparse; lê `sys.argv`)_

---

### `fetch_pedidos_compra.py`

Busca pedidos de compra (lista + detalhe) e grava data/pedidos_compra.json.


**Parâmetros:** _(nenhum — comportamento fixo)_

---

### `fetch_pedidos_venda.py`

Busca pedidos de venda (lista + detalhe) e grava data/pedidos_venda.json.

**Entidade:** pedidos de venda · **API:** leitura · **Muta dados:** não
- **Saída:** `data/pedidos_venda.json`
- **Exemplo:**

  ```bash
  python3 scripts/fetch_pedidos_venda.py
  ```

**Parâmetros:** _(nenhum — comportamento fixo)_

---

## `report_` — relatórios

### `report_artista.py`

Relatório de um artista: catálogo de obras + contas a pagar + contas a receber.

**Entidade:** artista (obras + CAP + CAR) · **API:** offline · **Muta dados:** não
- **Saída:** `report_<slug>.md`
- **Exemplo:**

  ```bash
  python3 scripts/report_artista.py --file data/artista_lazaro_roberto.json \
    --contato 18220750384 --categoria-repasse 14734724294 \
    --categoria-comissao 14730836888 --codigo-regex '^LRO?[\-0-9]' \
    --nome "Lázaro" --titulo "Lázaro Roberto" --out report_lazaro_roberto.md
  ```

**Parâmetros:**

```text
usage: report_artista.py [-h] --file FILE [--contato CONTATO]
                         [--categoria-repasse CATEGORIA_REPASSE]
                         [--categoria-comissao CATEGORIA_COMISSAO]
                         [--codigo-regex CODIGO_REGEX] [--nome NOME]
                         [--data-dir DATA_DIR] [--titulo TITULO] [--out OUT]
                         [--notas NOTAS]

Relatório de um artista (obras + CAP + CAR).

options:
  -h, --help            show this help message and exit
  --file FILE           snapshot bruto do artista (fetch_artista)
  --contato CONTATO     id do contato do artista
  --categoria-repasse CATEGORIA_REPASSE
                        categoria de repasse ao artista
  --categoria-comissao CATEGORIA_COMISSAO
                        categoria de comissão (repetível)
  --codigo-regex CODIGO_REGEX
                        regex do código de produto/item (obras do artista)
  --nome NOME           termos de busca textual (nome do artista)
  --data-dir DATA_DIR   diretório dos snapshots globais (CARs/PVs)
  --titulo TITULO       título do relatório (default: nome do artista)
  --out OUT             arquivo de saída .md
  --notas NOTAS         arquivo .md com observações a anexar no fim
```

---

### `report_caps.py`

Gera report_caps_por_pc.md e report_caps_sem_pc.md a partir de snapshots ao vivo.


**Parâmetros:**

```text
usage: report_caps.py [-h] [--data-dir DATA_DIR] [--out-dir OUT_DIR]
                      [--titulo TITULO]

Gera os relatórios de CAPs por PC / sem PC.

options:
  -h, --help           show this help message and exit
  --data-dir DATA_DIR  diretório dos snapshots
  --out-dir OUT_DIR    diretório de saída dos relatórios
  --titulo TITULO      título dos relatórios
```

---

### `report_cars.py`

Gera report_cars_por_pv.md e report_cars_sem_pv.md a partir de snapshots ao vivo.

**Entidade:** CARs por PV · **API:** offline · **Muta dados:** não
- **Saída:** `report_cars_por_pv.md`, `report_cars_sem_pv.md`
- **Exemplo:**

  ```bash
  python3 scripts/report_cars.py
  ```

**Parâmetros:**

```text
usage: report_cars.py [-h] [--data-dir DATA_DIR] [--out-dir OUT_DIR]
                      [--titulo TITULO]

Gera os relatórios de CARs por PV / sem PV.

options:
  -h, --help           show this help message and exit
  --data-dir DATA_DIR  diretório dos snapshots
  --out-dir OUT_DIR    diretório de saída dos relatórios
  --titulo TITULO      título dos relatórios
```

---

## `apply_` — ações que MUTAM dados na API

### `apply_categorias.py`

Aplica categorias em PVs e CARs conforme um plano JSON. Dry-run por padrão.

**Entidade:** PVs + CARs · **API:** escrita · **Muta dados:** sim
- **Saída:** backup em `backups/backups_categorias_<ts>/`
- **Exemplo:**

  ```bash
  python3 scripts/apply_categorias.py --plan plano.json        # dry-run
  python3 scripts/apply_categorias.py --plan plano.json --execute
  ```

**Parâmetros:**

```text
usage: apply_categorias.py [-h] --plan PLAN [--data-dir DATA_DIR] [--execute]

Aplica categorias em PVs/CARs a partir de um plano JSON.

options:
  -h, --help           show this help message and exit
  --plan PLAN          plano JSON (pvs/pv_only/excluir_cars)
  --data-dir DATA_DIR  diretório dos snapshots
  --execute            aplica de fato (default: dry-run)
```

---

### `apply_categorias_cap.py`

Aplica categoria financeira em CAPs conforme um plano JSON. Dry-run por padrão.

**Entidade:** CAPs · **API:** escrita · **Muta dados:** sim
- **Saída:** backup em `backups/backups_categorias_cap_<ts>/`
- **Exemplo:**

  ```bash
  python3 scripts/apply_categorias_cap.py --plan plano.json        # dry-run
  python3 scripts/apply_categorias_cap.py --plan plano.json --execute
  ```

**Parâmetros:**

```text
usage: apply_categorias_cap.py [-h] --plan PLAN [--execute] [--sleep SLEEP]

Aplica categoria em CAPs a partir de um plano JSON.

options:
  -h, --help     show this help message and exit
  --plan PLAN    plano JSON {capId: categoriaId}
  --execute      aplica de fato (default: dry-run)
  --sleep SLEEP  pausa entre chamadas (s)
```

---

### `apply_categorias_cars.py`

Troca a categoria das CARs de PVs, preservando a forma de pagamento.

**Entidade:** CARs · **API:** escrita · **Muta dados:** sim
- **Saída:** —
- **Exemplo:**

  ```bash
  python3 scripts/apply_categorias_cars.py --plan plano.json --execute
  ```

**Parâmetros:**

```text
usage: apply_categorias_cars.py [-h] --plan PLAN [--data-dir DATA_DIR]
                                [--forma FORMA] [--execute]

Troca categoria de CARs preservando a forma de pagamento.

options:
  -h, --help           show this help message and exit
  --plan PLAN          plano JSON (pvs/excluir_cars/forma)
  --data-dir DATA_DIR  diretório dos snapshots
  --forma FORMA        id de forma de pagamento fallback
  --execute            aplica de fato (default: dry-run)
```

---

### `apply_produtos.py`

Cadastra produtos (obras) no ERP a partir de um plano JSON. Dry-run por padrão.

**Entidade:** produtos (obras) + saldo + fornecedor · **API:** escrita · **Muta dados:** sim
- **Saída:** ids criados em `backups/backups_produtos_<ts>/criados.json`
- **Exemplo:**

  ```bash
  python3 scripts/apply_produtos.py --plan plano_produtos.json        # dry-run
  python3 scripts/apply_produtos.py --plan plano_produtos.json --execute
  ```

**Parâmetros:**

```text
usage: apply_produtos.py [-h] --plan PLAN [--codes CODES] [--sleep SLEEP]
                         [--execute]

Cadastra produtos no ERP a partir de um plano JSON.

options:
  -h, --help     show this help message and exit
  --plan PLAN    JSON com a lista de produtos
  --codes CODES  códigos a processar (csv); default: todos do plano
  --sleep SLEEP  intervalo entre chamadas à API
  --execute      cria de fato (default: dry-run)
```

---

### `apply_renomear_pv_historico.py`

Reescreve a numeração antiga de PV no histórico de CARs. Dry-run por padrão.

**Entidade:** CARs (histórico) · **API:** escrita · **Muta dados:** sim
- **Saída:** —
- **Exemplo:**

  ```bash
  python3 scripts/apply_renomear_pv_historico.py --map mapa_pv.json
  python3 scripts/apply_renomear_pv_historico.py --map mapa_pv.json --execute
  ```

**Parâmetros:**

```text
usage: apply_renomear_pv_historico.py [-h] --map MAP [--cars CARS]
                                      [--data-dir DATA_DIR] [--execute]

Renomeia a numeração antiga de PV no histórico de CARs.

options:
  -h, --help           show this help message and exit
  --map MAP            JSON {numero_antigo: numero_novo}
  --cars CARS          ids de CAR (csv); default: todas do snapshot que casem
                       o mapa
  --data-dir DATA_DIR  diretório dos snapshots
  --execute            aplica de fato (default: dry-run)
```

---

### `apply_template1_cars.py`

Aplica o Template 1 (histórico) nas CARs de uma lista de PVs. Dry-run por padrão.

**Entidade:** CARs (histórico) · **API:** escrita · **Muta dados:** sim
- **Saída:** —
- **Exemplo:**

  ```bash
  python3 scripts/apply_template1_cars.py --plan plano.json --execute
  ```

**Parâmetros:**

```text
usage: apply_template1_cars.py [-h] --plan PLAN [--data-dir DATA_DIR]
                               [--template TEMPLATE]
                               [--excluir-regex EXCLUIR_REGEX] [--execute]

Aplica o Template 1 de histórico nas CARs de PVs.

options:
  -h, --help            show this help message and exit
  --plan PLAN           plano JSON (pvs/cars_manuais/excluir_regex)
  --data-dir DATA_DIR   diretório dos snapshots
  --template TEMPLATE   arquivo com o template do histórico
                        ({numero},{obras},...)
  --excluir-regex EXCLUIR_REGEX
                        regex p/ excluir descrições de itens das 'Obras'
  --execute             aplica de fato (default: dry-run)
```

---

## `check_` — auditorias

### `check_duplicacao_lancamentos.py`

Detecta lançamentos duplicados entre dois grupos de categorias.

**Entidade:** CAPs duplicados entre 2 grupos · **API:** leitura · **Muta dados:** não
- **Saída:** stdout
- **Exemplo:**

  ```bash
  python3 scripts/check_duplicacao_lancamentos.py --a grupo_a.json --b grupo_b.json
  ```

**Parâmetros:**

```text
usage: check_duplicacao_lancamentos.py [-h] --a A --b B

Duplicatas de lançamentos entre dois grupos de categorias.

options:
  -h, --help  show this help message and exit
  --a A       JSON {categoria_id: rótulo} do grupo A
  --b B       JSON {categoria_id: rótulo} do grupo B
```

---

### `check_lancamentos_artistas.py`

Lista Contas a Pagar de um ou mais grupos de categorias.

**Entidade:** CAPs por grupo de categoria · **API:** leitura · **Muta dados:** não
- **Saída:** stdout
- **Exemplo:**

  ```bash
  python3 scripts/check_lancamentos_artistas.py --grupos grupos.json
  ```

**Parâmetros:**

```text
usage: check_lancamentos_artistas.py [-h] [--grupos GRUPOS]
                                     [--categoria CATEGORIA]

Lista CAPs de grupos de categorias.

options:
  -h, --help            show this help message and exit
  --grupos GRUPOS       JSON {categoria_id: rótulo}
  --categoria CATEGORIA
                        id de categoria (repetível)
```

---

## `recreate_` — recriação de entidades

### `recreate_pv.py`

Recria um Pedido de Venda preservando dados: GET (backup) -> DELETE -> POST (numero fixo) -> lancar-contas.

**Entidade:** pedido de venda · **API:** escrita · **Muta dados:** sim
- **Saída:** —
- **Exemplo:**

  ```bash
  python3 scripts/recreate_pv.py --backup backups/.../pv_2026028.json --vendedor 15596924706
  python3 scripts/recreate_pv.py --backup ... --vendedor ... --execute
  ```

**Parâmetros:**

```text
usage: recreate_pv.py [-h] --backup BACKUP [--vendedor VENDEDOR]
                      [--forma FORMA] [--execute]

options:
  -h, --help           show this help message and exit
  --backup BACKUP
  --vendedor VENDEDOR
  --forma FORMA
  --execute
```

---

## `enrich_` — complementa snapshots

### `enrich_snapshot.py`

Enriquece um snapshot bruto com mapas de nomes (contatos, categorias,

**Entidade:** — · **API:** leitura · **Muta dados:** não
- **Saída:** o próprio `--file` (in-place)
- **Exemplo:**

  ```bash
  python3 scripts/enrich_snapshot.py --file data/artista_lazaro_roberto.json
  ```

**Parâmetros:**

```text
usage: enrich_snapshot.py [-h] --file FILE

Enriquece um snapshot bruto com lookups de nome.

options:
  -h, --help   show this help message and exit
  --file FILE  snapshot JSON a enriquecer (in-place)
```

---
