---
name: cashflow
description: "Insere, remove ou edita o fluxo de caixa a partir de mensagens do dia a dia. Execute apply imediatamente."
version: 2.0.0
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

Quando o usuário descrever um gasto, uma receita, uma correção ou uma exclusão, execute **na hora**. Não pergunte categoria nem data.

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
| dia/mês | `list --date YYYY-MM-DD` / `list --month YYYY-MM` |
| contas | `accounts` |
| categorias | `categories` |

## Confirmação

Confirme **somente** se `"status":"ok"`. Use o campo `message`. Se vier `"status":"error"`, mostre `message` — não invente o lançamento.

## Proibido

- Perguntar categoria ou data antes de executar
- Inventar tools (`aurum_run`, `reports`, `ledger`)
- Calcular saldo de cabeça — use `today` ou `list`
