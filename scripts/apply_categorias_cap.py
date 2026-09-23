#!/usr/bin/env python3
"""Aplica categoria financeira em CAPs conforme um plano JSON. Dry-run por padrão.

Se a forma de pagamento da CAP estiver inativa, reativa em lote antes do PUT e
restaura a situação original ao final (mesmo padrão de apply_categorias_cars.py).

Plano (exemplo):
{
  "26709248753": 14734724294,
  "26709248754": 14734724294
}
(chave = id da CAP, valor = id da categoria alvo)

Uso: python3 scripts/apply_categorias_cap.py --plan plano.json        # dry-run
     python3 scripts/apply_categorias_cap.py --plan plano.json --execute
Backups em backups/backups_categorias_cap_<ts>/.
"""
import argparse
import datetime
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import BACKUPS_DIR, cap_put_body, load_json, save_json  # noqa: E402
from bling import BlingClient  # noqa: E402


def forma_situacao(client, forma_id):
    status, data = client.request("GET", f"/formas-pagamentos/{forma_id}")
    if status == 200 and isinstance(data, dict):
        return data["data"].get("situacao")
    return None


def main():
    ap = argparse.ArgumentParser(description="Aplica categoria em CAPs a partir de um plano JSON.")
    ap.add_argument("--plan", required=True, help="plano JSON {capId: categoriaId}")
    ap.add_argument("--execute", action="store_true", help="aplica de fato (default: dry-run)")
    ap.add_argument("--sleep", type=float, default=0.4, help="pausa entre chamadas (s)")
    args = ap.parse_args()

    plan = load_json(args.plan)
    targets = {int(k): int(v) for k, v in plan.items()}

    client = BlingClient()

    # fase 1: ler ao vivo, montar plano (pula no-ops), detectar formas envolvidas
    plan_rows, need_forms = [], set()
    for cap_id, target in targets.items():
        status, data = client.request("GET", f"/contas/pagar/{cap_id}")
        if status != 200:
            print(f"GET err {cap_id} -> {status}")
            continue
        cap = data["data"]
        current = (cap.get("categoria") or {}).get("id") or 0
        forma = (cap.get("formaPagamento") or {}).get("id") or 0
        if current == target:
            continue
        plan_rows.append((cap_id, target, current, forma))
        if forma:
            need_forms.add(forma)
        time.sleep(args.sleep / 2)

    inactive = {f for f in need_forms if forma_situacao(client, f) != 1}
    print(f"CAPs a corrigir: {len(plan_rows)} | formas a reativar: {sorted(inactive)}")
    for row in plan_rows:
        print("  ", row)

    if not args.execute:
        print("(dry-run; use --execute)")
        return

    # fase 2: reativar formas inativas em lote
    reactivated = []
    for forma_id in sorted(inactive):
        status, data = client.request("GET", f"/formas-pagamentos/{forma_id}")
        if status != 200:
            print("GET forma err", forma_id, status)
            continue
        forma = data["data"]
        if forma.get("situacao") != 1:
            forma["situacao"] = 1
            st, _ = client.request("PUT", f"/formas-pagamentos/{forma_id}", body=forma)
            print(f"reativar forma {forma_id} -> {st}")
            if st == 200:
                reactivated.append(forma_id)
        time.sleep(args.sleep)

    # fase 3: backup + PUT
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(BACKUPS_DIR, f"backups_categorias_cap_{ts}")
    os.makedirs(outdir, exist_ok=True)

    ok = 0
    falhas = []
    for cap_id, target, current, forma in plan_rows:
        status, data = client.request("GET", f"/contas/pagar/{cap_id}")
        if status != 200:
            print(f"  GET err {cap_id} -> {status}")
            falhas.append(cap_id)
            continue
        cap = data["data"]
        if (cap.get("categoria") or {}).get("id") == target:
            continue  # mudou entre a fase 1 e agora
        save_json(os.path.join(outdir, f"cap_{cap_id}.json"), cap, indent=1)
        cap["categoria"] = {"id": target}
        st, body = client.request("PUT", f"/contas/pagar/{cap_id}", body=cap_put_body(cap))
        if st in (200, 204):
            ok += 1
            print(f"CAP {cap_id}: cat {current}->{target} PUT {st}")
        else:
            falhas.append(cap_id)
            print(f"CAP {cap_id}: FALHA {st} — {body}")
        time.sleep(args.sleep)

    # fase 4: restaurar formas reativadas
    for forma_id in reactivated:
        status, data = client.request("GET", f"/formas-pagamentos/{forma_id}")
        if status == 200:
            forma = data["data"]
            forma["situacao"] = 0
            st, _ = client.request("PUT", f"/formas-pagamentos/{forma_id}", body=forma)
            print(f"inativar forma {forma_id} -> {st}")
        time.sleep(args.sleep)

    print(f"\naplicado em {ok}/{len(plan_rows)} | formas reativadas: {reactivated}")
    if falhas:
        print("falharam:", falhas)
    print("backups:", outdir)


if __name__ == "__main__":
    main()
