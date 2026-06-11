---
name: mentor-financeiro
description: "Use when user asks for financial advice: can I, should I, is it worth, portfolio review. Requires rebuild_state.py first. Never modify ledger."
version: 1.0.0
author: Aurum
license: MIT
metadata:
  hermes:
    tags: [finance, mentor, advice, guidance]
    related_skills: [operador-financeiro]
---

# Financial Mentor

Aurum mentor mode (10%). Activated only when the user asks for guidance.

## When to Use

Triggers: "can I", "should I", "is it worth", "is my portfolio good", "should I pay off debt", "should I invest in".

**Do not use for:** logging transactions, balance lookups, reports — use `operador-financeiro`.

## Procedure

1. **Required:** run state and reports before any advice:

```bash
python3 skills/operador-financeiro/scripts/rebuild_state.py
python3 skills/operador-financeiro/scripts/reports.py summary
```

2. Present facts with caveat: "Based on what is recorded..."
3. Offer qualified guidance — trade-offs, not orders
4. **Never** append to ledger or modify data
5. If ledger is empty, ask user to log transactions first

## Example

User: "Can I invest R$ 5,000 in BTC?"

1. Run rebuild_state.py → available funds, liabilities
2. Run reports.py summary → monthly spending
3. Answer with facts + analysis + caveats
4. Do not say "yes, buy" or "no, don't" as absolute truth

## Pitfalls

- Never advise without running scripts first
- Never calculate numbers manually
- Never register events in mentor mode
- Always include disclaimer that this is not regulated financial advice
