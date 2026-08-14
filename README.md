<p align="center">
  <img src="avatar.png" alt="Aurum — agente de fluxo de caixa para Hermes" width="220" />
</p>

<h1 align="center">Aurum</h1>

<p align="center">
  <strong>Agente de fluxo de caixa para Hermes</strong><br/>
  Recebe o dia a dia em linguagem natural · insere, remove e edita lançamentos
</p>

<p align="center">
  <a href="ROADMAP.md"><img src="https://img.shields.io/badge/status-v2.0-blue" alt="Status" /></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Hermes-Agent-blue" alt="Hermes" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" /></a>
</p>

---

O **Aurum** é um agente conversacional para o [Hermes Agent](https://github.com/NousResearch/hermes-agent). Você descreve situações rotineiras — no CLI ou no Telegram — e ele atualiza o fluxo de caixa.

Esta é a **v2**, reescrita do zero. O objetivo inicial é estreito: **inserir, remover ou editar um lançamento** e **categorizar** a partir da mensagem.

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

Categoria e data são opcionais. Sem categoria → **Outros**. Sem data → **hoje**.

## O que esta versão faz

- Interpreta mensagens do dia a dia (`gastei`, `paguei`, `recebi`, `apaga`, `corrige`)
- Insere despesa ou receita no fluxo de caixa do dia
- Categoriza (`mercado` → Alimentação, `uber` → Transporte, …)
- Identifica conta e forma de pagamento (`Inter` + `débito`)
- Remove ou edita um lançamento existente (por mensagem ou por `id`)

Ainda **não** faz: mentoria financeira, cartão com fatura/parcelas, patrimônio derivado, Open Finance.

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
| `data/cashflow.jsonl` | Lançamentos |
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

Contas seed: Banco Inter, Nubank, C6 Bank, Carteira.

## CLI (`aurum-run`)

```bash
AURUM="$HOME/.hermes/profiles/aurum/skills/cashflow/scripts/aurum-run"

"$AURUM" apply "Gastei 30 reais em mercado no débito com o banco Inter"
"$AURUM" apply "Apaga o último lançamento"
"$AURUM" apply "Corrige o valor para 35"
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
