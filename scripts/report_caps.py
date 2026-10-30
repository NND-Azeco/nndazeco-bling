#!/usr/bin/env python3
"""Gera report_caps_por_pc.md e report_caps_sem_pc.md a partir de snapshots ao vivo.

Fontes:
  data/pedidos_compra.json     (PC: itens, parcelas, fornecedor)
  data/contas_pagar.json       (CAPs com detalhe)
  data/contatos.json           (id -> nome, p/ fornecedor)
  data/categorias_com_situacao.json
  data/formas_pagamento.json

Associação CAP→PC (CAP não tem `origem`, diferente de CAR — ver specs/api-docs/api-cap.md):
  1. numeroDocumento no formato "{numeroPC}/{parcela}" -> numeroPC
  2. histórico "Ref. ao pedido de compra nº {numero}, ..." (regex) -> numero
  Sem match -> "sem PC" (manual). Dentro de "sem PC", 5 tipos (nessa ordem de prioridade):
  1 Exposição · 2 Comissões de Vendedores · 3 repasse de artista/vendas agenciadas ·
  4 histórico vazio · 5 restante (ordem alfabética por histórico).

Terceiro relatório (opcional): report_caps_template5.md — CAPs de `expos.json`
({capId: "EXP-..."}) com o histórico atual e o novo histórico (Template 5, specs/templates.md).

Grupos (mesmo espírito do report_cars, PV -> PC):
  1 Acima, 2 Abaixo, 3 Duplicação exata (~2x), 4 Cobre via manual,
  5 Ideal, 6 PCs sem CAP.
"""
import argparse
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import DATA_DIR, DESC_LONGA, descricao_exposicao, novo_historico  # noqa: E402

_ap = argparse.ArgumentParser(description="Gera os relatórios de CAPs por PC / sem PC.")
_ap.add_argument("--data-dir", default=DATA_DIR, help="diretório dos snapshots")
_ap.add_argument("--out-dir", default=ROOT, help="diretório de saída dos relatórios")
_ap.add_argument("--expos", default=os.path.join(ROOT, "expos.json"),
                 help="JSON {capId: ID de exposição} p/ o relatório do Template 5")
_ap.add_argument("--titulo", default="NND | AZECO — Galeria de Arte", help="título dos relatórios")
args = _ap.parse_args()

SIT = {1: "Aberto", 2: "Pago", 3: "Atrasado", 4: "Recebido", 5: "Baixado"}

RE_PC_HIST = re.compile(r"Ref\.\s+ao\s+pedido\s+de\s+compra\s+n[ºo°]\s*(\d+)", re.IGNORECASE)


def load(f):
    return json.load(open(os.path.join(args.data_dir, f), encoding="utf-8"))


FP_NAMES = {}


def load_fp_names():
    global FP_NAMES
    try:
        FP_NAMES = {x["id"]: x.get("descricao", "") for x in load("formas_pagamento.json")}
    except Exception:
        FP_NAMES = {}


CAT_NAMES = {}


def load_cat_names():
    try:
        d = load("categorias_com_situacao.json")
    except Exception:
        return

    def walk(o):
        if isinstance(o, dict):
            if o.get("id") and o.get("descricao"):
                CAT_NAMES[str(o["id"])] = o["descricao"]
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(d)


CONTATOS = {}


def load_contatos():
    global CONTATOS
    try:
        CONTATOS = load("contatos.json")
    except Exception:
        CONTATOS = {}


def cat_name(obj):
    cid = (obj.get("categoria") or {}).get("id") or 0
    if not cid:
        return "—"
    return CAT_NAMES.get(str(cid), f"{cid} (?)")


def fmt(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def r(hist):
    return (hist or "").replace("R$", "R\\$").replace("\n", " / ").replace("\r", "").replace("|", "\\|")


def fp_name(c):
    fp = c.get("formaPagamento") or {}
    return FP_NAMES.get(fp.get("id"), "")


def sit_name(c):
    return SIT.get(c.get("situacao"), str(c.get("situacao")))


def fornecedor_nome(cid):
    d = CONTATOS.get(str(cid))
    return (d or {}).get("nome") or ""


def is_exposicao(hist):
    h = hist or ""
    return "EXTRAORDINÁRIA" in h.upper() or "exposi" in h.lower()


def is_categoria_comissao_vendedor(cid):
    nome = CAT_NAMES.get(str(cid or 0), "").lower()
    return "comiss" in nome


def is_categoria_repasse(cid):
    """Repasse de artista ou repasse de venda agenciada (comissão de vendedor é grupo à parte)."""
    nome = CAT_NAMES.get(str(cid or 0), "").lower()
    return nome.startswith("repasse")


def find_pc_number(c, pc_nums):
    """Acha o número do PC citado numeroDocumento ou no histórico de uma CAP."""
    doc = c.get("numeroDocumento") or ""
    if "/" in doc:
        head = doc.split("/", 1)[0]
        if head.isdigit() and int(head) in pc_nums:
            return int(head)
    m = RE_PC_HIST.search(c.get("historico") or "")
    if m:
        n = int(m.group(1))
        if n in pc_nums:
            return n
    return None


def main():
    pcs = load("pedidos_compra.json")
    caps = load("contas_pagar.json")
    load_cat_names()
    load_fp_names()
    load_contatos()
    pc_by_num = {}
    for p in pcs:
        pc_by_num.setdefault(p["numero"], p)
    pc_nums = set(pc_by_num.keys())

    by_pc = {}
    no_pc = []
    for c in caps:
        n = find_pc_number(c, pc_nums)
        if n:
            by_pc.setdefault(n, []).append(c)
        else:
            no_pc.append(c)

    # Grupos por categoria (mutuamente exclusivos): 1 Exposição · 2 repasse (artista/vendas
    # agenciadas) · 3 Comissões de Vendedores · 4 histórico vazio · 5 restante.
    exposicao_cars = [c for c in no_pc if is_exposicao(c.get("historico"))]
    resto1 = [c for c in no_pc if not is_exposicao(c.get("historico"))]
    comissao_vendedores = [c for c in resto1 if is_categoria_comissao_vendedor((c.get("categoria") or {}).get("id"))]
    resto2 = [c for c in resto1 if not is_categoria_comissao_vendedor((c.get("categoria") or {}).get("id"))]
    repasse = [c for c in resto2 if is_categoria_repasse((c.get("categoria") or {}).get("id"))]
    resto3 = [c for c in resto2 if not is_categoria_repasse((c.get("categoria") or {}).get("id"))]
    historico_vazio = [c for c in resto3 if not (c.get("historico") or "").strip()]
    outras_manuais = [c for c in resto3 if (c.get("historico") or "").strip()]

    # estado de cada PC
    info = {}
    for num, p in pc_by_num.items():
        cs = by_pc.get(num, [])
        total = p.get("total") or 0
        soma = sum(x.get("valor") or 0 for x in cs)
        info[num] = dict(pc=p, caps=cs, total=total, soma=round(soma, 2))

    def classify(num):
        it = info[num]
        total, soma = it["total"], it["soma"]
        ncaps = len(it["caps"])
        if ncaps == 0:
            return 6
        if soma == 0:
            return 6
        if total and abs(soma - 2 * total) < 0.01 and ncaps > 1:
            return 3
        if soma > total + 0.01:
            return 1
        if soma < total - 0.01:
            return 2
        return 5

    groups = {1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
    for num in info:
        groups[classify(num)].append(num)

    def order_key(num):
        p = info[num]["pc"]
        return p.get("data") or "", p.get("numero") or num

    for g in groups:
        groups[g].sort(key=order_key)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    n_auto = len(caps) - len(no_pc)
    pc_com_cap = sum(1 for num in info if len(info[num]["caps"]) > 0)
    n_pcs = len(info)

    # ---------- relatório principal (por PC) ----------
    out = []
    out.append("# Relatório de Contas a Pagar por Pedido de Compra")
    out.append("")
    out.append("**" + args.titulo + "**")
    out.append("")
    out.append("> Total de cada título = total do PC. PCs classificados por cobertura das CAPs.")
    out.append("")
    out.append(f"- Total CAPs: **{len(caps)}** · vinculadas a PC: {n_auto} · sem PC: {len(no_pc)} "
               f"(exposição: {len(exposicao_cars)}, repasse: {len(repasse)}, "
               f"comissões de vendedores: {len(comissao_vendedores)}, "
               f"histórico vazio: {len(historico_vazio)}, outras: {len(outras_manuais)}) · "
               f"PCs: {n_pcs} · PCs com CAP: {pc_com_cap}")
    out.append(f"- Atualizado: {now}")
    out.append("")
    out.append("## Índice")
    out.append("")
    out.append(f"1. ⬆ Acima do total — {len(groups[1])} PC")
    out.append(f"2. ⬇ Abaixo do total — {len(groups[2])} PC")
    out.append(f"3. 🔁 Duplicação exata (≈2×) — {len(groups[3])} PC")
    out.append(f"4. 🔄 Cobre via manual — {len(groups[4])} PC")
    out.append(f"5. ✅ Ideal — {len(groups[5])} PC")
    out.append(f"6. ⚠️ PCs sem CAP (não cobertos) — {len(groups[6])}")
    out.append("")
    out.append("")
    group_titles = {
        1: ("## 1. ⬆ Acima do total", "CAPs somam **mais** que o total do PC"),
        2: ("## 2. ⬇ Abaixo do total", "CAPs somam **menos** que o total do PC"),
        3: ("## 3. 🔁 Duplicação exata (≈2×)", "Soma das CAPs = **2× total**"),
        4: ("## 4. 🔄 Cobre via manual", "Total **coberto**, mas por mais de uma CAP"),
        5: ("## 5. ✅ Ideal", "CAPs somam exatamente o total do PC"),
        6: ("## 6. ⚠️ PCs sem CAP (não cobertos)", "Pedidos de compra existentes **sem nenhuma CAP** vinculada"),
    }

    def emit_header(g):
        t, d = group_titles[g]
        out.append(t + f" — {len(groups[g])} PC")
        out.append("")
        out.append(f"> {d}.")
        out.append("")

    def emit_pc_block(num):
        it = info[num]
        p = it["pc"]
        fnome = fornecedor_nome((p.get("fornecedor") or {}).get("id"))
        num_pc = p.get("numero")
        out.append(f"### PC {num_pc} — {fnome}")
        out.append("")
        out.append(f"**Total do PC:** {fmt(it['total'])} · _(soma CAPs: {fmt(it['soma'])})_ · {len(it['caps'])} CAP(s)")
        out.append(f"**Categoria do PC:** {cat_name(p)}")
        out.append("")
        if it["caps"]:
            out.append("| CAP | vencimento | competência | valor | situação | categoria | forma | nº documento | histórico |")
            out.append("|---|---|---|---|---|---|---|---|---|")
            for c in sorted(it["caps"], key=lambda x: x.get("vencimento") or ""):
                out.append(f"| `{c['id']}` | {c.get('vencimento')} | {c.get('competencia')} | {fmt(c.get('valor'))} | {sit_name(c)} | {cat_name(c)} | {fp_name(c)} | {c.get('numeroDocumento') or ''} | {r(c.get('historico'))} |")
            out.append("")

    for g in (1, 2, 3, 4, 5):
        emit_header(g)
        for num in groups[g]:
            emit_pc_block(num)
            out.append("")

    emit_header(6)
    if groups[6]:
        out.append("| PC | data | total | fornecedor | situação | categoria |")
        out.append("|---|---|---|---|---|---|")
        for num in groups[6]:
            it = info[num]
            p = it["pc"]
            fnome = fornecedor_nome((p.get("fornecedor") or {}).get("id"))
            sit = (p.get("situacao") or {}).get("valor")
            out.append(f"| {p.get('numero')} | {p.get('data')} | {fmt(it['total'])} | {fnome} | {sit} | {cat_name(p)} |")
        out.append("")
    out.append("")

    # ---------- relatório CAPs sem PC ----------
    out2 = []
    out2.append("# Relatório — CAPs sem PC (manuais)")
    out2.append("")
    out2.append("**" + args.titulo + "**")
    out2.append("")
    out2.append(f"- CAPs sem PC: **{len(no_pc)}** · Exposição: **{len(exposicao_cars)}** · "
                 f"Repasse (artista/vendas agenciadas): **{len(repasse)}** · "
                 f"Comissões de Vendedores: **{len(comissao_vendedores)}** · "
                 f"Histórico vazio: **{len(historico_vazio)}** · Outras: **{len(outras_manuais)}**")
    out2.append(f"- Atualizado: {now}")
    out2.append("")
    out2.append("## Índice")
    out2.append("")
    out2.append(f"1. CAPs de Exposição — {len(exposicao_cars)}")
    out2.append(f"2. Repasse de artista / vendas agenciadas — {len(repasse)}")
    out2.append(f"3. Comissões de Vendedores — {len(comissao_vendedores)}")
    out2.append(f"4. CAPs com histórico vazio — {len(historico_vazio)}")
    out2.append(f"5. Restante (ordem alfabética por histórico) — {len(outras_manuais)}")
    out2.append("")
    out2.append("")

    def emit_tabela(rows, key=lambda x: x.get("vencimento") or ""):
        out2.append("| CAP | venc | valor | situação | categoria | forma | fornecedor | histórico |")
        out2.append("|---|---|---|---|---|---|---|---|")
        for c in sorted(rows, key=key):
            fnome = fornecedor_nome((c.get("contato") or {}).get("id"))
            out2.append(f"| `{c['id']}` | {c.get('vencimento')} | {fmt(c.get('valor'))} | {sit_name(c)} | {cat_name(c)} | {fp_name(c)} | {fnome} | {r(c.get('historico'))} |")
        out2.append("")

    out2.append("## 1. CAPs de Exposição")
    out2.append("")
    out2.append("> Gastos de evento/exposição lançados manualmente (sem PC associado no Bling).")
    out2.append("")
    emit_tabela(exposicao_cars)

    out2.append("## 2. Repasse de artista / vendas agenciadas")
    out2.append("")
    out2.append("> Categoria começa com `Repasse` (artista ou vendas agenciadas).")
    out2.append("")
    emit_tabela(repasse)

    out2.append("## 3. Comissões de Vendedores")
    out2.append("")
    out2.append("> Categoria contém `Comiss` (Comissões de Vendedores, Comissionamento Vendas, Comissões).")
    out2.append("")
    emit_tabela(comissao_vendedores)

    out2.append("## 4. CAPs com histórico vazio")
    out2.append("")
    out2.append("> Sem PC, não são de Exposição, repasse ou comissão, e `historico` está vazio.")
    out2.append("")
    emit_tabela(historico_vazio)

    out2.append("## 5. Restante")
    out2.append("")
    out2.append("> Ordenado alfabeticamente pelo texto do histórico.")
    out2.append("")
    emit_tabela(outras_manuais, key=lambda x: (x.get("historico") or "").lower())

    # ---------- relatório CAPs do Template 5 (exposição) ----------
    n_t5 = 0
    if os.path.exists(args.expos):
        expos = {str(k): v for k, v in json.load(open(args.expos, encoding="utf-8")).items()}
        caps_by_id = {str(c["id"]): c for c in caps}
        no_pc_ids = {str(c["id"]) for c in no_pc}
        ausentes = sorted(k for k in expos if k not in caps_by_id)
        com_pc = sorted(k for k in expos if k in caps_by_id and k not in no_pc_ids)

        def sel(rows):
            return [c for c in rows if str(c["id"]) in expos]

        grupos_t5 = [
            ("1. CAPs de Exposição", sel(exposicao_cars), lambda x: x.get("vencimento") or ""),
            ("2. Repasse de artista / vendas agenciadas", sel(repasse), lambda x: x.get("vencimento") or ""),
            ("3. Comissões de Vendedores", sel(comissao_vendedores), lambda x: x.get("vencimento") or ""),
            ("4. CAPs com histórico vazio", sel(historico_vazio), lambda x: x.get("vencimento") or ""),
            ("5. Restante", sel(outras_manuais), lambda x: (x.get("historico") or "").lower()),
        ]
        todos_t5 = [c for _, rows, _ in grupos_t5 for c in rows]
        n_t5 = len(todos_t5)
        sem_desc = [c for c in todos_t5 if not descricao_exposicao(c.get("historico"))]
        longas = [c for c in todos_t5 if len(descricao_exposicao(c.get("historico"))) > DESC_LONGA]
        por_expo = {}
        for c in todos_t5:
            por_expo[expos[str(c["id"])]] = por_expo.get(expos[str(c["id"])], 0) + 1

        out3 = ["# Relatório — CAPs do Template 5 (Despesas com Exposição)", "",
                "**" + args.titulo + "**", "",
                "> Histórico atual × novo histórico (Template 5, `specs/templates.md`). "
                "Descrição = histórico atual sem o trecho `Exposição: ...`; "
                "`⚠️ FALTA` = nada aproveitável no histórico atual.", "",
                f"- CAPs no `expos.json`: **{len(expos)}** · listadas aqui: **{n_t5}** · "
                f"valor total: **{fmt(sum(c.get('valor') or 0 for c in todos_t5))}**",
                f"- Sem descrição aproveitável (`⚠️ FALTA`): **{len(sem_desc)}** · "
                f"descrição longa (> {DESC_LONGA} caracteres, revisar): **{len(longas)}**",
                f"- IDs ausentes no snapshot: **{len(ausentes)}**"
                + (f" ({', '.join(ausentes)})" if ausentes else "")
                + f" · vinculadas a PC (fora do escopo sem PC): **{len(com_pc)}**"
                + (f" ({', '.join(com_pc)})" if com_pc else ""),
                f"- Atualizado: {now}", "", "## Exposições", "",
                "| Exposição | CAPs |", "|---|---|"]
        for ex, n in sorted(por_expo.items()):
            out3.append(f"| {ex} | {n} |")
        out3 += ["", "## Índice", ""]
        for titulo, rows, _ in grupos_t5:
            out3.append(f"- {titulo} — {len(rows)}")
        out3 += ["", ""]

        def md_novo(c):
            texto, desc = novo_historico(c, expos[str(c["id"])])
            if not desc:
                texto = texto.rstrip() + " ⚠️ FALTA"
            elif len(desc) > DESC_LONGA:
                texto += " ⚠️ LONGA"
            return "<br>".join(r(ln) for ln in texto.split("\n"))

        for titulo, rows, key in grupos_t5:
            out3 += [f"## {titulo}", ""]
            out3 += ["| CAP | venc | valor | histórico | novo histórico |", "|---|---|---|---|---|"]
            for c in sorted(rows, key=key):
                out3.append(f"| `{c['id']}` | {c.get('vencimento')} | {fmt(c.get('valor'))} | "
                            f"{r(c.get('historico'))} | {md_novo(c)} |")
            out3.append("")
        with open(os.path.join(args.out_dir, "report_caps_template5.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(out3))
        print("template5:", n_t5, "CAPs · sem descrição:", len(sem_desc), "· longas:", len(longas),
              "· ausentes:", len(ausentes), "· com PC:", len(com_pc))

    with open(os.path.join(args.out_dir, "report_caps_por_pc.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    with open(os.path.join(args.out_dir, "report_caps_sem_pc.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out2))

    print("grupos:", {k: len(v) for k, v in groups.items()})
    print("sem PC:", len(no_pc), "exposicao:", len(exposicao_cars), "repasse:", len(repasse),
          "comissoes vendedores:", len(comissao_vendedores), "historico vazio:", len(historico_vazio),
          "outras:", len(outras_manuais))


if __name__ == "__main__":
    main()
