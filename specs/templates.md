# Templates de histórico — lançamentos Bling

**NND | AZECO — Galeria de Arte**

Como usar: copie o bloco do template, cole no campo **"Histórico"** (ou "Descrição") do
lançamento no Bling e substitua o que está entre colchetes `[ ]`. Apague os colchetes depois
de preencher. As linhas começam com `| ` apenas para facilitar a leitura — pode manter ou
remover ao colar.

## Índice

- **Ciclo de Venda**
  - Template 1 — Conta a Receber — Recebimento do Cliente
  - Template 2 — Conta a Pagar — Repasse ao Artista
  - Template 3 — Conta a Pagar — Comissão da Vendedora
- **Contas Recorrentes e Extraordinárias**
  - Template 4 — Conta a Pagar — Outras despesas
  - Template 5 — Conta a Pagar — Despesas com Exposição
- **Lembretes Gerais** (Política de Pagamentos)

## Ciclo de Venda

Use os templates desta seção nos lançamentos ligados a uma mesma venda: quando o cliente
paga (conta a receber), quando a galeria repassa ao artista (conta a pagar) e quando paga a
comissão da vendedora (conta a pagar).

- **Template 1 (Conta a Receber)** nasce do Pedido de Venda — o Bling preenche a primeira
  linha (`Ref. ao pedido de venda nº ...`) automaticamente, **não digite** o número.
- **Templates 2 e 3 (Contas a Pagar)** são criados **manualmente** — o Bling não insere o PV,
  então inclua sempre o campo `| Venda: PV#...` no início.

As demais linhas são sempre iguais — só mudam as linhas finais, de acordo com o tipo de
lançamento.

## Template 1 — Conta a Receber (recebimento do cliente)

```
| Obras: [NOME DA OBRA]
| Cliente: [NOME DO CLIENTE]
| Valor da venda: R$ [VALOR TOTAL]
| Parcelas: [Nº]/[TOTAL]
```

Exemplo completo:

```
| Obras: Sem Título
| Artista: Walcyr
| Cliente: Maria Fernandes
| Valor da venda: R$ 18.000,00
| Parcelas: 1/3
```

> **Várias obras:** separe por `; ` (ponto e vírgula + espaço) na mesma linha `| Obras:`.
> Evite vírgula (as descrições de obra já a usam) e barra (usada em alguns títulos).

## Template 2 — Conta a Pagar — Repasse ao Artista

```
| Venda: PV#[Nº do Pedido de Venda]
| Obras: [NOME DA OBRA]
| Cliente: [NOME DO CLIENTE]
| Valor da venda: R$ [VALOR TOTAL]
| Parcelas: [Nº]/[TOTAL]
```

Exemplo completo:

```
| Venda: PV#1234
| Obras: Sem Título
| Cliente: Maria Fernandes
| Valor da venda: R$ 18.000,00
| Parcelas: 1/10
```

> **Regra fixa:** repasse ao artista = **50% sobre 90%** da venda. O **coeficiente de custo
> (0,10)** é deduzido antes de calcular o repasse — não precisa constar no lançamento. O
> valor da conta já é o repasse líquido.

## Template 3 — Conta a Pagar — Comissão da Vendedora

```
| Venda: PV#[Nº do Pedido de Venda]
| Obras: [NOME DA OBRA]
| Cliente: [NOME DO CLIENTE]
| Valor da venda: R$ [VALOR TOTAL]
| Comissão: [PERCENTUAL]%
| Parcelas: [Nº]/[TOTAL]
```

Exemplo completo:

```
| Venda: PV#1234
| Obras: Sem Título
| Cliente: Maria Fernandes
| Valor da venda: R$ 18.000,00
| Comissão: 25%
| Parcelas: 1/3
```

> **Observação:** nº do PV, obra, artista e valores devem sempre bater com o Pedido de Venda
> no Bling — é a fonte oficial da informação (inclusive para o próprio artista, que acompanha
> por lá).

## Template 4 — Outras despesas / recorrentes

Use para despesas recorrentes ou despesas extraordinárias.

```
| Unidade: [MOCOCA/SSA/SP/RJ]
| Despesa: [Descrição]
```

Exemplo completo:

```
| Unidade: SP
| Despesa: Aluguel Galeria SP
```

## Template 5 — Conta a Pagar — Despesas com Exposição

Use para despesas ligadas a uma exposição (frete, montagem, curadoria,
plotagem etc.). **Exposição** identifica o evento; IDs vigentes:

`EXP-CUENCA-SP26` · `EXP-DEMONS-RJ26` · `EXP-ENOQUE-SP26` · `EXP-EVANDRO-SP26` ·
`EXP-HAYASHI-SP 26` · `EXP-YEMANJA-SSA26` · `EXP-LAZARO-SP26` · `EXP-MARLON-SSA26` ·
`EXP-DBARRETO-SSA26`

```
| Exposição: [EXP-XXXX-YY]
| Descrição: [Descrição da despesa]
```

Exemplo completo:

```
| Exposição: EXP-LAZARO-SP26
| Descrição: Transporte de obras para montagem
```

> **Exposição** deve bater com um dos IDs vigentes (ex.: `EXP-LAZARO-SP26`,
> `EXP-DEMONS-RJ26`) — não inventar um novo sem alinhar antes.

## Lembretes Gerais (Política de Pagamentos)

1. Pagamentos (artistas, fornecedores, prestadores): todo dia **15**. Se cair em fim de
   semana/feriado, posterga para o próximo dia útil.
2. Comissão de vendedoras: paga dia **30**.
3. Salários: pagos dia **30**.
4. Nenhum pagamento sem documentação: nota fiscal ou recibo, contrato (quando houver) e dados
   bancários/Pix.
5. Solicitações de pagamento até o dia **10** entram no ciclo do dia 15; depois disso, vão
   para o mês seguinte.

## Aplicação (scripts)

- Template 1 (histórico de CAR): `scripts/apply_template1_cars.py` (dry-run por padrão).
- Regra de repasse/comissão: `scripts/report_artista.py` (relatórios por artista).
- Template 5 (histórico de CAP): `tools/gen_plano_template5.py` monta o plano a partir de
  `{capId: exposição}` + `{capId: descrição}`; `scripts/apply_historico.py --entidade cap`
  aplica (dry-run por padrão). `scripts/report_caps.py` gera `report_caps_template5.md` com o
  histórico atual × novo para revisão antes de aplicar.
