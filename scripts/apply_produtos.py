#!/usr/bin/env python3
"""Cadastra produtos (obras) no ERP a partir de um plano JSON. Dry-run por padrão.

Para cada item do plano faz `POST /produtos` (tipo P, formato simples) e, se `estoque` > 0,
lança o saldo inicial no depósito padrão via `POST /estoques`. Se o item tiver `fornecedor`
(nome do artista), cria o contato (só nome, tipo Fornecedor) quando não existir e vincula ao
produto via `POST /produtos/fornecedores`. Pula códigos que já existem no ERP (idempotente).
Não envia imagens (a API só aceita URL pública) nem dados fiscais.

Marca (opcional): só é enviada com `--marca`. Valor = `marca` do item, ou o nome do
`fornecedor` se o item não tiver `marca`. O texto precisa ser igual ao de uma marca já cadastrada
na loja virtual (ver specs/loja-virtual.md); sem `--marca` o campo não é enviado, mesmo que o
plano o traga.

Plano (lista de itens):
[{"codigo": "OBRA-001", "nome": "Título", "preco": 25000, "situacao": "A", "marca": "Artista",
  "categoria_id": 14580914, "descricaoCurta": "...", "descricaoComplementar": "<p>...</p>",
  "estoque": 1}]

Uso: python3 scripts/apply_produtos.py --plan plano_produtos.json [--codes OBRA-001,OBRA-002] [--marca] [--execute]
"""
import argparse
import os
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import BACKUPS_DIR, load_json, money, save_json  # noqa: E402
from bling import BlingClient  # noqa: E402


def marca_de(item):
    """Marca do item: `marca` do plano ou, se ausente, o nome do fornecedor (artista)."""
    return (item.get("marca") or item.get("fornecedor") or "").strip()


def produto_body(item, com_marca=False):
    """Corpo de `POST /produtos` a partir de um item do plano. `marca` só entra se `com_marca`."""
    body = {
        "nome": item["nome"],
        "codigo": item["codigo"],
        "preco": item["preco"],
        "tipo": "P",
        "formato": "S",
        "situacao": item.get("situacao", "A"),
        "unidade": item.get("unidade", "UN"),
        "descricaoCurta": item.get("descricaoCurta", ""),
        "descricaoComplementar": item.get("descricaoComplementar", ""),
    }
    if item.get("categoria_id"):
        body["categoria"] = {"id": item["categoria_id"]}
    if com_marca and marca_de(item):
        body["marca"] = marca_de(item)
    return body


def existe(client, codigo):
    """True se já há produto com esse código no ERP (leitura ao vivo)."""
    st, data = client.get("/produtos", {"codigos[]": codigo, "criterio": 5, "tipo": "T"})
    return st == 200 and bool(data.get("data"))


def achar_contato(client, nome):
    """Id do contato com esse nome exato (case-insensitive), ou None."""
    st, data = client.get("/contatos", {"pesquisa": nome, "limite": 100})
    if st != 200:
        return None
    for c in data.get("data", []):
        if (c.get("nome") or "").strip().lower() == nome.strip().lower():
            return c["id"]
    return None


def criar_fornecedor(client, nome):
    """Cria contato só com nome, tipo Fornecedor. Retorna (id, resposta)."""
    st, tipos = client.get("/contatos/tipos")
    tid = next((t["id"] for t in tipos.get("data", []) if t["descricao"] == "Fornecedor"), None)
    body = {"nome": nome, "situacao": "A", "tipo": "F"}
    if tid:
        body["tiposContato"] = [{"id": tid}]
    st, resp = client.request("POST", "/contatos", body=body)
    return (resp["data"]["id"] if st in (200, 201) else None), (st, resp)


def deposito_padrao(client):
    st, data = client.get("/depositos")
    deps = data.get("data", []) if st == 200 else []
    for d in deps:
        if d.get("padrao"):
            return d["id"]
    return deps[0]["id"] if deps else None


def main():
    ap = argparse.ArgumentParser(description="Cadastra produtos no ERP a partir de um plano JSON.")
    ap.add_argument("--plan", required=True, help="JSON com a lista de produtos")
    ap.add_argument("--codes", help="códigos a processar (csv); default: todos do plano")
    ap.add_argument("--marca", action="store_true",
                    help="envia o campo Marca (item.marca ou nome do fornecedor); default: não envia")
    ap.add_argument("--sleep", type=float, default=0.5, help="intervalo entre chamadas à API")
    ap.add_argument("--execute", action="store_true", help="cria de fato (default: dry-run)")
    args = ap.parse_args()

    plano = load_json(args.plan)
    if args.codes:
        so = {c.strip() for c in args.codes.split(",") if c.strip()}
        plano = [p for p in plano if p["codigo"] in so]

    client = BlingClient()  # leitura ao vivo também no dry-run (checa duplicidade)
    deposito = deposito_padrao(client)
    print(f"depósito padrão: {deposito}\n")

    # fornecedores (artistas): reaproveita existente, cria o que faltar só no --execute
    forn = {}
    for nome in sorted({p["fornecedor"] for p in plano if p.get("fornecedor")}):
        fid = achar_contato(client, nome)
        forn[nome] = fid
        print(f"  fornecedor {nome}: " + (f"existe id={fid}" if fid else "a criar"))
        time.sleep(args.sleep)
    print()

    criados, criados_forn, pulados, erros = [], [], 0, 0
    for item in plano:
        cod = item["codigo"]
        linha = f"{cod}  {money(item['preco'])}  sit={item.get('situacao', 'A')}  {item['nome']}"
        if args.marca:
            linha += f"  marca={marca_de(item) or '(sem marca)'}"
        if existe(client, cod):
            print(f"  = {linha}  [já existe, pulado]")
            pulados += 1
            time.sleep(args.sleep)
            continue
        print(f"  + {linha}")
        if not args.execute:
            time.sleep(args.sleep)
            continue
        st, body = client.request("POST", "/produtos", body=produto_body(item, args.marca))
        if st not in (200, 201):
            print(f"    ERRO POST /produtos: {st} {body}", file=sys.stderr)
            erros += 1
            time.sleep(args.sleep)
            continue
        pid = body["data"]["id"]
        criados.append({"codigo": cod, "id": pid})
        print(f"    criado id={pid}")
        nome = item.get("fornecedor")
        if nome:
            if not forn.get(nome):
                forn[nome], resp = criar_fornecedor(client, nome)
                if forn[nome]:
                    print(f"    fornecedor criado: {nome} id={forn[nome]}")
                    criados_forn.append({"nome": nome, "id": forn[nome]})
                else:
                    print(f"    ERRO POST /contatos: {resp}", file=sys.stderr)
                    erros += 1
                time.sleep(args.sleep)
            if forn.get(nome):
                st, body = client.request("POST", "/produtos/fornecedores", body={
                    "produto": {"id": pid},
                    "fornecedor": {"id": forn[nome]},
                    "padrao": True,
                })
                if st not in (200, 201):
                    print(f"    ERRO POST /produtos/fornecedores: {st} {body}", file=sys.stderr)
                    erros += 1
                time.sleep(args.sleep)
        if item.get("estoque") and deposito:
            time.sleep(args.sleep)
            st, body = client.request("POST", "/estoques", body={
                "produto": {"id": pid},
                "deposito": {"id": deposito},
                "operacao": "B",
                "quantidade": item["estoque"],
                "preco": item["preco"],
                "observacoes": "Saldo inicial (cadastro via API)",
            })
            if st not in (200, 201):
                print(f"    ERRO POST /estoques: {st} {body}", file=sys.stderr)
                erros += 1
        time.sleep(args.sleep)

    if args.execute and criados:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = os.path.join(BACKUPS_DIR, f"backups_produtos_{ts}", "criados.json")
        save_json(out, {"produtos": criados, "fornecedores": criados_forn}, indent=2)
        print(f"\nids criados gravados em {os.path.relpath(out, ROOT)}")

    print("\n" + (f"aplicado em {len(criados)} produtos" if args.execute
                  else f"{len(plano) - pulados} a criar (dry-run; use --execute)")
          + f" · {pulados} já existiam · {erros} erros")


if __name__ == "__main__":
    main()
