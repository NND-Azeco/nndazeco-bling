#!/usr/bin/env python3
"""Monta o plano de histórico do Template 5 (Despesas com Exposição) p/ scripts/apply_historico.py.

Junta {capId: "EXP-..."} (--expos) com {capId: descrição} (--descricoes) e grava
{capId: "| Exposição: EXP-...\\n| Descrição: ..."} (--out). Falha se as listas não baterem
ou se alguma descrição estiver vazia.

Uso: python3 tools/gen_plano_template5.py --expos expos.json \\
       --descricoes descricoes_template5.json --out plano_historico_template5.json
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from _common import load_json, save_json, template5_historico  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Monta o plano de histórico do Template 5.")
    ap.add_argument("--expos", required=True, help="JSON {capId: ID de exposição}")
    ap.add_argument("--descricoes", required=True, help="JSON {capId: descrição}")
    ap.add_argument("--out", required=True, help="plano de saída {capId: histórico novo}")
    args = ap.parse_args()

    expos = {str(k): v for k, v in load_json(args.expos).items()}
    descricoes = {str(k): v for k, v in load_json(args.descricoes).items()}
    sem_desc = sorted(set(expos) - set(descricoes))
    sem_expo = sorted(set(descricoes) - set(expos))
    vazias = sorted(k for k, v in descricoes.items() if not (v or "").strip())
    if sem_desc or sem_expo or vazias:
        sys.exit(f"inconsistente — sem descrição: {sem_desc} | sem exposição: {sem_expo} | vazias: {vazias}")

    plano = {k: template5_historico(expos[k], descricoes[k].strip()) for k in expos}
    save_json(args.out, plano, indent=2)
    print(f"gravou {args.out} ({len(plano)} CAPs)")


if __name__ == "__main__":
    main()
