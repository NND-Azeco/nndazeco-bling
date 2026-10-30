#!/usr/bin/env python3
"""Reescreve o histórico de CAPs ou CARs conforme um plano JSON. Dry-run por padrão.

Plano (exemplo): chave = id do lançamento, valor = histórico COMPLETO novo.
{
  "26174449188": "| Exposição: EXP-YEMANJA-SSA26\\n| Descrição: Transporte de obra",
  "26174449337": "| Exposição: EXP-YEMANJA-SSA26\\n| Descrição: Fotógrafo"
}

Formas de pagamento inativas travam o PUT (erro 84): são reativadas em lote antes dos PUTs e
restauradas ao final (mesmo se algum PUT falhar). A situação original de cada forma é gravada em
`formas_reativadas.json` no diretório de backup, antes de reativar, p/ recuperação manual se o
processo morrer no meio. Lançamentos sem forma (id 0) não passam por reativação.
Cada PUT é conferido com um GET (histórico novo, forma e categoria preservadas).

Uso: python3 scripts/apply_historico.py --entidade cap --plan plano.json [--ids 1,2] [--execute]
Backups em backups/backups_historico_<entidade>_<ts>/.
"""
import argparse
import datetime
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import BACKUPS_DIR, cap_put_body, car_put_body, load_json, save_json  # noqa: E402
from bling import BlingClient  # noqa: E402

ENTIDADES = {
    "cap": {"path": "/contas/pagar", "body": cap_put_body, "nome": "CAP"},
    "car": {"path": "/contas/receber", "body": car_put_body, "nome": "CAR"},
}


def norm(texto):
    return (texto or "").replace("\r", "").strip()


def resumo(texto, n=60):
    t = norm(texto).replace("\n", " ⏎ ")
    return t if len(t) <= n else t[: n - 1] + "…"


def main():
    ap = argparse.ArgumentParser(description="Reescreve o histórico de CAPs/CARs a partir de um plano JSON.")
    ap.add_argument("--entidade", required=True, choices=sorted(ENTIDADES), help="cap (contas a pagar) ou car (contas a receber)")
    ap.add_argument("--plan", required=True, help="plano JSON {id: histórico novo}")
    ap.add_argument("--ids", help="aplica só nestes ids do plano (separados por vírgula), p/ testes")
    ap.add_argument("--execute", action="store_true", help="aplica de fato (default: dry-run)")
    ap.add_argument("--sleep", type=float, default=0.4, help="pausa entre chamadas (s)")
    args = ap.parse_args()

    ent = ENTIDADES[args.entidade]
    plan = {int(k): v for k, v in load_json(args.plan).items()}
    if args.ids:
        sel = {int(x) for x in args.ids.split(",") if x.strip()}
        fora = sorted(sel - set(plan))
        if fora:
            sys.exit(f"ids fora do plano: {fora}")
        plan = {k: v for k, v in plan.items() if k in sel}

    client = BlingClient()

    # fase 1: ler ao vivo, montar plano (pula no-ops), detectar formas envolvidas
    rows, falhas_get = [], []
    for item_id, novo in plan.items():
        status, data = client.request("GET", f"{ent['path']}/{item_id}")
        if status != 200:
            print(f"GET err {item_id} -> {status}")
            falhas_get.append(item_id)
            continue
        atual = data["data"]
        forma = (atual.get("formaPagamento") or {}).get("id") or 0
        if norm(atual.get("historico")) == norm(novo):
            continue
        rows.append({"id": item_id, "novo": novo, "atual": atual.get("historico") or "",
                     "forma": forma, "situacao": atual.get("situacao")})
        time.sleep(args.sleep / 2)

    formas = sorted({r["forma"] for r in rows if r["forma"]})
    estado_formas = {}
    for fid in formas:
        status, data = client.request("GET", f"/formas-pagamentos/{fid}")
        estado_formas[fid] = data["data"].get("situacao") if status == 200 else None
    inativas = [f for f in formas if estado_formas[f] != 1]
    sem_forma = sum(1 for r in rows if not r["forma"])

    print(f"{ent['nome']}s a alterar: {len(rows)} de {len(plan)} no plano | "
          f"formas a reativar: {inativas} | sem forma: {sem_forma} | GET com erro: {len(falhas_get)}")
    for r in rows:
        print(f"  {ent['nome']} {r['id']} (forma {r['forma']}, sit {r['situacao']}):")
        print(f"      de:   {resumo(r['atual'])!r}")
        print(f"      para: {resumo(r['novo'])!r}")

    if not args.execute:
        print("(dry-run; use --execute)")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(BACKUPS_DIR, f"backups_historico_{args.entidade}_{ts}")
    os.makedirs(outdir, exist_ok=True)

    # fase 2: reativar formas inativas em lote (gravando o estado original antes)
    save_json(os.path.join(outdir, "formas_reativadas.json"),
              {str(f): estado_formas[f] for f in inativas}, indent=1)
    reativadas = {}
    ok, falhas, avisos = 0, [], []
    try:
        for fid in inativas:
            status, data = client.request("GET", f"/formas-pagamentos/{fid}")
            if status != 200:
                print(f"GET forma err {fid} -> {status}")
                continue
            forma = data["data"]
            original = forma.get("situacao")
            forma["situacao"] = 1
            st, _ = client.request("PUT", f"/formas-pagamentos/{fid}", body=forma)
            print(f"reativar forma {fid} -> {st}")
            if st == 200:
                reativadas[fid] = original
            time.sleep(args.sleep)

        # fase 3: backup + PUT + conferência
        for r in rows:
            status, data = client.request("GET", f"{ent['path']}/{r['id']}")
            if status != 200:
                print(f"  GET err {r['id']} -> {status}")
                falhas.append(r["id"])
                continue
            atual = data["data"]
            if norm(atual.get("historico")) == norm(r["novo"]):
                continue
            save_json(os.path.join(outdir, f"{args.entidade}_{r['id']}.json"), atual, indent=1)
            forma_antes = (atual.get("formaPagamento") or {}).get("id") or 0
            cat_antes = (atual.get("categoria") or {}).get("id") or 0
            atual["historico"] = r["novo"]
            st, body = client.request("PUT", f"{ent['path']}/{r['id']}", body=ent["body"](atual))
            if st not in (200, 204):
                falhas.append(r["id"])
                print(f"{ent['nome']} {r['id']}: FALHA {st} — {body}")
                time.sleep(args.sleep)
                continue
            time.sleep(args.sleep)
            st2, conf = client.request("GET", f"{ent['path']}/{r['id']}")
            if st2 == 200:
                novo_det = conf["data"]
                problemas = []
                if norm(novo_det.get("historico")) != norm(r["novo"]):
                    problemas.append("histórico diferente do enviado")
                if ((novo_det.get("formaPagamento") or {}).get("id") or 0) != forma_antes:
                    problemas.append(f"forma mudou ({forma_antes} -> {(novo_det.get('formaPagamento') or {}).get('id')})")
                if ((novo_det.get("categoria") or {}).get("id") or 0) != cat_antes:
                    problemas.append("categoria mudou")
                if problemas:
                    avisos.append((r["id"], problemas))
                    print(f"{ent['nome']} {r['id']}: PUT {st} MAS CONFERIR — {'; '.join(problemas)}")
                    ok += 1
                    continue
            ok += 1
            print(f"{ent['nome']} {r['id']}: histórico atualizado (PUT {st}, conferido)")
            time.sleep(args.sleep)
    finally:
        # fase 4: restaurar formas reativadas, mesmo se algo falhou acima
        for fid, original in reativadas.items():
            status, data = client.request("GET", f"/formas-pagamentos/{fid}")
            if status == 200:
                forma = data["data"]
                forma["situacao"] = original
                st, _ = client.request("PUT", f"/formas-pagamentos/{fid}", body=forma)
                print(f"restaurar forma {fid} -> situação {original}: {st}")
            time.sleep(args.sleep)

    print(f"\naplicado em {ok}/{len(rows)} | formas reativadas e restauradas: {sorted(reativadas)}")
    if falhas:
        print("falharam:", falhas)
    if avisos:
        print("conferir manualmente:", [a[0] for a in avisos])
    print("backups:", outdir)


if __name__ == "__main__":
    main()
