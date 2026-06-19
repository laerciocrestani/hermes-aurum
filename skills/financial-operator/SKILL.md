---
name: financial-operator
description: "Registre despesas com compose --run e consulte via terminal. NÃO chame aurum_run — só terminal com caminho absoluto."
version: 1.4.4
author: Aurum
license: MIT
metadata:
  hermes:
    tags: [finance, ledger, operator, bookkeeping]
    related_skills: [financial-mentor]
---

# Operador Financeiro

## CRÍTICO — única tool: `terminal`

No Hermes existe **somente** a tool **`terminal`** (`command` = shell).

**NÃO EXISTEM** tools `aurum_run`, `aurum-run`, `reports`, `ledger`, `financial_operator`.

Caminho do script:

```
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run
```

## Registrar despesa — uma chamada, sem explicar antes

Quando o usuário disser **gastei**, **paguei**, **comprei** (com valor):

1. Chame **`terminal`** imediatamente — **não** explique "para registrar vou..."
2. Use **`compose --run`** com o texto **exato** do usuário
3. Só confirme ao usuário se o JSON tiver `"status":"ok"`

```json
{
  "command": "$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run compose --run \"Gastei 33 reais no C6bank crédito em 3x\""
}
```

| Frase do usuário | Comando |
|------------------|---------|
| gastei X no crédito em Nx | `compose --run "<frase>"` |
| mercado no Inter débito | `compose --run "<frase>"` |
| transferi / saquei | `do record-transfer` com JSON |
| pagamento misto (duas contas) | `do record-mixed-expense` |

**Crédito em N parcelas numa conta** → `compose --run` (vira `record-expense` com `installments`).

**Proibido:** narrar o que vai fazer; perguntar "quer que eu registre?"; responder "O comando..." sem executar.

## Consultas

| Usuário pergunta | `terminal` → `command` |
|------------------|------------------------|
| liste contas | `.../aurum-run do list-accounts` |
| quanto gastei | `.../aurum-run do monthly-report` |
| saldo | `.../aurum-run do balances` |
| menu / ajuda | `.../aurum-run menu` |

## Regras de domínio

| Usuário diz | Ação |
|-------------|------|
| mercado | categoria Alimentação |
| roupas | Vestuário |
| crédito / Nx | conta `credit` (cartão) |
| débito / PIX | conta `debit` (asset) |
| sem categoria | Outros (compose faz isso) |

## Fail closed

- `compose` retorna erro de conta → `do list-accounts` e use nome exato
- Confirme registro **só** após `"status":"ok"` no stdout
- Se perguntarem "registrou?" → rode `do monthly-report` ou confira o último `compose --run`

## Proibições

- Chamar tool que não seja `terminal`
- Explicar em vez de executar
- Inventar saldos ou dizer que registrou sem `status: ok`
