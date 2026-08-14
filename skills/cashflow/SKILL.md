---
name: cashflow
description: "Insere, remove ou edita lançamentos, contas (saldo/fatura) e parcelas. Execute apply imediatamente."
version: 2.2.0
author: Aurum
license: MIT
metadata:
  hermes:
    tags: [finance, cashflow, bookkeeping]
    requires_toolsets: [terminal]
---

# Fluxo de caixa

## CRÍTICO — única tool: `terminal`

Caminho:

```
$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run
```

Quando o usuário descrever um gasto, uma receita, uma conta bancária nova, um cartão, uma conta mensal, uma compra parcelada, uma correção ou uma exclusão, execute **na hora**. Não pergunte categoria nem data.

## Inserir

Gatilhos: *gastei*, *paguei*, *comprei*, *recebi*.

```json
{
  "command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Gastei 30 reais em mercado no débito com o banco Inter\""
}
```

Defaults:

| Campo | Se o usuário omitir |
|-------|---------------------|
| data | hoje |
| categoria | inferida (`mercado` → Alimentação) ou **Outros** |
| conta | inferida ou última usada / Carteira |

## Contas de débito e cartões

Débito **exige saldo inicial**. Crédito **exige dia de fechamento e dia de pagamento da fatura**. Se faltar, mostre o `ask` do JSON e rode `apply` de novo com a frase completa.

```json
{"command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Nova conta débito Itaú com saldo de 1500\""}
```

```json
{"command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Novo cartão Inter, fecha dia 19, fatura dia 25\""}
```

Saldo da carteira: `accounts` ou `apply "Quanto tenho?"`.

## Contas mensais (água, luz, telefone)

Gatilhos: *conta de*, *por mês*, *mensal*, *todo mês*.

```json
{"command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Conta de luz 150 por mês dia 10 no Inter\""}
```

```json
{"command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Muda a água para 90\""}
```

```json
{"command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Apaga a conta de telefone\""}
```

`Paguei a luz 150` continua sendo lançamento do dia (não agenda).

## Crédito parcelado

```json
{"command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Compra de 1000 no cartão de crédito banco Inter em 5x\""}
```

Gera 5 cobranças futuras de R$ 200. `Cancela a compra em 5x` remove o plano.

## Remover

```json
{"command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Apaga o último lançamento\""}
```

```json
{"command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Remove o gasto de 30 reais no mercado\""}
```

## Editar valor

```json
{"command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Corrige o valor para 35\""}
```

```json
{"command": "$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run apply \"Na verdade foi 35, não 30\""}
```

## Consultar

| Pergunta | Comando |
|----------|---------|
| hoje | `today` |
| cobranças futuras | `upcoming` |
| dia/mês | `list --date YYYY-MM-DD` / `list --month YYYY-MM` |
| contas / saldo | `accounts` |
| categorias | `categories` |

## Confirmação

Confirme **somente** se `"status":"ok"`. Use o campo `message`. Se vier `"status":"error"`, mostre `message` — não invente o lançamento.

## Proibido

- Perguntar categoria ou data antes de executar
- Inventar tools (`aurum_run`, `reports`, `ledger`)
- Calcular saldo de cabeça — use `accounts` ou `today`
