#!/usr/bin/env python3
"""Troca a categoria das CARs de PVs, preservando a forma de pagamento.

Se a forma da CAR estiver inativa, ela é reativada temporariamente para o PUT
e inativada de volta ao final (validado na API). Dry-run por padrão.

Plano (exemplo):
{
  "pvs":          {"2026010": 14734130713},   # número do PV -> categoria alvo
  "excluir_cars": [26644610113],
  "forma":        10378288                     # fallback p/ CAR sem forma
}

Uso: python3 scripts/apply_categorias_cars.py --plan plano.json [--execute]
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import DATA_DIR, associate_cars, car_put_body, load_json  # noqa: E402
from bling import BlingClient  # noqa: E402


def forma_situacao(client, forma_id):
    status, data = client.request("GET", f"/formas-pagamentos/{forma_id}")
    if status == 200 and isinstance(data, dict):
        return data["data"].get("situacao")
    return None


def main():
    ap = argparse.ArgumentParser(description="Troca categoria de CARs preservando a forma de pagamento.")
    ap.add_argument("--plan", required=True, help="plano JSON (pvs/excluir_cars/forma)")
    ap.add_argument("--data-dir", default=DATA_DIR, help="diretório dos snapshots")
    ap.add_argument("--forma", type=int, help="id de forma de pagamento fallback")
    ap.add_argument("--execute", action="store_true", help="aplica de fato (default: dry-run)")
    args = ap.parse_args()

    plan = load_json(args.plan)
    targets = {int(k): int(v) for k, v in (plan.get("pvs") or {}).items()}
    excluir = set(plan.get("excluir_cars") or [])
    fallback = args.forma or plan.get("forma")

    cars = load_json(os.path.join(args.data_dir, "contas_receber.json"))
    pvs = load_json(os.path.join(args.data_dir, "pedidos_venda.json"))
    _, car_ids_by_pv = associate_cars(cars, pvs, excluir=excluir)

    client = BlingClient()
    plan_rows, need_forms = [], set()
    for number, target in targets.items():
        for car_id in car_ids_by_pv.get(number, []):
            status, data = client.request("GET", f"/contas/receber/{car_id}")
            if status != 200:
                print("GET err", car_id, status)
                continue
            car = data["data"]
            cat = (car.get("categoria") or {}).get("id") or 0
            forma = (car.get("formaPagamento") or {}).get("id") or 0
            desired = forma or fallback
            if cat == target and forma == desired:
                continue
            plan_rows.append((car_id, target, desired, cat, forma))
            if desired:
                need_forms.add(desired)
            time.sleep(0.15)

    inactive = {f for f in need_forms if forma_situacao(client, f) != 1}
    print(f"CARs a corrigir: {len(plan_rows)} | formas a reativar: {sorted(inactive)}")
    for row in plan_rows:
        print("  ", row)
    for car_id, target, desired, cat, forma in plan_rows:
        if not desired:
            print(f"  ! CAR {car_id} sem forma de pagamento (use --forma)")

    if not args.execute:
        print("(dry-run; use --execute)")
        return

    reactivated = []
    for forma_id in sorted(inactive):
        status, data = client.request("GET", f"/formas-pagamentos/{forma_id}")
        if status != 200:
            print("GET form err", forma_id, status)
            continue
        forma = data["data"]
        if forma.get("situacao") != 1:
            forma["situacao"] = 1
            st, _ = client.request("PUT", f"/formas-pagamentos/{forma_id}", body=forma)
            print(f"reativar forma {forma_id} -> {st}")
            if st == 200:
                reactivated.append(forma_id)
        time.sleep(0.4)

    ok = 0
    for car_id, target, desired, cat, forma in plan_rows:
        if not desired:
            continue
        status, data = client.request("GET", f"/contas/receber/{car_id}")
        if status != 200:
            continue
        car = data["data"]
        car["categoria"] = {"id": target}
        car["formaPagamento"] = {"id": desired}
        st, _ = client.request("PUT", f"/contas/receber/{car_id}", body=car_put_body(car))
        if st in (200, 204):
            ok += 1
            print(f"CAR {car_id}: cat {cat}->{target} forma {desired} OK")
        else:
            print(f"CAR {car_id}: FALHA {st}")
        time.sleep(0.4)

    for forma_id in reactivated:
        status, data = client.request("GET", f"/formas-pagamentos/{forma_id}")
        if status == 200:
            forma = data["data"]
            forma["situacao"] = 0
            st, _ = client.request("PUT", f"/formas-pagamentos/{forma_id}", body=forma)
            print(f"inativar forma {forma_id} -> {st}")
        time.sleep(0.4)

    print(f"\nCARs atualizadas: {ok}/{len(plan_rows)} | formas reativadas: {reactivated}")


if __name__ == "__main__":
    main()
