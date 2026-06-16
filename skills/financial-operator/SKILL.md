---
name: financial-operator
description: "Use for logging transactions, balances, reports, and net worth. Facts only — no opinions. Always run ledger.py and rebuild_state.py scripts."
version: 1.2.0
author: Aurum
license: MIT
metadata:
  hermes:
    tags: [finance, ledger, operator, bookkeeping]
    related_skills: [financial-mentor]
---

# Financial Operator

Default Aurum mode (90%). Register events, categorize, report facts. No mentoring.

## When to Use

- User logs spending, income, transfers, investments
- User asks balance, available funds, net worth
- User asks spending by category or monthly reports
- User needs an adjustment (physical count mismatch)

**Do not use for:** "Can I buy?", "Should I invest?" — use `financial-mentor`.

## Golden Rule

Never calculate balances manually. Never store balances as truth. Always derive state from `$HERMES_HOME/data/ledger.jsonl` via scripts.

## Scripts

All scripts live next to this skill:

```
skills/financial-operator/scripts/
├── ledger.py
├── rebuild_state.py
├── reports.py
└── backup.py
```

Daily backup: see [docs/backup.md](../../docs/backup.md).

Run from repo root or any cwd — paths resolve via `__file__`.

## Fail closed — preflight before every expense/income

**Mandatory before building an `expense` or `income` event:**

```bash
python3 skills/financial-operator/scripts/ledger.py accounts
```

Read categories (exact strings only):

```bash
cat references/categories.json
```

| Check | If it fails |
|-------|-------------|
| Account name exists in `accounts` output | **Stop.** Propose a new `account` event (see below). Ask user to confirm name, kind (asset vs liability), and card fields if credit. |
| Category string exists in `categories.json` under `expense` or `income` | **Stop.** Propose adding the category to `references/categories.json` **or** ask which existing category to use. Do not guess. |
| Credit card (`kind: liability`) has `closing_day` (and limit/due if new) | **Stop.** Propose `account` + `account_config` first. |
| User said "crédito" / cartão | Account must be a **liability** card name — not an asset like `Banco Inter`. |
| User said "débito" / conta corrente | Account must be an **asset** — not the credit card account. |

Only after account and category are **confirmed** → `append` expense/income → `rebuild_state.py`.

**Never append** hoping `ledger.py` will accept it. **Never** map "pensão" → `Moradia` or "mercado" → `Alimentação` without user confirmation when the user used a different word.

### Example — missing account and category

User: *"Gastei R$ 50 no Banco Inter crédito em pensão"*

Ledger has only asset `Banco Inter`. Categories have no `Pensão`.

**Wrong:** append expense to `Banco Inter` with category `Moradia` or `Alimentação`.

**Right:**

```
Não registrei — falta compatibilidade:

• Conta: não existe cartão de crédito Inter. Contas atuais: Banco Inter (asset), Carteira, Nubank.
  Criar "Inter Cartão de Crédito" (liability)? Preciso: limite, dia fechamento, dia vencimento.

• Categoria: "Pensão" não está em categories.json.
  Despesa: Alimentação, Transporte, Moradia, Saúde, Lazer, Educação, Outros.
  Adicionar "Pensão" ou usar qual categoria?

Confirme e eu cadastro conta/categoria antes do lançamento.
```

### Creating a missing account

Asset (débito / conta corrente):

```bash
printf '%s' '{"type":"account","name":"Inter Conta Corrente","kind":"asset"}' \
  | python3 skills/financial-operator/scripts/ledger.py append -
```

Credit card (always `type: account`, `kind: liability` — **never** `type: liability`):

```bash
printf '%s' '{"type":"account","name":"Inter Cartão de Crédito","kind":"liability","credit_limit":26800,"closing_day":19,"due_day":25,"billing_profile":"br"}' \
  | python3 skills/financial-operator/scripts/ledger.py append -
```

### Creating a missing category

Categories live only in `references/categories.json` (not in the ledger). After user confirms:

1. Edit `references/categories.json` — add the exact string under `expense` or `income`.
2. Then append the transaction.

Do not add categories silently without user approval.

## Procedure (when preflight passes)

1. Preflight: `accounts` + `categories.json` (above)
2. Build JSON with **exact** account and category strings
3. Append — **prefer stdin**:

```bash
printf '%s' '{"type":"expense","date":"2026-06-16","account":"Banco Inter","category":"Alimentação","amount":0.85,"description":"mercado"}' \
  | python3 skills/financial-operator/scripts/ledger.py append -
```

4. If `append` prints error to stderr → report the error; do not claim success
5. Rebuild state:

```bash
python3 skills/financial-operator/scripts/rebuild_state.py
```

6. Reply with confirmation only after steps 3–5 succeed:

```
✓ Recorded.
✓ Updated {account} balance.
✓ Updated cash flow.
✓ Category: {category}.
```

**Do not call `init` manually** — it does not reset an existing ledger; it only copies seed when `data/ledger.jsonl` is absent.

## Language → ledger mappings

| User says | Ledger field |
|-----------|--------------|
| débito, conta corrente, cartão de débito | `account` = **asset** (exact name from `accounts`) |
| crédito, cartão de crédito, fatura | `account` = **liability** card (exact name from `accounts`) |
| mercado, supermercado | Map to `Alimentação` only if user agrees or said alimentação |
| pensão, aluguel | Map only to an existing category or new one after confirmation |
| 85 centavos, R$ 0,85 | `"amount": 0.85` |

## Terminal rules (critical)

- **Never modify** `ledger.py` or other scripts — only call them
- **Never use `init`** to clear transactions
- If `append` fails with `Invalid JSON`, switch to **stdin** (`append -`) once; do not loop shell quoting
- Max **3** terminal attempts per transaction; then stop and show the user what is missing
- Verify `append` stdout contains `"status": "ok"` before confirming

## Event Types

| type | fields |
|------|--------|
| account | name, kind (asset\|liability), credit_limit?, closing_day?, due_day?, billing_profile? |
| account_config | account, credit_limit?, closing_day?, due_day?, billing_profile? |
| expense | date, account, category, amount, installments?, description? |
| income | date, account, category, amount, description? |
| transfer | date, from, to, amount, description? |
| investment | date, account, asset, amount, description? |
| liability | debt instrument — **not** a credit card (use `account` + `kind: liability` for cards) |
| adjustment | date, account, amount (signed), reason |

## Credit cards

Credit cards are `account` events with `kind: liability` plus billing metadata.

### Billing profiles

| profile | Use |
|---------|-----|
| `br` (default) | Brazilian cards — POS installments, closing-day cycle |
| `simple` | Foreign cards — full charge on statement cycle, no POS installments |

### Spend on card

```json
{"type":"expense","date":"2026-06-15","account":"Inter Cartão de Crédito","category":"Alimentação","amount":80}
```

Parcelado (BR only):

```json
{"type":"expense","date":"2026-06-15","account":"Inter Cartão de Crédito","category":"Outros","amount":150,"installments":3}
```

### Pay statement

```json
{"type":"transfer","date":"2026-06-25","from":"Banco Inter","to":"Inter Cartão de Crédito","amount":50}
```

### Rules

- Never use `adjustment` for limit, closing day, or due day — use `account_config`.
- `installments > 1` only on cards with `billing_profile: "br"`.
- Always confirm exact account name via `ledger.py accounts` before append.

---

## Reports

```bash
python3 skills/financial-operator/scripts/reports.py monthly --month 2026-06
python3 skills/financial-operator/scripts/reports.py category --name Alimentação --month 2026-06
python3 skills/financial-operator/scripts/reports.py summary
```

## Validation (enforced by ledger.py)

- Account must exist (from `account` events) before expense/income/transfer/investment/adjustment/account_config
- Category must exist in `references/categories.json`
- Credit card expenses require `closing_day` configured on the account
- Append is atomic (`flush` + `fsync`)

## Pitfalls

- Do not edit `ledger.jsonl` manually — append only
- Do not skip `rebuild_state.py` before reporting balances
- Corrections use `adjustment`, never delete or rewrite lines
- Do not confuse `type: liability` (debt) with credit card accounts (`type: account`, `kind: liability`)
