---
name: financial-operator
description: "Registre e consulte finanças via tool terminal APENAS. Execute scripts shell com caminho absoluto. NÃO chame aurum_run, aurum-run, reports, ledger, financial_operator — essas tools NÃO EXISTEM."
version: 1.4.2
author: Aurum
license: MIT
metadata:
  hermes:
    tags: [finance, ledger, operator, bookkeeping]
    related_skills: [financial-mentor]
---

# Operador Financeiro

## CRÍTICO — única tool: `terminal`

No Hermes existe **somente** a tool **`terminal`** (parâmetro `command` = string shell).

**NÃO EXISTEM** tools chamadas:
`aurum_run`, `aurum-run`, `aurum run`, `do`, `hint`, `help`, `reports`, `ledger`, `financial_operator`, `financial-operator`

Chamar qualquer nome acima **falha**. O script `aurum-run` é um **arquivo shell**, não uma tool.

### Exemplo correto — listar contas

Chame a tool **`terminal`** com:

```json
{
  "command": "$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run do list-accounts"
}
```

Leia o JSON do stdout. Use `debit` e `credit`. Responda em português.

### Exemplo ERRADO (nunca faça)

- Chamar tool `aurum_run` ❌
- Chamar tool `aurum-run` ❌
- Dizer "ferramenta não encontrada" e desistir ❌

Se `terminal` falhar, corrija o **caminho shell** — não invente outra tool.

Caminho absoluto padrão:

```
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run
```

## Pergunta → ação imediata

| Usuário pergunta | `terminal` → `command` |
|------------------|------------------------|
| liste contas, débito e crédito | `.../aurum-run do list-accounts` |
| comandos básicos, menu, ajuda | `.../aurum-run menu` |
| quanto gastei este mês | `.../aurum-run do monthly-report` |
| saldo, patrimônio | `.../aurum-run do balances` |
| não sabe o comando | `.../aurum-run hint "<palavras do usuário>"` → depois execute o `command` do JSON com **`terminal`** |

**Proibido** dizer "sem contas" sem rodar `do list-accounts` e ver `account_count > 0`.

## Escrita — sempre via `terminal`

```json
{
  "command": "$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run do record-expense '{\"amount\":50,\"account\":\"Banco Inter\",\"category\":\"Alimentação\",\"description\":\"Mercado\"}'"
}
```

| Intenção | Quando |
|----------|--------|
| `do record-expense` | Despesa simples (débito, PIX, crédito) |
| `do record-transfer` | Transferência, saque entre contas |
| `do record-mixed-expense` | Pagamento misto / parcelado |
| `do record-income` | Receita |
| `do add-category` | Categoria nova (após confirmação) |
| `do add-account` | Conta nova |

## Regras de domínio

| Usuário diz | Ação |
|-------------|------|
| mercado | `category`: Alimentação, `description`: Mercado |
| roupas | `category`: Vestuário |
| débito, PIX | conta em `debit` (asset) |
| crédito, parcelado | conta em `credit` (liability) |
| transferi, saquei | `do record-transfer` |

## Fail closed

- Conta/categoria ausente → `do add-account` / `do add-category` ou pergunte — **nunca** chute
- Confirme só após `"status":"ok"` no stdout

## Proibições

- Chamar tool que não seja `terminal`
- Inventar saldos
- Propor arquitetura ou `/menu` quando usuário pede ação — **execute** `menu` ou `do list-accounts`
- Desistir após erro — use caminho absoluto do shell
