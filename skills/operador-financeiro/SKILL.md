---
name: operador-financeiro
description: "Use for logging transactions, balances, reports, and net worth. Facts only — no opinions. Always run ledger.py and rebuild_state.py scripts."
version: 1.0.0
author: Aurum
license: MIT
metadata:
  hermes:
    tags: [finance, ledger, operator, bookkeeping]
    related_skills: [mentor-financeiro]
---

# Financial Operator

Default Aurum mode (90%). Register events, categorize, report facts. No mentoring.

## When to Use

- User logs spending, income, transfers, investments
- User asks balance, available funds, net worth
- User asks spending by category or monthly reports
- User needs an adjustment (physical count mismatch)

**Do not use for:** "Can I buy?", "Should I invest?" — use `mentor-financeiro`.

## Golden Rule

Never calculate balances manually. Never store balances as truth. Always derive state from `$HERMES_HOME/data/ledger.jsonl` via scripts.

## Scripts

All scripts live next to this skill:

```
skills/operador-financeiro/scripts/
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
python3 skills/operador-financeiro/scripts/ledger.py append '<json>'
```

4. Rebuild state:

```bash
python3 skills/operador-financeiro/scripts/rebuild_state.py
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
| account | name, kind (asset\|liability) |
| expense | date, account, category, amount, description? |
| income | date, account, category, amount, description? |
| transfer | date, from, to, amount, description? |
| investment | date, account, asset, amount, description? |
| liability | date, name, amount, monthly_payment?, description? |
| adjustment | date, account, amount (signed), reason |

## Reports

```bash
python3 skills/operador-financeiro/scripts/reports.py monthly --month 2026-06
python3 skills/operador-financeiro/scripts/reports.py category --name Food --month 2026-06
python3 skills/operador-financeiro/scripts/reports.py summary
```

## Validation (enforced by ledger.py)

- Account must exist (from `account` events) before expense/income/transfer/investment/adjustment
- Category must exist in `references/categories.json`
- Append is atomic (`flush` + `fsync`)

## Pitfalls

- Do not edit ledger.jsonl manually — append only
- Do not skip rebuild_state.py before reporting balances
- Corrections use `adjustment`, never delete or rewrite lines
