<p align="center">
  <img src="avatar.png" alt="Aurum — agente de fluxo de caixa para Hermes" width="220" />
</p>

<h1 align="center">Aurum</h1>

<p align="center">
  <strong>Agente de fluxo de caixa para Hermes</strong><br/>
  Recebe o dia a dia em linguagem natural · lançamentos, contas mensais e crédito parcelado
</p>

<p align="center">
  <a href="ROADMAP.md"><img src="https://img.shields.io/badge/status-v2.2-blue" alt="Status" /></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Hermes-Agent-blue" alt="Hermes" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" /></a>
</p>

---

O **Aurum** é um agente conversacional para o [Hermes Agent](https://github.com/NousResearch/hermes-agent). Você descreve situações rotineiras — no CLI ou no Telegram — e ele atualiza o fluxo de caixa.

Esta é a **v2**. O núcleo: lançamentos do dia, **contas de débito com saldo inicial**, **cartão com fechamento/fatura**, contas mensais e parcelas.

## Exemplo

**Você**

```
Gastei 30 reais em mercado no débito com o banco Inter.
```

**Aurum**

```
✓ Despesa de R$ 30,00 em Alimentação (Mercado) no Banco Inter (débito).
```

Outros exemplos:

| Você diz | Aurum faz |
|----------|-----------|
| `Apaga o último lançamento` | Remove a última linha |
| `Remove o gasto de 30 reais no mercado` | Remove o lançamento que combina |
| `Corrige o valor para 35` | Edita o valor do último lançamento |
| `Na verdade foi 35, não 30` | Localiza o de R$ 30 e troca para R$ 35 |
| `Conta de luz 150 por mês dia 10` | Agenda conta mensal (vence dia 10) |
| `Compra de 1000 no crédito Inter em 5x` | 5 cobranças de R$ 200 no cartão |
| `Nova conta débito Itaú com saldo de 1500` | Cadastra débito e inicia o saldo da carteira |
| `Novo cartão Inter, fecha dia 19, fatura dia 25` | Cadastra cartão com ciclo de fatura |
| `Quanto tenho?` | Saldos de débito + ciclo dos cartões |
| `O que vence esse mês?` | Lista débitos e parcelas em aberto |

Categoria e data são opcionais. Sem categoria → **Outros**. Sem data → **hoje**.

## O que esta versão faz

- Interpreta mensagens do dia a dia (`gastei`, `paguei`, `recebi`, `apaga`, `corrige`)
- Insere despesa ou receita no fluxo de caixa do dia
- Categoriza (`mercado` → Alimentação, `luz` → Moradia, …)
- Identifica conta e forma de pagamento (`Inter` + `débito` / `crédito`)
- Remove ou edita um lançamento existente (por mensagem ou por `id`)
- Contas mensais recorrentes (água, luz, telefone) com vencimento
- Compras no crédito em Nx, projetadas mês a mês
- Agenda de cobranças futuras (`upcoming`)
- Conta de débito com **saldo inicial** (saldo da carteira derivado)
- Cartão de crédito com **dia de fechamento** e **dia de pagamento da fatura**

Ainda **não** faz: mentoria financeira, patrimônio consolidado além das contas, Open Finance.

O ledger da v1 (`ledger.jsonl` append-only) **não é migrado**. A v2 usa `data/cashflow.jsonl` com id por linha.

## Arquitetura

Este repositório é uma [distribuição de perfil Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/profile-distributions). `hermes profile install` copia para `~/.hermes/profiles/aurum/` e cria o comando `aurum`.

```
hermes-aurum/
├── SOUL.md                 # persona e regras
├── config.yaml             # modelo, Telegram
├── distribution.yaml
├── references/             # categorias, contas e palavras-chave (seed)
└── skills/cashflow/
    ├── SKILL.md
    └── scripts/aurum-run   # apply | add | remove | edit | list
```

Dados do usuário (não versionados):

| Arquivo | Função |
|---------|--------|
| `data/cashflow.jsonl` | Lançamentos do dia |
| `data/schedule.jsonl` | Contas mensais e parcelamentos |
| `data/accounts.json` | Contas em uso (cópia do seed na 1ª execução) |
| `data/categories.json` | Categorias em uso |

Cada linha do fluxo de caixa:

```json
{
  "id": "cf_a1b2c3d4e5",
  "type": "expense",
  "date": "2026-08-14",
  "amount": 30.0,
  "category": "Alimentação",
  "account": "Banco Inter",
  "method": "debito",
  "description": "Mercado"
}
```

## Categorias padrão

Despesa: `Alimentação` · `Transporte` · `Moradia` · `Saúde` · `Lazer` · `Educação` · `Vestuário` · `Outros`

Receita: `Salário` · `Freelance` · `Investimentos` · `Outros`

Contas seed (débito, saldo inicial 0): Banco Inter, Nubank, C6 Bank, Carteira. Ao cadastrar uma nova, débito pede saldo inicial; cartão pede fechamento e pagamento da fatura.

## CLI (`aurum-run`)

```bash
AURUM="$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run"

"$AURUM" apply "Gastei 30 reais em mercado no débito com o banco Inter"
"$AURUM" apply "Conta de luz 150 por mês dia 10 no Inter"
"$AURUM" apply "Compra de 1000 no cartão de crédito banco Inter em 5x"
"$AURUM" apply "Nova conta débito Itaú com saldo de 1500"
"$AURUM" apply "Novo cartão Inter, fecha dia 19, fatura dia 25"
"$AURUM" accounts
"$AURUM" today
"$AURUM" list --month 2026-08
"$AURUM" remove cf_a1b2c3d4e5
"$AURUM" edit cf_a1b2c3d4e5 '{"amount":35}'
```

A saída é sempre JSON. O agente só confirma quando `"status":"ok"`.

## Instalação

### ① Hermes

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes doctor
```

### ② Credenciais

- [Google AI Studio](https://aistudio.google.com/apikey) → `GOOGLE_API_KEY`
- Telegram (opcional): token do [@BotFather](https://t.me/BotFather) e ID em [@userinfobot](https://t.me/userinfobot)

### ③ Instalar o perfil

```bash
hermes profile install github.com/laerciocrestani/hermes-aurum --alias -y
hermes profile info aurum
aurum setup
```

Desenvolvimento local:

```bash
git clone https://github.com/laerciocrestani/hermes-aurum.git
cd hermes-aurum
hermes profile install "$(pwd)" --alias -y
```

### ④ Conversar

```bash
aurum chat
aurum gateway start    # Telegram
```

## Desenvolvimento

```bash
python3 -m unittest discover -s tests -v
```

Workflow com symlink:

```bash
REPO="$(pwd)"
PROFILE="$HOME/.hermes/profiles/aurum"
mkdir -p "$PROFILE/skills"
ln -sf "$REPO/skills/cashflow" "$PROFILE/skills/cashflow"
ln -sf "$REPO/references" "$PROFILE/references"
cp "$REPO/SOUL.md" "$PROFILE/SOUL.md"
cp "$REPO/config.yaml" "$PROFILE/config.yaml"
```

## Licença

MIT — veja [LICENSE](LICENSE).

O Aurum não é consultoria financeira regulamentada.
