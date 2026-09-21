#!/usr/bin/env python3
"""Salva os contatos citados em CARs/CAPs (incremental, retomável).

Evita repetir lookup de `contato.id` -> nome nos scripts de report.
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bling import BlingClient  # noqa: E402

OUT = os.path.join(ROOT, "data", "contatos.json")
FONTES = ["contas_receber.json", "contas_pagar.json"]

_client = None


def api(endpoint):
    global _client
    if _client is None:
        _client = BlingClient()
    status, data = _client.request("GET", endpoint)
    if status != 200:
        raise RuntimeError(f"GET {endpoint} -> {status}")
    return data


def ids_referenciados():
    ids = set()
    for nome in FONTES:
        path = os.path.join(ROOT, "data", nome)
        if not os.path.exists(path):
            continue
        for item in json.load(open(path, encoding="utf-8")):
            cid = (item.get("contato") or {}).get("id")
            if cid:
                ids.add(cid)
    return ids


# já coletados?
acumulado = {}
if os.path.exists(OUT):
    try:
        acumulado = json.load(open(OUT))
        print(f"Retomando: já há {len(acumulado)} contatos salvos", flush=True)
    except Exception:
        acumulado = {}

alvo = ids_referenciados()
print(f"Contatos referenciados em CAR/CAP: {len(alvo)}", flush=True)

faltantes = [i for i in alvo if str(i) not in acumulado]
print(f"Faltam detalhes de: {len(faltantes)}", flush=True)

for n, i in enumerate(faltantes):
    try:
        det = api(f"/contatos/{i}").get("data", {})
        acumulado[str(i)] = det
    except Exception as e:
        print(f"  erro id {i}: {e}", flush=True)
        time.sleep(1)
    if (n + 1) % 25 == 0:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(acumulado, f, ensure_ascii=False, indent=2)
        print(f"  {n+1}/{len(faltantes)} salvos ({len(acumulado)} total)", flush=True)
    time.sleep(0.02)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(acumulado, f, ensure_ascii=False, indent=2)
print(f"Concluído: {len(acumulado)} contatos em data/contatos.json", flush=True)
