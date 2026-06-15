---
name: financial-operator
description: "Use for logging transactions, balances, reports, and net worth. Facts only — no opinions. Always run ledger.py and rebuild_state.py scripts."
version: 1.0.0
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
└── reports.py
```

Run from repo root or any cwd — paths resolve via `__file__`.

## Procedure

1. Interpret user intent → build JSON event
2. If category missing, suggest from `references/categories.json`
3. Append event (auto-inits ledger on first write):

```bash
python3 skills/financial-operator/scripts/ledger.py append '<json>'
```

4. Rebuild state:

```bash
python3 skills/financial-operator/scripts/rebuild_state.py
```

5. Reply with confirmation (no opinions):

```
✓ Recorded.
✓ Updated {account} balance.
✓ Updated cash flow.
✓ Category: {category}.
```

**Do not call `init` manually** — `append` handles first-time setup.

## Event Types

| type | fields |
|------|--------|
| account | name, kind (asset\|liability), credit_limit?, closing_day?, due_day?, billing_profile? |
| account_config | account, credit_limit?, closing_day?, due_day?, billing_profile? |
| expense | date, account, category, amount, installments?, description? |
| income | date, account, category, amount, description? |
| transfer | date, from, to, amount, description? |
| investment | date, account, asset, amount, description? |
| liability | date, name, amount, monthly_payment?, description? |
| adjustment | date, account, amount (signed), reason |

## Credit cards

Credit cards are `account` events with `kind: liability` plus billing metadata.

### Billing profiles

| profile | Use |
|---------|-----|
| `br` (default) | Brazilian cards — POS installments, closing-day cycle |
| `simple` | Foreign cards — full charge on statement cycle, no POS installments |

When registering a foreign card, ask country/issuer and set `billing_profile: "simple"`.

### Register a card

```bash
python3 skills/financial-operator/scripts/ledger.py append \
  '{"type":"account","name":"Inter Cartão de Crédito","kind":"liability","credit_limit":26800,"closing_day":19,"due_day":25}'

# Or update config later:
python3 skills/financial-operator/scripts/ledger.py append \
  '{"type":"account_config","account":"Inter Cartão de Crédito","credit_limit":26800,"closing_day":19,"due_day":25}'
```

### Spend on card

À vista:

```json
{"type":"expense","date":"2026-06-15","account":"Inter Cartão de Crédito","category":"Food","amount":80}
```

Parcelado (BR only):

```json
{"type":"expense","date":"2026-06-15","account":"Inter Cartão de Crédito","category":"Other","amount":150,"installments":3}
```

Confirm the derived schedule (e.g. R$ 50 on faturas 06/07/08 when purchase is before closing day 19).

### Pay statement

```json
{"type":"transfer","date":"2026-06-25","from":"Banco Inter","to":"Inter Cartão de Crédito","amount":50}
```

### Rules

- Never use `adjustment` for limit, closing day, or due day — use `account_config`.
- `installments > 1` only on cards with `billing_profile: "br"`.
- Best purchase day = day after closing → map user "melhor dia de compra" to `closing_day`.
- Always confirm exact account name via `ledger.py accounts` before append.

---

## Reports

```bash
python3 skills/financial-operator/scripts/reports.py monthly --month 2026-06
python3 skills/financial-operator/scripts/reports.py category --name Food --month 2026-06
python3 skills/financial-operator/scripts/reports.py summary
```

## Validation (enforced by ledger.py)

- Account must exist (from `account` events) before expense/income/transfer/investment/adjustment/account_config
- Category must exist in `references/categories.json`
- Credit card expenses require `closing_day` configured on the account
- Append is atomic (`flush` + `fsync`)

## Pitfalls

- Do not edit ledger.jsonl manually — append only
- Do not skip rebuild_state.py before reporting balances
- Corrections use `adjustment`, never delete or rewrite lines
- Credit cards use `account` + `account_config`, not `adjustment` for billing metadata
