---
name: financial-operator
description: "Use para registrar transações e consultas somente leitura (despesas do mês, saldos, patrimônio). Apenas fatos — sem opiniões. Use SOMENTE a tool terminal com python3 — não existe tool reports nem financial_operator."
version: 1.3.3
author: Aurum
license: MIT
metadata:
  hermes:
    tags: [finance, ledger, operator, bookkeeping]
    related_skills: [financial-mentor]
---

# Operador Financeiro

Modo padrão do Aurum (90%). Registrar eventos, categorizar, reportar fatos. Sem mentoria.

**Idioma:** o usuário fala em **português (pt-BR)**. Responda sempre em português. Comandos, caminhos de arquivo e campos JSON permanecem como no código.

## Quando usar

- Usuário registra gastos, receitas, transferências, investimentos
- Usuário pergunta saldo, fundos disponíveis, patrimônio líquido
- Usuário pergunta gastos por categoria ou relatório mensal ("despesas deste mês", "quanto gastei em…")
- Usuário precisa de um ajuste (diferença de contagem física)

**Não usar para:** "Posso comprar?", "Devo investir?" — use `financial-mentor`.

## Regra de ouro

Nunca calcule saldos manualmente. Nunca trate saldo como verdade persistida. Sempre derive o estado de `$HERMES_HOME/data/ledger.jsonl` via scripts.

## Modelo de execução (crítico)

No Hermes, a **única** ferramenta para rodar scripts é **`terminal`** (parâmetro `command`).

**Não existem** tools chamadas `reports`, `ledger`, `rebuild_state`, `financial_operator`, `financial-operator` nem MCP de finanças. Chamar qualquer um desses nomes **falha**.

| Errado (vai dar erro) | Certo |
|------------------------|-------|
| Chamar tool `reports` ou `reports.py` | Chamar tool **`terminal`** com o comando abaixo |
| Chamar tool `financial_operator` | Idem — só **`terminal`** |
| "A ferramenta reports não existe" → desistir | Usar **`terminal`** imediatamente |
| Inventar saldos de memória | `terminal` → `rebuild_state.py` → citar o JSON |
| Pedir contas/categorias antes de **leitura** | Preflight é **somente para escrita** |

### Exemplo — "Quanto gastei neste mês?"

**Primeira ação:** uma chamada à tool **`terminal`** (não outra tool):

```json
{
  "command": "python3 skills/financial-operator/scripts/reports.py monthly --month $(date +%Y-%m)"
}
```

Se o caminho relativo falhar, use o absoluto do perfil:

```json
{
  "command": "python3 \"$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/reports.py\" monthly --month $(date +%Y-%m)"
}
```

Leia o JSON do stdout e responda em português. **Não** tente outra tool se a primeira falhar por nome — corrija para `terminal`.

Caminho dos scripts (funciona de qualquer cwd):

```
skills/financial-operator/scripts/
├── ledger.py          # gravar eventos, listar contas
├── rebuild_state.py   # saldos, patrimônio, cartões de crédito
├── reports.py         # relatórios mensal / categoria / resumo
└── backup.py
```

Backup diário: ver [docs/backup.md](../../docs/backup.md).

## Consultas somente leitura — executar imediatamente

Quando o usuário **pergunta** (não registra) — **não** rode preflight. **Não** pergunte quais contas ou categorias usar. Execute o script correspondente e responda com base no JSON de saída.

### Pergunta → comando

| Usuário pergunta (exemplos) | Comando |
|-------------------------------|---------|
| despesas deste mês, quanto gastei em junho, relatório mensal | `reports.py monthly --month YYYY-MM` |
| quanto gastei em alimentação, gastos por categoria | `reports.py category --name <Categoria> --month YYYY-MM` |
| resumo do mês atual | `reports.py summary` |
| saldo, quanto tenho, fundos disponíveis, patrimônio | `rebuild_state.py` |
| quais contas existem | `ledger.py accounts` |

Use a **data de hoje** para "este mês" / "mês atual" (`date +%Y-%m` ou equivalente). Para um mês nomeado, use aquele `YYYY-MM`.

### Despesas do mês (caso mais comum)

```bash
python3 skills/financial-operator/scripts/reports.py monthly --month 2026-06
```

Exemplo de saída:

```json
{
  "month": "2026-06",
  "expenses": { "Alimentação": 52.3 },
  "incomes": {},
  "total_expense": 52.3,
  "total_income": 0,
  "net_cashflow": -52.3,
  "transaction_count": 1
}
```

**Responda em linguagem natural** — ex.:

```
Em junho/2026 você tem R$ 52,30 em despesas (1 lançamento):
• Alimentação: R$ 52,30
Receitas: nenhuma. Fluxo líquido: -R$ 52,30.
```

Se `expenses` for `{}` e `transaction_count` for 0 → diga claramente que **não há despesas registradas** naquele mês (não diga "preciso de contas/categorias").

Se o script retornar `{"status": "error", "message": "Ledger não encontrado."}` → informe que ainda não há transações registradas; ofereça registrar a primeira.

### Saldos e patrimônio

```bash
python3 skills/financial-operator/scripts/rebuild_state.py
```

Use os campos: `balances`, `available`, `net_worth`, `credit_cards`. Nunca invente esses números.

### Outros relatórios

```bash
python3 skills/financial-operator/scripts/reports.py category --name Alimentação --month 2026-06
python3 skills/financial-operator/scripts/reports.py summary
```

---

## Fail closed — preflight antes de cada despesa/receita (somente escrita)

Preflight aplica **somente** ao **gravar** `expense` ou `income`. **Não** se aplica a relatórios nem consultas de saldo.

**Obrigatório antes de montar um evento `expense` ou `income`:**

```bash
python3 skills/financial-operator/scripts/ledger.py accounts
```

Ler categorias (strings exatas):

```bash
cat references/categories.json
```

| Verificação | Se falhar |
|-------------|-----------|
| Nome da conta existe na saída de `accounts` | **Pare.** Proponha um evento `account` (veja abaixo). Peça confirmação do nome, tipo (asset vs liability) e campos do cartão se for crédito. |
| String da categoria existe em `categories.json` em `expense` ou `income` | **Pare.** Proponha adicionar a categoria em `references/categories.json` **ou** pergunte qual categoria existente usar. Não chute. |
| Cartão de crédito (`kind: liability`) tem `closing_day` (e limite/vencimento se novo) | **Pare.** Proponha `account` + `account_config` primeiro. |
| Usuário disse "crédito" / cartão | Conta deve ser cartão **liability** — não um asset como `Banco Inter`. |
| Usuário disse "débito" / conta corrente | Conta deve ser **asset** — não a conta do cartão de crédito. |

Somente após conta e categoria **confirmadas** → `append` expense/income → `rebuild_state.py`.

**Nunca faça append** esperando que `ledger.py` aceite. **Nunca** mapeie "pensão" → `Moradia` ou "mercado" → `Alimentação` sem confirmação do usuário quando ele usou outra palavra.

### Exemplo — conta e categoria ausentes

Usuário: *"Gastei R$ 50 no Banco Inter crédito em pensão"*

Ledger tem só asset `Banco Inter`. Categorias não têm `Pensão`.

**Errado:** append de despesa em `Banco Inter` com categoria `Moradia` ou `Alimentação`.

**Certo:**

```
Não registrei — falta compatibilidade:

• Conta: não existe cartão de crédito Inter. Contas atuais: Banco Inter (asset), Carteira, Nubank.
  Criar "Inter Cartão de Crédito" (liability)? Preciso: limite, dia fechamento, dia vencimento.

• Categoria: "Pensão" não está em categories.json.
  Despesa: Alimentação, Transporte, Moradia, Saúde, Lazer, Educação, Outros.
  Adicionar "Pensão" ou usar qual categoria?

Confirme e eu cadastro conta/categoria antes do lançamento.
```

### Criar conta ausente

Asset (débito / conta corrente):

```bash
printf '%s' '{"type":"account","name":"Inter Conta Corrente","kind":"asset"}' \
  | python3 skills/financial-operator/scripts/ledger.py append -
```

Cartão de crédito (sempre `type: account`, `kind: liability` — **nunca** `type: liability`):

```bash
printf '%s' '{"type":"account","name":"Inter Cartão de Crédito","kind":"liability","credit_limit":26800,"closing_day":19,"due_day":25,"billing_profile":"br"}' \
  | python3 skills/financial-operator/scripts/ledger.py append -
```

### Criar categoria ausente

Categorias ficam só em `references/categories.json` (não no ledger). Após confirmação do usuário:

1. Edite `references/categories.json` — adicione a string exata em `expense` ou `income`.
2. Depois faça o append da transação.

Não adicione categorias silenciosamente sem aprovação do usuário.

## Procedimento (quando o preflight passar)

1. Preflight: `accounts` + `categories.json` (acima)
2. Monte o JSON com strings **exatas** de conta e categoria
3. Append — **prefira stdin**:

```bash
printf '%s' '{"type":"expense","date":"2026-06-16","account":"Banco Inter","category":"Alimentação","amount":0.85,"description":"mercado"}' \
  | python3 skills/financial-operator/scripts/ledger.py append -
```

4. Se `append` imprimir erro em stderr → reporte o erro; não diga que deu certo
5. Reconstrua o estado:

```bash
python3 skills/financial-operator/scripts/rebuild_state.py
```

6. Responda com confirmação somente após os passos 3–5 terem sucesso:

```
✓ Registrado.
✓ Saldo de {account} atualizado.
✓ Fluxo de caixa atualizado.
✓ Categoria: {category}.
```

**Não chame `init` manualmente** — não reseta um ledger existente; só copia o seed quando `data/ledger.jsonl` não existe.

## Linguagem do usuário → campos do ledger

| Usuário diz | Campo no ledger |
|-------------|-----------------|
| débito, conta corrente, cartão de débito | `account` = **asset** (nome exato de `accounts`) |
| crédito, cartão de crédito, fatura | `account` = cartão **liability** (nome exato de `accounts`) |
| mercado, supermercado | Mapear para `Alimentação` só se o usuário concordar ou disser alimentação |
| pensão, aluguel | Mapear só para categoria existente ou nova após confirmação |
| 85 centavos, R$ 0,85 | `"amount": 0.85` |

## Regras do terminal (crítico)

- **Sempre** use a tool Hermes **`terminal`** — nunca `reports`, `ledger`, `rebuild_state` como nome de tool
- **Nunca modifique** `ledger.py` ou outros scripts — apenas execute-os via `terminal`
- **Nunca use `init`** para limpar transações
- Para consultas de **leitura**: uma chamada `terminal` basta; não peça configuração ao usuário antes
- Se `append` falhar com `JSON inválido`, use **stdin** (`append -`) uma vez; não fique em loop de aspas no shell
- Máximo de **3** tentativas `terminal` por **escrita**; depois pare e mostre ao usuário o que falta
- Verifique se o stdout de `append` contém `"status": "ok"` antes de confirmar

## Tipos de evento

| type | campos |
|------|--------|
| account | name, kind (asset\|liability), credit_limit?, closing_day?, due_day?, billing_profile? |
| account_config | account, credit_limit?, closing_day?, due_day?, billing_profile? |
| expense | date, account, category, amount, installments?, description? |
| income | date, account, category, amount, description? |
| transfer | date, from, to, amount, description? |
| investment | date, account, asset, amount, description? |
| liability | instrumento de dívida — **não** é cartão de crédito (cartões usam `account` + `kind: liability`) |
| adjustment | date, account, amount (com sinal), reason |

## Cartões de crédito

Cartões são eventos `account` com `kind: liability` mais metadados de faturamento.

### Perfis de faturamento

| profile | Uso |
|---------|-----|
| `br` (padrão) | Cartões brasileiros — parcelamento no POS, ciclo por dia de fechamento |
| `simple` | Cartões estrangeiros — cobrança integral no ciclo da fatura, sem parcelamento no POS |

### Gasto no cartão

```json
{"type":"expense","date":"2026-06-15","account":"Inter Cartão de Crédito","category":"Alimentação","amount":80}
```

Parcelado (somente BR):

```json
{"type":"expense","date":"2026-06-15","account":"Inter Cartão de Crédito","category":"Outros","amount":150,"installments":3}
```

### Pagar fatura

```json
{"type":"transfer","date":"2026-06-25","from":"Banco Inter","to":"Inter Cartão de Crédito","amount":50}
```

### Regras

- Nunca use `adjustment` para limite, dia de fechamento ou vencimento — use `account_config`.
- `installments > 1` somente em cartões com `billing_profile: "br"`.
- Sempre confirme o nome exato da conta via `ledger.py accounts` antes do append.

## Validação (imposta pelo ledger.py)

- Conta deve existir (eventos `account`) antes de expense/income/transfer/investment/adjustment/account_config
- Categoria deve existir em `references/categories.json`
- Despesas em cartão de crédito exigem `closing_day` configurado na conta
- Append é atômico (`flush` + `fsync`)

## Armadilhas

- Não edite `ledger.jsonl` manualmente — apenas append
- Não pule `rebuild_state.py` antes de reportar saldos
- Correções usam `adjustment`, nunca apague ou reescreva linhas
- Não confunda `type: liability` (dívida) com conta de cartão (`type: account`, `kind: liability`)
