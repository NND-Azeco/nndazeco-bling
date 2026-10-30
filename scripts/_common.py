"""Utilitários compartilhados pelos scripts (paths, JSON, formatação, associação CAR↔PV)."""
import json
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
BACKUPS_DIR = os.path.join(ROOT, "backups")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj, indent=None):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)


def money(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def car_put_body(car, historico=None):
    """Corpo de `PUT /contas/receber/{id}` a partir do GET (omite `situacao`, read-only)."""
    return {
        "contato": {"id": car["contato"]["id"]},
        "dataEmissao": car.get("dataEmissao"),
        "vencimento": car.get("vencimento"),
        "valor": car.get("valor"),
        "formaPagamento": {"id": (car.get("formaPagamento") or {}).get("id")},
        "categoria": {"id": (car.get("categoria") or {}).get("id")},
        "portador": {"id": (car.get("portador") or {}).get("id")},
        "vendedor": {"id": (car.get("vendedor") or {}).get("id")},
        "numeroDocumento": car.get("numeroDocumento") or "",
        "historico": car.get("historico") if historico is None else historico,
    }


def cap_put_body(cap, historico=None):
    """Corpo de `PUT /contas/pagar/{id}` a partir do GET (omite `situacao`, read-only)."""
    return {
        "contato": {"id": cap["contato"]["id"]},
        "dataEmissao": cap.get("dataEmissao"),
        "vencimento": cap.get("vencimento"),
        "valor": cap.get("valor"),
        "formaPagamento": {"id": (cap.get("formaPagamento") or {}).get("id")},
        "categoria": {"id": (cap.get("categoria") or {}).get("id")},
        "portador": {"id": (cap.get("portador") or {}).get("id")},
        "vendedor": {"id": (cap.get("vendedor") or {}).get("id") or 0},
        "competencia": cap.get("competencia"),
        "numeroDocumento": cap.get("numeroDocumento") or "",
        "historico": cap.get("historico") if historico is None else historico,
    }


def erro_84(body):
    """True se o erro do PUT for 'forma de pagamento inativa' (code 84)."""
    fields = ((body or {}).get("error") or {}).get("fields") or []
    return any(f.get("code") == 84 for f in fields)


def set_forma_situacao(client, fid, situacao):
    _, d = client.get(f"/formas-pagamentos/{fid}")
    body = dict(d["data"])
    body["situacao"] = situacao
    body.pop("id", None)
    return client.request("PUT", f"/formas-pagamentos/{fid}", body=body)


def put_car(client, car, historico, sleep=0.4):
    """PUT de CAR; se erro 84 (forma inativa), reativa a forma, refaz e restaura a situação."""
    import time as _time

    path = f"/contas/receber/{car['id']}"
    st, body = client.request("PUT", path, body=car_put_body(car, historico))
    if st == 400 and erro_84(body):
        fid = (car.get("formaPagamento") or {}).get("id")
        _, d = client.get(f"/formas-pagamentos/{fid}")
        orig = d["data"].get("situacao")
        set_forma_situacao(client, fid, 1)
        _time.sleep(sleep)
        try:
            st, body = client.request("PUT", path, body=car_put_body(car, historico))
        finally:
            set_forma_situacao(client, fid, orig)
            _time.sleep(sleep)
    return st, body


RE_EXPO = re.compile(r"\s*\|?\s*Exposi[çc][ãa]o:[^\n]*", re.IGNORECASE)
RE_CAMPO = re.compile(r"^(Tipo|Despesa|Motivo|Fornecedor/Credor|Valor|Vencimento|Aprovado por):\s*(.*)$")
DESC_LONGA = 150


def descricao_exposicao(hist):
    """Descrição p/ o Template 5 a partir do histórico atual ('' se não houver o que aproveitar)."""
    h = RE_EXPO.sub("", (hist or "").replace("\r", ""))
    linhas = [ln.strip(" |").strip() for ln in h.split("\n")]
    linhas = [ln for ln in linhas if ln]
    campos = {}
    for ln in linhas:
        m = RE_CAMPO.match(ln)
        if m:
            campos[m.group(1)] = m.group(2).strip()
    if campos.get("Despesa"):
        partes = [campos["Despesa"]]
        motivo = campos.get("Motivo", "")
        if motivo and "informar" not in motivo.lower():
            partes.append(motivo)
        return " - ".join(partes)
    return " - ".join(linhas)


def template5_historico(expo_id, descricao):
    """Histórico do Template 5 (Despesas com Exposição) — ver specs/templates.md."""
    return f"| Exposição: {expo_id}\n| Descrição: {descricao}"


def novo_historico(c, expo_id):
    """Template 5 a partir do histórico atual da CAP: (texto, descrição aproveitada)."""
    desc = descricao_exposicao(c.get("historico"))
    return template5_historico(expo_id, desc), desc


def find_pv_number(hist, pv_numbers):
    """Acha o número de PV (20NNNNN/20NNNNNN) citado no histórico de uma CAR manual."""
    if not hist:
        return None
    candidates = [int(m.group(1)) for m in re.finditer(r"(?<!\d)(20\d{5,6})(?!\d)", hist)
                  if int(m.group(1)) in pv_numbers]
    if candidates:
        return max(candidates, key=lambda n: len(str(n)))
    return None


def associate_cars(cars, pvs, excluir=()):
    """Agrupa CARs por número de PV.

    origem 'venda' -> origem.numero; 'notafiscal' -> NF ligada ao PV; manual -> histórico.
    Retorna (pv_by_num, car_ids_by_pv).
    """
    excluir = set(excluir or [])
    pv_by_num = {p["numero"]: p for p in pvs}
    pv_numbers = set(pv_by_num)
    nf_to_pv = {}
    for p in pvs:
        nf = (p.get("notaFiscal") or {}).get("id")
        if nf:
            nf_to_pv[nf] = p["numero"]

    car_ids_by_pv = defaultdict(list)
    for c in cars:
        if c["id"] in excluir:
            continue
        origem = c.get("origem") or {}
        tipo = origem.get("tipoOrigem") or ""
        number = None
        if tipo == "venda":
            try:
                number = int(origem.get("numero"))
            except (TypeError, ValueError):
                number = None
            if number not in pv_by_num:
                number = None
        elif tipo == "notafiscal":
            number = nf_to_pv.get(origem.get("id"))
        else:
            number = find_pv_number(c.get("historico") or "", pv_numbers)
        if number:
            car_ids_by_pv[number].append(c["id"])
    return pv_by_num, car_ids_by_pv
