# Aurum — Personal Finance Agent for Hermes

> Event-sourced personal finance for [Hermes Agent](https://github.com/NousResearch/hermes-agent). Records transactions, rebuilds net worth from history, and offers financial mentoring only when you ask.

[![Status](https://img.shields.io/badge/status-MVP-yellow)](ROADMAP.md)
[![Hermes](https://img.shields.io/badge/Hermes-Agent-blue)](https://github.com/NousResearch/hermes-agent)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Open source** — free to use, fork, and contribute.

## What is Aurum?

**Aurum** is a conversational agent for [Hermes Agent](https://github.com/NousResearch/hermes-agent) with two modes:

| Mode | When | Behavior |
|------|------|----------|
| **Financial Operator** (90%) | Logging, balances, reports | Facts only. No opinions. |
| **Financial Mentor** (10%) | "Can I invest?", "Should I pay off debt?" | Guidance based on your recorded data |

### Philosophy

> Aurum is an event-based financial manager. Its primary goal is to faithfully record your financial activity, reconstruct your net worth at any time, and provide financial guidance based exclusively on the data you have logged.

### Golden rule

- Balances are **never** stored as absolute truth
- Net worth is **always derived** from the event history
- The ledger is **append-only** — corrections use an `adjustment` event, never line edits

## Example

```
You: I spent R$ 52.30 at the grocery store using Inter.

Aurum:
✓ Recorded.
✓ Updated Inter balance.
✓ Updated cash flow.
✓ Category: Food.

You: How much do I have available?
Aurum: [runs rebuild_state.py — facts derived from the ledger]

You: Can I invest R$ 5,000 in BTC?
Aurum: [mentor mode — facts + qualified analysis]
```

## Prerequisites

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed (`hermes` CLI)
- Python 3.10+
- Model provider API key configured in your Hermes profile

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/laerciocrestani/hermes-aurum.git
cd hermes-aurum
```

### 2. Create a Hermes profile

```bash
hermes profile create aurum --description "Personal ledger + financial mentoring"
```

### 3. Install skills into the profile

**Symlink (recommended for development):**

```bash
REPO="$(pwd)"
PROFILE="$HOME/.hermes/profiles/aurum"
mkdir -p "$PROFILE/skills"

ln -sf "$REPO/skills/operador-financeiro" "$PROFILE/skills/operador-financeiro"
ln -sf "$REPO/skills/mentor-financeiro" "$PROFILE/skills/mentor-financeiro"
```

**Copy (stable usage):**

```bash
cp -r skills/* ~/.hermes/profiles/aurum/skills/
cp -r references ~/.hermes/profiles/aurum/
```

### 4. Configure SOUL and model

```bash
cp docs/SOUL.example.md ~/.hermes/profiles/aurum/SOUL.md

# Set model and temperature (~0.2) in:
# ~/.hermes/profiles/aurum/config.yaml
```

### 5. Run

```bash
aurum chat
```

On the first recorded transaction, the ledger is created automatically at `$HERMES_HOME/data/ledger.jsonl`.

## Repository structure

```
hermes-aurum/
├── README.md
├── ROADMAP.md
├── agent.yaml
├── docs/
│   └── SOUL.example.md
├── references/
│   ├── categories.json
│   └── ledger.seed.jsonl
└── skills/
    ├── operador-financeiro/
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── ledger.py
    │       ├── rebuild_state.py
    │       └── reports.py
    └── mentor-financeiro/
        └── SKILL.md
```

### Where data lives

| Data | Location | Versioned? |
|------|----------|------------|
| Skills and scripts | This repository | Yes |
| SOUL + Hermes config | `~/.hermes/profiles/aurum/` | No (local) |
| Your ledger | `$HERMES_HOME/data/ledger.jsonl` | **Never commit** |

## Data model (JSONL)

Each ledger line is an independent JSON event:

```jsonl
{"type":"account","name":"Banco Inter","kind":"asset"}
{"type":"expense","date":"2026-06-10","account":"Banco Inter","category":"Food","amount":52.30,"description":"Grocery"}
{"type":"income","date":"2026-06-10","account":"Banco Inter","category":"Salary","amount":5000}
{"type":"transfer","date":"2026-06-10","from":"Banco Inter","to":"Carteira","amount":100}
{"type":"investment","date":"2026-06-10","account":"Banco Inter","asset":"BTC","amount":500}
{"type":"adjustment","date":"2026-06-10","account":"Carteira","amount":15,"reason":"Physical count"}
```

Supported types: `account`, `expense`, `income`, `transfer`, `investment`, `liability`, `adjustment`.

## Scripts (direct usage)

```bash
SCRIPT="skills/operador-financeiro/scripts"

# Log an expense (auto-inits ledger on first run)
python3 "$SCRIPT/ledger.py" append '{"type":"expense","date":"2026-06-10","account":"Banco Inter","category":"Food","amount":52.30,"description":"Grocery"}'

# Rebuild financial state
python3 "$SCRIPT/rebuild_state.py"

# Monthly report
python3 "$SCRIPT/reports.py" monthly --month 2026-06
```

## Implemented (MVP v1.0)

- [x] Append-only JSONL ledger
- [x] Financial operator (logging, categorization, reports)
- [x] Financial mentor (on demand)
- [x] State reconstruction from event history
- [x] Account and category validation on append
- [x] Atomic writes (`flush` + `fsync`)
- [x] Auto-init on first write
- [x] Events: account, expense, income, transfer, investment, liability, adjustment

## Not implemented yet

See [ROADMAP.md](ROADMAP.md) for detailed future plans.

## Contributing

1. Read [ROADMAP.md](ROADMAP.md) before large PRs
2. Open issues for future features — don't implement silently
3. Keep the golden rule: derived balances, never persisted

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

Aurum is **not** regulated financial advice. Mentor mode offers guidance based on data you logged, with caveats. Financial decisions are your responsibility.
