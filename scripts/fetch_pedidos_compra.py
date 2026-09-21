#!/usr/bin/env python3
"""Busca pedidos de compra (lista + detalhe) e grava data/pedidos_compra.json.

Uso: python3 scripts/fetch_pedidos_compra.py
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bling import BlingClient  # noqa: E402

OUT = os.path.join(ROOT, "data", "pedidos_compra.json")


def fetch(client, sleep=0.25):
    """Lista os PCs e busca o detalhe de cada um."""
    pcs = client.paginate("/pedidos/compras")
    detalhes = []
    for i, pc in enumerate(pcs, 1):
        status, data = client.get(f"/pedidos/compras/{pc['id']}")
        if status == 200 and isinstance(data, dict):
            detalhes.append(data["data"])
        else:
            print(f"  ! PC {pc.get('id')} -> {status}", flush=True)
        if i % 25 == 0:
            print(f"  detalhes {i}/{len(pcs)}", flush=True)
        time.sleep(sleep)
    return detalhes


def snapshot(det):
    """Reduz o detalhe a um snapshot enxuto (compatível com os relatórios)."""
    f = det.get("fornecedor") or {}
    s = det.get("situacao") or {}
    return {
        "id": det["id"], "numero": det.get("numero"),
        "data": det.get("data"), "dataPrevista": det.get("dataPrevista"),
        "totalProdutos": det.get("totalProdutos"), "total": det.get("total"),
        "fornecedor": {"id": f.get("id")},
        "situacao": {"id": s.get("id"), "valor": s.get("valor")},
        "desconto": det.get("desconto"), "itens": det.get("itens"), "parcelas": det.get("parcelas"),
        "categoria": det.get("categoria"),
    }


def main():
    client = BlingClient()
    print("1) PCs (lista + detalhe)...", flush=True)
    detalhes = fetch(client)
    pcs = [snapshot(d) for d in detalhes]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(pcs, f, ensure_ascii=False, indent=1)
    print(f"gravou {OUT} ({len(pcs)})", flush=True)


if __name__ == "__main__":
    main()
