# API — Baixa, estorno e exclusão (CAR/CAP)

> Achados validados (não redescobrir).

- **Estorno de baixa existe via API**: `DELETE /borderos/{idBordero}` — o bordero é o
  registro do recebimento (`GET /contas/receber/{id}` → `borderos[]`). Ao deletar o bordero
  a CAR volta a **Aberto** (situação 1, saldo restaurado) e o **registro do pagamento é
  apagado**.
- `POST /contas/receber/{id}/baixar` cria a baixa/recebimento (CAR → Pago, cria bordero).
  Campos: `data`, `usarDataVencimento`, `portador{id}`, `categoria{id}`, `historico`.
- CAR/CAP **Paga** (saldo 0, bordero) **não pode ser excluída** (`DELETE /contas/receber/{id}`
  → 400 "Existe um pagamento"). Fluxo para remover paga: deletar bordero (estorno) →
  excluir CAR.
- `POST /pedidos/vendas/{id}/estornar-contas` **falha (erro 63)** se existir conta
  paga/conciliada/em remessa — não é caminho de estorno de baixa.
- **Baixa conciliada via integração bancária não estorna** (nem `DELETE /borderos` nem o
  botão "Excluir recebimento" da UI): erro "vínculo com integração ou já foi conciliado".
  Só desfazendo a conciliação no módulo de extrato/conciliação bancária.
- Fluxo de correção de CARs duplicadas: estornar manuais pagas (`DELETE /borderos`),
  excluir manuais, re-baixar as automáticas correspondentes com `data`/`portador` reais
  p/ não perder o registro do recebimento.
- Edição (PUT) de CAR/CAP: **omitir `situacao`** (read-only; enviar `2` dá 400). Atualizar
  categoria de CAPs pagas via PUT funciona.
- **PUT de CAR exige body completo e rejeita forma de pagamento INATIVA** (`erro 84` "A
  forma de pagamento não existe ou está inativa"). Omitir `formaPagamento` é
  **inconsistente** (às vezes preserva, às vezes zera → `0`). Para trocar só a categoria
  preservando a forma antiga: **reativar a forma temporariamente** (`PUT /formas-pagamentos/{id}`
  com `situacao=1`), fazer o `PUT /contas/receber/{id}` com a forma original e **inativar
  de volta**.
- **Erro 84 vale para CAP também** (`PUT /contas/pagar/{id}`), não só CAR. Validado em lote:
  `apply_categorias_cap.py` (191 CAPs) e `apply_historico.py` (72 CAPs, 71 pagas) — reativar
  cada forma inativa **uma vez** antes dos PUTs e restaurar ao final é bem mais barato que
  reativar por chamada (poucas formas cobrem muitas contas). `apply_historico.py` grava a
  situação original das formas em `formas_reativadas.json` antes de reativar (recuperação se o
  processo morrer) e restaura num `finally`.
- **CAP sem forma** (`formaPagamento.id = 0`) aceita o PUT normalmente (forma continua 0) — não
  passa por reativação. **Editar o histórico de CAP paga** (saldo 0, com bordero) via PUT
  também funciona, preservando situação, saldo, forma e categoria.
