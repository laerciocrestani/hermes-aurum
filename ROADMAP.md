# Roadmap — Aurum

This document explicitly separates what **exists today** from what is **planned**.
Items marked as planned are **not implemented** — do not confuse them with the README.

## Legend

| Symbol | Meaning |
|--------|---------|
| Shipped | Available in MVP |
| In progress | Under development |
| Planned | Contributions welcome via issue/PR |
| Idea | No priority yet |

---

## MVP v1.0 — Shipped

- Personal append-only ledger (`ledger.jsonl`)
- Hermes skills: `financial-operator` + `financial-mentor`
- Scripts: `ledger.py`, `rebuild_state.py`, `reports.py`
- Events: account, account_config, expense, income, transfer, investment, liability, adjustment
- Credit cards: liability accounts with billing cycle (BR parcelamento + simple international profile)
- Net worth derived from history (balances never persisted)
- Account (`account` event) and category (`categories.json`) validation on append
- Atomic writes with `flush()` + `os.fsync()`
- Ledger auto-init on first write
- Operator (90%) / mentor (10%) separation

---

## v1.x — Incremental improvements (Planned)

Improvements that **do not change** the event-sourced architecture:

| Item | Description | Priority |
|------|-------------|----------|
| Custom categories | Add categories via event or config, not only fixed `categories.json` | High |
| Account aliases | Map "Inter" to "Banco Inter" in agent interpretation | Medium |
| Annual report | `reports.py yearly --year 2026` | Medium |
| CSV export | Export transactions to spreadsheet | Low |
| Automated tests | pytest suite for ledger, rebuild, reports | High |
| Credit card alerts | Reminders for closing/due dates from `credit_cards` state | Medium |
| SOUL variants | Conservative vs direct tone in `docs/SOUL.example.md` | Low |

---

## v2.0 — Integrations (Planned)

Larger features — **require separate design**:

| Item | Description | Dependencies | Status |
|------|-------------|--------------|--------|
| Open Finance | Import transactions from Brazilian banks | Regulatory API, user consent | Planned |
| OFX/CSV import | Bank statement parser | Account/category mapping | Planned |
| Asset quotes | Live BTC, ETF, stock prices | External API (Yahoo, etc.) | Planned |
| Financial goals | `goal` event + tracking | Extended JSONL schema | Idea |
| Monthly budget | Per-category limits + alerts | Reports + events | Idea |

---

## v3.0 — Experience (Idea)

| Item | Description | Status |
|------|-------------|--------|
| Web UI | Net worth and spending dashboard | Idea |
| Multi-currency | USD, EUR beyond BRL | Idea |
| Telegram/Discord gateway | Aurum via Hermes messaging gateways | Planned |
| Profile distribution | Package as `hermes profile install` | Idea |

---

## Explicitly out of scope

Aurum targets **personal** finance, not institutional:

- Family office / institutional wealth management
- DCF / LBO / M&A modeling (Hermes corporate finance skills)
- Trade execution or brokerage integration
- Automated buy/sell orders

---

## How to contribute to the roadmap

1. Open an **issue** describing the feature and which phase it fits
2. Align on design before large PRs (v2+)
3. v1.x PRs welcome if they keep the golden rule (event-sourced, append-only)

## Changelog

| Version | Date | Notes |
|---------|------|-------|
| v1.2.1 | 2026-06-16 | Gemini Flash Lite primário + Flash fallback (menos 503 no Telegram) |
| v1.2.0 | 2026-06-16 | Fail-closed: validar conta/categoria antes de append; sugerir criação; proibir init/reset falso |
| v1.1.0 | 2026-06-16 | Categorias pt-BR; backup diário (`backup.py`); `ledger append -` (stdin); provider Gemini; skill operator reforçado |
| v1.0.0 | 2026-06-10 | Initial MVP |
