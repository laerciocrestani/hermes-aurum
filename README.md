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

ln -sf "$REPO/skills/financial-operator" "$PROFILE/skills/financial-operator"
ln -sf "$REPO/skills/financial-mentor" "$PROFILE/skills/financial-mentor"
ln -sf "$REPO/references" "$PROFILE/references"
```

**Copy (stable usage):**

```bash
cp -r skills/* ~/.hermes/profiles/aurum/skills/
cp -r references ~/.hermes/profiles/aurum/
```

### 4. Customize categories (required)

The operator skill maps your natural language to **exact** category strings in `references/categories.json`. `ledger.py` rejects any category not listed there.

**Edit the file in your native language** so the agent understands how you describe expenses and income:

| Install method | File to edit |
|----------------|--------------|
| Symlink (skills) | `references/categories.json` in this repo |
| Copy | `~/.hermes/profiles/aurum/references/categories.json` |

Default categories are in English. Example for Portuguese:

```json
{
  "expense": [
    "Alimentação",
    "Transporte",
    "Moradia",
    "Saúde",
    "Lazer",
    "Educação",
    "Outros"
  ],
  "income": [
    "Salário",
    "Freelance",
    "Investimentos",
    "Outros"
  ]
}
```

After editing, use those exact names when logging — e.g. `"category": "Alimentação"` in the ledger. The agent will suggest from this list when you do not specify a category.

You can add or remove categories, but keep the `expense` and `income` keys. Restart is not required; the scripts read the file on each append.

### 5. Configure SOUL and model

```bash
cp docs/SOUL.example.md ~/.hermes/profiles/aurum/SOUL.md

# Set model and temperature (~0.2) in:
# ~/.hermes/profiles/aurum/config.yaml
```

### 6. Connect via Telegram (recommended)

Use Telegram to log expenses and ask balances from your phone. Each Hermes profile runs its own bot — the `aurum` profile gets the `aurum` command (same as `hermes -p aurum`).

#### 6.1 Create a bot with BotFather

1. Open Telegram and go to [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Choose a **display name** (e.g. `Aurum`)
4. Choose a **username** ending in `bot` (e.g. `my_aurum_finance_bot`)
5. Copy the **API token** BotFather returns (format: `123456789:ABCdef...`)

Keep the token secret. If it leaks, revoke it in BotFather with `/revoke`.

Optional — improve the bot profile in BotFather:

| Command | Purpose |
|---------|---------|
| `/setdescription` | Short “what can this bot do?” text |
| `/setabouttext` | Text on the bot profile |
| `/setcommands` | Command menu (`/help`, `/new`, etc.) |

#### 6.2 Get your Telegram user ID

Hermes only accepts messages from allowed users. Your user ID is a number (not your `@username`).

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy the numeric ID (e.g. `123456789`)

#### 6.3 Wire the bot to the Aurum profile

**Interactive (recommended):**

```bash
aurum gateway setup
```

Select **Telegram**, paste the bot token, and enter your user ID when prompted.

**Manual** — edit `~/.hermes/profiles/aurum/.env`:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_ALLOWED_USERS=123456789
```

For multiple users, comma-separate IDs. Alternatively, use DM pairing: unknown users get a code; approve with `hermes pairing approve telegram <CODE>`.

#### 6.4 Start the gateway

```bash
aurum gateway start
```

For a background service (macOS launchd / Linux systemd):

```bash
aurum gateway install
aurum gateway start
aurum gateway status
```

Send a message to your bot on Telegram — e.g. “I spent R$ 52.30 at the grocery store using Inter.” Aurum uses the **financial-operator** and **financial-mentor** skills from this profile.

Docs: [Hermes Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging) · [Telegram setup](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)

### 7. Run

**CLI:**

```bash
aurum chat
```

**Telegram:** message your bot after step 6.

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
    ├── financial-operator/
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── ledger.py
    │       ├── rebuild_state.py
    │       └── reports.py
    └── financial-mentor/
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
SCRIPT="skills/financial-operator/scripts"

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
