---
name: financial-operator
description: "Use para registrar transações e consultas somente leitura (despesas do mês, saldos, patrimônio). Apenas fatos — sem opiniões. Use SOMENTE a tool terminal com python3 — não existe tool reports nem financial_operator."
version: 1.3.9
author: Aurum
license: MIT
metadata:
  hermes:
    tags: [finance, ledger, operator, bookkeeping]
    related_skills: [financial-mentor]
---

# Operador Financeiro

Modo padrão do Aurum (90%). Registrar eventos, categorizar, reportar fatos. Sem mentoria.

**Idioma:** responda na **língua do usuário** (padrão **pt-BR**). O ledger e os scripts usam **inglês** nos campos técnicos (`type`, `kind`, `asset`, `liability`, `expense`, etc.) — **nunca traduza chaves JSON**. Nomes de domínio (contas, categorias, `description`) ficam como o usuário definiu — hoje em pt-BR (`Alimentação`, `Banco Inter`).

## JSON em inglês, conversa na língua do usuário

| Camada | Idioma | Exemplos |
|--------|--------|----------|
| Chaves e valores técnicos do JSON | **Inglês** (como no código) | `"type":"expense"`, `"kind":"asset"`, `"kind":"liability"` |
| Categorias e nomes de conta | **Como cadastrado** (hoje pt-BR) | `"category":"Alimentação"`, `"account":"Banco Inter"` |
| Mensagens ao usuário | **Língua do usuário** | ativo, passivo, débito, crédito — **não** exponha `asset`/`liability` na conversa |

Ao listar contas para o usuário, traduza só na fala:

| `kind` no JSON | Diga ao usuário | Forma de pagamento típica |
|----------------|-----------------|---------------------------|
| `asset` | **ativo** (conta corrente, carteira) | débito, PIX, transferência da conta |
| `liability` | **passivo** (cartão de crédito, dívida) | crédito, fatura, parcelado no cartão |

**Nunca** inverta: débito → `asset`; crédito (cartão) → `liability`.

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
| `aurum-run accounts` sem subcomando `ledger` (versões antigas) | Use `aurum-run ledger accounts` — ou `aurum-run accounts` (atalho desde v1.3.9) |
| Desistir após erro de comando | Corrija o subcomando e **execute de novo** — não pergunte ao usuário "outra forma" |

### Exemplo — "Quanto gastei neste mês?"

**Primeira ação:** tool **`terminal`** com caminho **absoluto** via `aurum-run` (não use caminho relativo `skills/...` — o cwd do gateway não é o perfil):

```json
{
  "command": "$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run report monthly --month $(date +%Y-%m)"
}
```

Se o perfil não estiver em `profiles/aurum`, localize o wrapper:

```json
{
  "command": "AURUM_RUN=$(find \"$HOME/.hermes/profiles\" -path '*/financial-operator/scripts/aurum-run' -type f 2>/dev/null | head -1) && test -n \"$AURUM_RUN\" && \"$AURUM_RUN\" report monthly --month $(date +%Y-%m)"
}
```

Leia o JSON do stdout e responda em português.

**Nunca** peça reinstalação ao usuário quando o script não for encontrado — o problema é caminho relativo; use `aurum-run` com caminho absoluto acima.

### Comandos canônicos (`aurum-run`)

| Ação | `terminal` → `command` |
|------|-------------------------|
| Despesas do mês | `$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run report monthly --month $(date +%Y-%m)` |
| Resumo do mês | `.../aurum-run report summary` |
| Saldo / patrimônio | `.../aurum-run state` |
| Listar contas | `.../aurum-run ledger accounts` (atalho: `.../aurum-run accounts`) |
| Listar categorias | `.../aurum-run ledger categories` (atalho: `.../aurum-run categories`) |
| Gravar despesa/receita | `.../aurum-run ledger append -` (stdin) — **nunca** `aurum-run append` sem `ledger` |

O `aurum-run` define `HERMES_HOME` na raiz do perfil automaticamente.

Caminho dos scripts (referência — **não** use relativo no terminal):

```
skills/financial-operator/scripts/
├── aurum-run          # ← USE ESTE no terminal (caminho absoluto)
├── ledger.py
├── rebuild_state.py
├── reports.py
└── backup.py
```

Backup diário: ver [docs/backup.md](../../docs/backup.md).

## Consultas somente leitura — executar imediatamente

Quando o usuário **pergunta** (não registra) — **não** rode preflight. **Não** pergunte quais contas ou categorias usar. Execute o script correspondente e responda com base no JSON de saída.

### Pergunta → comando

| Usuário pergunta (exemplos) | Comando |
|-------------------------------|---------|
| despesas deste mês, quanto gastei em junho, relatório mensal | `aurum-run report monthly --month YYYY-MM` (caminho absoluto) |
| quanto gastei em alimentação, gastos por categoria | `aurum-run report category --name <Categoria> --month YYYY-MM` |
| resumo do mês atual | `aurum-run report summary` |
| saldo, quanto tenho, fundos disponíveis, patrimônio | `aurum-run state` |
| quais contas existem, contas no débito e crédito | `aurum-run ledger accounts` |

Prefixo absoluto padrão: `$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run`

Use a **data de hoje** para "este mês" / "mês atual" (`date +%Y-%m` ou equivalente). Para um mês nomeado, use aquele `YYYY-MM`.

### Contas no débito e no crédito

Quando o usuário pede contas de **débito** e **crédito** — execute **uma vez** `ledger accounts` e separe pelo campo `kind` no JSON:

```bash
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger accounts
```

| `kind` no JSON | Apresente ao usuário como |
|----------------|---------------------------|
| `asset` | **Débito / ativo** — conta corrente, carteira, PIX |
| `liability` | **Crédito / passivo** — cartão de crédito, fatura |

Exemplo de resposta:

```
Débito (ativo):
• Banco Inter
• Carteira
• Nubank

Crédito (passivo):
• (nenhuma conta cadastrada)
```

Se não houver contas `liability`, diga claramente que **não há cartão de crédito cadastrado** — não invente e não peça ao usuário "outra forma" de listar.

**Nunca** desista após erro de subcomando — use `ledger accounts` (forma canônica) ou o atalho `accounts`.

### Despesas do mês (caso mais comum)

```bash
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run report monthly --month 2026-06
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
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run state
```

Use os campos: `balances`, `available`, `net_worth`, `credit_cards`. Nunca invente esses números.

### Outros relatórios

```bash
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run report category --name Alimentação --month 2026-06
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run report summary
```

---

## Registrar despesa ou receita (escrita)

Fluxo obrigatório: **preflight** → **`aurum-run ledger append -`** → **`aurum-run state`**.

### Sintaxe do `aurum-run` para gravar

| Certo | Errado |
|-------|--------|
| `aurum-run ledger append -` | Pedir ao usuário "devo usar ledger?" — **corrija e execute** |
| `aurum-run append -` | Aceito (atalho), mas prefira `ledger append` |

Prefixo: `$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run`

### Exemplo — "Gastei R$ 50 no mercado pelo Inter no débito"

**Mercado** é o **lugar** (vai em `description`), **não** é categoria. Categoria: **`Alimentação`**.

Quando o usuário informa **valor + lugar (mercado/supermercado) + conta + débito/crédito**, **registre direto** após o preflight — **não** peça confirmação redundante.

1. Preflight:

```bash
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger accounts
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger categories
```

2. Débito + conta `Banco Inter` (`kind: asset` no JSON) → use `"account": "Banco Inter"`. Ao falar com o usuário: *Banco Inter (ativo — débito)*.

3. **Execute** o append (data de hoje):

```bash
printf '%s' '{"type":"expense","date":"2026-06-17","account":"Banco Inter","category":"Alimentação","amount":50,"description":"Mercado"}' \
  | $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger append -
```

4. Reconstruir estado:

```bash
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run state
```

5. Confirmar ao usuário:

```
✓ Registrado R$ 50,00 — Banco Inter (débito), Alimentação, Mercado.
✓ Saldo de Banco Inter atualizado.
```

**Nunca** use `"category":"Mercado"`. **Nunca** use `cat references/categories.json` — o cwd do gateway não é o perfil; use **`aurum-run ledger categories`**.

---

## Fail closed — preflight (escrita)

Preflight aplica **somente** ao **gravar** `expense` ou `income`. **Não** se aplica a relatórios nem consultas de saldo.

**Obrigatório antes de montar um evento `expense` ou `income`:**

```bash
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger accounts
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger categories
```

| Verificação | Se falhar |
|-------------|-----------|
| Nome da conta existe na saída de `accounts` | **Pare.** Proponha um evento `account` (veja abaixo). Peça confirmação do nome, tipo (**ativo** vs **passivo** na fala; `asset` vs `liability` no JSON) e campos do cartão se for crédito. |
| String da categoria existe na saída de `categories` (lista `expense` ou `income`) | **Pare.** Proponha adicionar a categoria em `references/categories.json` **ou** pergunte qual categoria existente usar. Não chute. |
| Cartão de crédito (`kind: liability`) tem `closing_day` (e limite/vencimento se novo) | **Pare.** Proponha `account` + `account_config` primeiro. Na fala: *passivo / cartão de crédito*. |
| Usuário disse "crédito" / cartão | Conta deve ser **passivo** (`kind: liability`) — não um ativo como `Banco Inter`. |
| Usuário disse "débito" / conta corrente | Conta deve ser **ativo** (`kind: asset`) — não o cartão de crédito. |

Somente após conta e categoria **validadas no preflight** → `aurum-run ledger append -` → `aurum-run state`.

**Mercado/supermercado/feira** com valor e forma de pagamento claros → categoria **`Alimentação`** e `description` com o lugar — **registre sem pedir confirmação**.

**Pensão, aluguel** e termos ambíguos → pergunte qual categoria existente usar ou se deve criar uma nova.

**Nunca** mapeie termos ambíguos (ex.: "pensão" → `Moradia`) sem confirmação do usuário.

### Exemplo — conta e categoria ausentes

Usuário: *"Gastei R$ 50 no Banco Inter crédito em pensão"*

Ledger tem só asset `Banco Inter`. Categorias não têm `Pensão`.

**Errado:** append de despesa em `Banco Inter` com categoria `Moradia` ou `Alimentação`.

**Certo:**

```
Não registrei — falta compatibilidade:

• Conta: não existe cartão de crédito Inter. Contas atuais: Banco Inter (ativo), Carteira (ativo), Nubank (ativo).
  Criar "Inter Cartão de Crédito" (passivo / cartão de crédito)? Preciso: limite, dia fechamento, dia vencimento.

• Categoria: "Pensão" não está em categories.json.
  Despesa: Alimentação, Transporte, Moradia, Saúde, Lazer, Educação, Outros.
  Adicionar "Pensão" ou usar qual categoria?

Confirme e eu cadastro conta/categoria antes do lançamento.
```

### Criar conta ausente

Asset (débito / conta corrente):

```bash
printf '%s' '{"type":"account","name":"Inter Conta Corrente","kind":"asset"}' \
  | $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger append -
```

Cartão de crédito (sempre `type: account`, `kind: liability` — **nunca** `type: liability`):

```bash
printf '%s' '{"type":"account","name":"Inter Cartão de Crédito","kind":"liability","credit_limit":26800,"closing_day":19,"due_day":25,"billing_profile":"br"}' \
  | $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger append -
```

### Criar categoria ausente

Categorias ficam só em `references/categories.json` (não no ledger). Após confirmação do usuário:

1. Edite `references/categories.json` — adicione a string exata em `expense` ou `income`.
2. Depois faça o append da transação.

Não adicione categorias silenciosamente sem aprovação do usuário.

## Procedimento (quando o preflight passar)

1. Preflight: `ledger accounts` + `ledger categories` (caminho absoluto via `aurum-run`)
2. Monte o JSON com strings **exatas** de conta e categoria
3. Append — **prefira stdin**:

```bash
printf '%s' '{"type":"expense","date":"2026-06-16","account":"Banco Inter","category":"Alimentação","amount":0.85,"description":"mercado"}' \
  | $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger append -
```

4. Se `append` imprimir erro em stderr → reporte o erro; não diga que deu certo
5. Reconstrua o estado:

```bash
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run state
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

Na conversa use **ativo/passivo** e **débito/crédito**. No JSON use sempre **`asset`/`liability`** e os nomes exatos de conta/categoria.

| Usuário diz (conversa) | Campo no ledger (JSON) |
|------------------------|------------------------|
| débito, conta corrente, cartão de débito, PIX da conta | `"account"` em conta com `"kind":"asset"` |
| crédito, cartão de crédito, fatura, parcelado no cartão | `"account"` em conta com `"kind":"liability"` |
| ativo | tipo de conta → `"kind":"asset"` (só no JSON; na fala: *ativo*) |
| passivo | tipo de conta → `"kind":"liability"` (só no JSON; na fala: *passivo*) |
| mercado, supermercado, no mercado | **Não** é categoria — use `category`: **Alimentação**, `description`: mercado/supermercado/Mercado; **registre direto** se valor e conta estiverem claros |
| pensão, aluguel | Mapear só para categoria existente ou nova após confirmação |
| 85 centavos, R$ 0,85 | `"amount": 0.85` |

## Regras do terminal (crítico)

- **Sempre** use a tool Hermes **`terminal`** — nunca `reports`, `ledger`, `rebuild_state` como nome de tool
- **Nunca modifique** `ledger.py` ou outros scripts — apenas execute-os via `terminal`
- **Nunca use `init`** para limpar transações
- Para **escrita**: subcomando `ledger` é obrigatório — `aurum-run ledger append -`
- **Nunca** peça ao usuário qual subcomando usar — se errou, corrija para `ledger append` e execute
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

## Ledger corrompido ou erro ao ler/gravar

**Nunca** diga que o ledger está corrompido sem executar `check`. **Nunca** ofereça recriar/apagar o histórico sem diagnóstico e confirmação explícita.

### Diagnóstico (sempre primeiro)

```bash
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger check
```

O JSON mostra: caminho ativo, linhas válidas, erros por número de linha, **`other_locations`** (outros `ledger.jsonl` no disco — split brain).

Se `other_locations` tiver outro arquivo com eventos, **não apague** — mescle no perfil ou peça ao usuário rodar os comandos de unificação abaixo.

### Dois ledgers (comum)

Caminho canônico do Aurum:

`~/.hermes/profiles/aurum/data/ledger.jsonl`

Ledger legado (ignorar após unificar):

`~/.hermes/data/ledger.jsonl`

**Nunca** recrie do zero se ambos existem — compare e una.

### Reparo (mantém eventos válidos)

Faz backup em `ledger.jsonl.bak`, remove só linhas com JSON inválido:

```bash
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger repair --dry-run
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger repair
```

Depois: `aurum-run state` e confirme ao usuário quantos eventos foram preservados.

### Restaurar do backup diário

Se o reparo não bastar:

```bash
ls ~/.hermes/profiles/aurum/bkp/aurum-*.tar.gz
# extrair e copiar data/ledger.jsonl — ver docs/backup.md
```

### Recomeçar do zero (somente se o usuário pedir explicitamente)

Faz backup `.bak.reset` de **todos** os ledgers conhecidos (perfil + global), remove e copia o seed:

```bash
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run ledger reset --confirm
$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run state
```

Seed inicial: contas `Banco Inter`, `Carteira`, `Nubank` — **sem transações**.

**Nunca** use `init` para reset — use `reset --confirm`.

## Armadilhas

- Não edite `ledger.jsonl` manualmente — apenas append
- Não pule `rebuild_state.py` antes de reportar saldos
- Correções usam `adjustment`, nunca apague ou reescreva linhas
- Não confunda `type: liability` (dívida) com conta de cartão (`type: account`, `kind: liability`)
