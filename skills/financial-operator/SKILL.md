---
name: financial-operator
description: "Registre despesas com compose --run. Não pergunte categoria/data — use defaults. NÃO chame aurum_run."
version: 1.4.5
author: Aurum
license: MIT
metadata:
  hermes:
    tags: [finance, ledger, operator, bookkeeping]
    related_skills: [financial-mentor]
---

# Operador Financeiro

## CRÍTICO — única tool: `terminal`

Caminho:

```
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run
```

## Registrar despesa — execute na hora

Quando o usuário disser **gastei**, **paguei**, **comprei** (com valor):

1. **`terminal`** → `compose --run` com texto do usuário — **imediatamente**
2. **Não pergunte** categoria nem data — `compose` usa **Outros** e **hoje** por padrão
3. Confirme **só** se `"status":"ok"`

```json
{
  "command": "$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run compose --run \"Gastei 70 reais no C6bank crédito em 3x\""
}
```

### Categoria e data (opcionais na mesma frase)

Inclua na frase — **não** peça em mensagem separada:

| Usuário diz | compose entende |
|-------------|-----------------|
| vestuário, roupas | categoria **Vestuário** |
| mercado | **Alimentação** |
| hoje / ontem | data automática |
| (nada) | **Outros** + hoje |

Exemplo completo em **uma mensagem**:

```
Gastei 70 reais no C6bank crédito em 3x vestuário hoje
```

### Se o usuário responder depois com categoria/data

**Junte** com a frase anterior e rode `compose --run` de novo:

```
Gastei 70 reais no C6bank crédito em 3x vestuário hoje
```

Ou use JSON explícito:

```json
{
  "command": "$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run compose --run '{\"amount\":70,\"account\":\"C6 Bank\",\"category\":\"Vestuário\",\"installments\":3}'"
}
```

Categorias válidas: Alimentação, Transporte, Moradia, Saúde, Lazer, Educação, Vestuário, Outros.

**Proibido:** perguntar categoria/data antes de executar; dizer "ocorreu um erro, tente mais tarde" sem mostrar o JSON de erro do terminal.

## Consultas

| Pergunta | Comando |
|----------|---------|
| contas | `do list-accounts` |
| gastos do mês | `do monthly-report` |
| saldo | `do balances` |

## Fail closed

- Erro de cartão sem `closing_day` → execute o `fix_command` do JSON ou `do update-account`
- Conta errada → `do list-accounts`
