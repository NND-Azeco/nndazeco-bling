#!/usr/bin/env python3
"""Gera specs/scripts.md a partir do docstring e do `--help` de cada script.

Uso: python3 tools/gen_script_docs.py

A descrição/entidade/saída vêm do META abaixo; os parâmetros são extraídos do
argparse de cada script (rodando `--help`), então não desatualizam. Não edite
specs/scripts.md à mão — rode este gerador.
"""
import ast
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
OUT = os.path.join(ROOT, "specs", "scripts.md")

VERBS = [
    ("fetch", "coleta / snapshots"),
    ("report", "relatórios"),
    ("apply", "ações que MUTAM dados na API"),
    ("check", "auditorias"),
    ("recreate", "recriação de entidades"),
    ("delete", "exclusões"),
    ("enrich", "complementa snapshots"),
]

# status: "atual" (padrão) | "legado" | "pendente"
META = {
    "fetch_all": dict(entity="— (orquestrador)", api="leitura", mutates="não",
                      output="`data/pedidos_venda.json`, `data/notas_fiscais.json`, `data/contas_receber.json`, `data/formas_pagamento.json`, `data/categorias_com_situacao.json`",
                      example="python3 scripts/fetch_all.py"),
    "fetch_pedidos_venda": dict(entity="pedidos de venda", api="leitura", mutates="não",
                                output="`data/pedidos_venda.json`",
                                example="python3 scripts/fetch_pedidos_venda.py"),
    "fetch_notas_fiscais": dict(entity="notas fiscais (PV → NF)", api="offline (leitura com `--live`)",
                                mutates="não", output="`data/notas_fiscais.json`",
                                params="`--live` — reconsulta cada PV na API (default: deriva do snapshot).\n\n_(sem argparse; lê `sys.argv`)_",
                                example="python3 scripts/fetch_notas_fiscais.py\npython3 scripts/fetch_notas_fiscais.py --live"),
    "fetch_contas_receber": dict(entity="contas a receber", api="leitura", mutates="não",
                                 output="`data/contas_receber.json`",
                                 example="python3 scripts/fetch_contas_receber.py"),
    "fetch_formas_pagamento": dict(entity="formas de pagamento", api="leitura", mutates="não",
                                   output="`data/formas_pagamento.json`",
                                   example="python3 scripts/fetch_formas_pagamento.py"),
    "fetch_categorias": dict(entity="categorias de receitas/despesas", api="leitura", mutates="não",
                             output="`data/categorias_com_situacao.json`",
                             example="python3 scripts/fetch_categorias.py"),
    "fetch_contas_pagar": dict(entity="contas a pagar", api="leitura", mutates="não",
                               output="`data/contas_pagar.json`",
                               example="python3 scripts/fetch_contas_pagar.py",
                               status="legado (não usa `BlingClient`; migrar)"),
    "fetch_artista": dict(entity="artista (obras + PV + CAP)", api="leitura", mutates="não",
                          output="`data/artista_<slug>.json`",
                          example="python3 scripts/fetch_artista.py --nome \"Lázaro Roberto\" \\\n"
                                  "  --contato 18220750384 --categoria 14734724294 --codigo-regex '^LRO?[\\-0-9]'",
                          status="pendente (filtro de janela em /contas/pagar retorna 400)"),
    "enrich_snapshot": dict(entity="—", api="leitura", mutates="não",
                            output="o próprio `--file` (in-place)",
                            example="python3 scripts/enrich_snapshot.py --file data/artista_lazaro_roberto.json"),
    "report_cars": dict(entity="CARs por PV", api="offline", mutates="não",
                        output="`report_cars_por_pv.md`, `report_cars_sem_pv.md`",
                        example="python3 scripts/report_cars.py"),
    "report_artista": dict(entity="artista (obras + CAP + CAR)", api="offline", mutates="não",
                           output="`report_<slug>.md`",
                           example="python3 scripts/report_artista.py --file data/artista_lazaro_roberto.json \\\n"
                                   "  --contato 18220750384 --categoria-repasse 14734724294 \\\n"
                                   "  --categoria-comissao 14730836888 --codigo-regex '^LRO?[\\-0-9]' \\\n"
                                   "  --nome \"Lázaro\" --titulo \"Lázaro Roberto\" --out report_lazaro_roberto.md"),
    "apply_categorias": dict(entity="PVs + CARs", api="escrita", mutates="sim",
                             output="backup em `backups/backups_categorias_<ts>/`",
                             example="python3 scripts/apply_categorias.py --plan plano.json        # dry-run\n"
                                     "python3 scripts/apply_categorias.py --plan plano.json --execute"),
    "apply_categorias_cars": dict(entity="CARs", api="escrita", mutates="sim",
                                  output="—",
                                  example="python3 scripts/apply_categorias_cars.py --plan plano.json --execute"),
    "apply_categorias_cap": dict(entity="CAPs", api="escrita", mutates="sim",
                                 output="backup em `backups/backups_categorias_cap_<ts>/`",
                                 example="python3 scripts/apply_categorias_cap.py --plan plano.json        # dry-run\n"
                                         "python3 scripts/apply_categorias_cap.py --plan plano.json --execute"),
    "apply_historico": dict(entity="CAPs ou CARs (histórico)", api="escrita", mutates="sim",
                            output="backup em `backups/backups_historico_<entidade>_<ts>/` (+ `formas_reativadas.json`)",
                            example="python3 scripts/apply_historico.py --entidade cap --plan plano.json        # dry-run\n"
                                    "python3 scripts/apply_historico.py --entidade cap --plan plano.json --ids 123,456 --execute"),
    "apply_produtos": dict(entity="produtos (obras) + saldo + fornecedor", api="escrita", mutates="sim",
                           output="ids criados em `backups/backups_produtos_<ts>/criados.json`",
                           example="python3 scripts/apply_produtos.py --plan plano_produtos.json        # dry-run\n"
                                   "python3 scripts/apply_produtos.py --plan plano_produtos.json --execute"),
    "apply_template1_cars": dict(entity="CARs (histórico)", api="escrita", mutates="sim",
                                 output="—",
                                 example="python3 scripts/apply_template1_cars.py --plan plano.json --execute"),
    "apply_renomear_pv_historico": dict(entity="CARs (histórico)", api="escrita", mutates="sim",
                                        output="—",
                                        example="python3 scripts/apply_renomear_pv_historico.py --map mapa_pv.json\n"
                                                "python3 scripts/apply_renomear_pv_historico.py --map mapa_pv.json --execute"),
    "recreate_pv": dict(entity="pedido de venda", api="escrita", mutates="sim", output="—",
                        example="python3 scripts/recreate_pv.py --backup backups/.../pv_2026028.json --vendedor 15596924706\n"
                                "python3 scripts/recreate_pv.py --backup ... --vendedor ... --execute"),
    "check_lancamentos_artistas": dict(entity="CAPs por grupo de categoria", api="leitura", mutates="não",
                                       output="stdout",
                                       example="python3 scripts/check_lancamentos_artistas.py --grupos grupos.json"),
    "check_duplicacao_lancamentos": dict(entity="CAPs duplicados entre 2 grupos", api="leitura", mutates="não",
                                         output="stdout",
                                         example="python3 scripts/check_duplicacao_lancamentos.py --a grupo_a.json --b grupo_b.json"),
}


def first_doc_line(path):
    try:
        doc = ast.get_docstring(ast.parse(open(path, encoding="utf-8").read())) or ""
    except Exception:
        return ""
    return doc.strip().splitlines()[0].strip() if doc.strip() else ""


def help_output(path):
    """Roda `--help` e devolve a saída (só p/ scripts com argparse)."""
    try:
        proc = subprocess.run(
            [sys.executable, path, "--help"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONPATH": ROOT},
        )
        out = (proc.stdout or "").strip()
        return out or (proc.stderr or "").strip()
    except Exception as exc:  # noqa: BLE001
        return f"(erro ao obter --help: {exc})"


def section(stem, path):
    meta = META.get(stem, {})
    purpose = first_doc_line(path)
    src = open(path, encoding="utf-8").read()
    status = meta.get("status")

    lines = [f"### `{stem}.py`", ""]
    if purpose:
        lines.append(purpose)
        lines.append("")
    header_bits = []
    if meta.get("entity"):
        header_bits.append(f"**Entidade:** {meta['entity']}")
    if meta.get("api"):
        header_bits.append(f"**API:** {meta['api']}")
    if meta.get("mutates"):
        header_bits.append(f"**Muta dados:** {meta['mutates']}")
    if header_bits:
        lines.append(" · ".join(header_bits))
    if meta.get("output"):
        lines.append(f"- **Saída:** {meta['output']}")
    if status:
        lines.append(f"- **Status:** ⚠ {status}")
    if meta.get("example"):
        lines.append("- **Exemplo:**")
        lines.append("")
        lines.append("  ```bash")
        for ln in meta["example"].splitlines():
            lines.append("  " + ln)
        lines.append("  ```")
    lines.append("")

    if meta.get("params"):
        lines += ["**Parâmetros:**", "", meta["params"]]
    elif "add_argument" in src:
        lines += ["**Parâmetros:**", "", "```text", help_output(path), "```"]
    else:
        lines.append("**Parâmetros:** _(nenhum — comportamento fixo)_")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    stems = sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(SCRIPTS, "*.py")))
    stems = [s for s in stems if s != "_common"]

    lst = []
    lst.append("# Referência dos scripts")
    lst.append("")
    lst.append("> Gerado por `tools/gen_script_docs.py` — **não editar à mão**.")
    lst.append("> Os parâmetros são extraídos do `argparse` de cada script (`--help`).")
    lst.append("> Cada script vai do heading `### nome.py` até o `---` seguinte.")
    lst.append("")
    lst.append("Convenção de nome dos scripts: ver [`writing-scripts.md`](writing-scripts.md#nomenclatura).")
    lst.append("")

    for verb, desc in VERBS:
        group = [s for s in stems if s.startswith(verb + "_")]
        if not group:
            continue
        lst.append(f"## `{verb}_` — {desc}")
        lst.append("")
        for stem in group:
            lst.append(section(stem, os.path.join(SCRIPTS, f"{stem}.py")))

    others = [s for s in stems if not any(s.startswith(v + "_") for v, _ in VERBS)]
    if others:
        lst.append("## Outros")
        lst.append("")
        for stem in others:
            lst.append(section(stem, os.path.join(SCRIPTS, f"{stem}.py")))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lst).rstrip() + "\n")
    print("gerou", OUT, f"({len(stems)} scripts)")


if __name__ == "__main__":
    main()
