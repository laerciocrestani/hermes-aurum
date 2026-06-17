# Roadmap — Aurum

Este documento separa explicitamente o que **existe hoje** do que está **planejado**.
Itens marcados como planejados **não estão implementados** — não confunda com o README.

## Legenda

| Símbolo | Significado |
|---------|-------------|
| Entregue | Disponível no MVP |
| Em progresso | Em desenvolvimento |
| Planejado | Contribuições bem-vindas via issue/PR |
| Ideia | Sem prioridade ainda |

---

## MVP v1.0 — Entregue

- Ledger pessoal append-only (`ledger.jsonl`)
- Skills Hermes: `financial-operator` + `financial-mentor`
- Scripts: `ledger.py`, `rebuild_state.py`, `reports.py`
- Eventos: account, account_config, expense, income, transfer, investment, liability, adjustment
- Cartões de crédito: contas liability com ciclo de faturamento (parcelamento BR + perfil internacional simple)
- Patrimônio derivado do histórico (saldos nunca persistidos)
- Validação de conta (`account`) e categoria (`categories.json`) no append
- Escritas atômicas com `flush()` + `os.fsync()`
- Auto-init do ledger na primeira escrita
- Separação operador (90%) / mentor (10%)

---

## v1.x — Melhorias incrementais (Planejado)

Melhorias que **não alteram** a arquitetura event-sourced:

| Item | Descrição | Prioridade |
|------|-----------|------------|
| Categorias customizadas | Adicionar categorias via evento ou config, não só `categories.json` fixo | Alta |
| Aliases de conta | Mapear "Inter" → "Banco Inter" na interpretação do agente | Média |
| Relatório anual | `reports.py yearly --year 2026` | Média |
| Exportação CSV | Exportar transações para planilha | Baixa |
| Testes automatizados | Suite pytest para ledger, rebuild, reports | Alta |
| Alertas de cartão | Lembretes de fechamento/vencimento a partir do estado `credit_cards` | Média |
| Variantes de SOUL | Tom conservador vs direto em `docs/SOUL.example.md` | Baixa |

---

## v2.0 — Integrações (Planejado)

Funcionalidades maiores — **exigem design separado**:

| Item | Descrição | Dependências | Status |
|------|-----------|--------------|--------|
| Open Finance | Importar transações de bancos brasileiros | API regulatória, consentimento do usuário | Planejado |
| Importação OFX/CSV | Parser de extrato bancário | Mapeamento conta/categoria | Planejado |
| Cotações de ativos | Preços ao vivo de BTC, ETF, ações | API externa (Yahoo, etc.) | Planejado |
| Metas financeiras | Evento `goal` + acompanhamento | Schema JSONL estendido | Ideia |
| Orçamento mensal | Limites por categoria + alertas | Reports + eventos | Ideia |

---

## v3.0 — Experiência (Ideia)

| Item | Descrição | Status |
|------|-----------|--------|
| Web UI | Dashboard de patrimônio e gastos | Ideia |
| Multi-moeda | USD, EUR além de BRL | Ideia |
| Gateway Telegram/Discord | Aurum via gateways de mensagem do Hermes | Planejado |
| Distribuição de perfil | Empacotar como `hermes profile install` | Ideia |

---

## Explicitamente fora do escopo

O Aurum visa finanças **pessoais**, não institucionais:

- Family office / gestão patrimonial institucional
- Modelagem DCF / LBO / M&A (skills de corporate finance do Hermes)
- Execução de trades ou integração com corretora
- Ordens automáticas de compra/venda

---

## Como contribuir com o roadmap

1. Abra uma **issue** descrevendo a funcionalidade e em qual fase se encaixa
2. Alinhe o design antes de PRs grandes (v2+)
3. PRs v1.x são bem-vindos se mantiverem a regra de ouro (event-sourced, append-only)

Releases versionadas: bump em `distribution.yaml`, changelog abaixo, tag Git `vX.Y.Z` — ver [docs/versioning.md](docs/versioning.md).

## Changelog

| Versão | Data | Notas |
|--------|------|-------|
| v1.3.1 | 2026-06-17 | Skill: tool `terminal` explícita (não `reports`); Flash primário para tool calling |
| v1.3.0 | 2026-06-17 | Documentação e skills em pt-BR; consultas de leitura sem preflight; skill operator v1.3 |
| v1.2.2 | 2026-06-16 | Telegram: `busy_input_mode: queue` (evita interrupt loop com clarify/ledger) |
| v1.2.1 | 2026-06-16 | Gemini Flash Lite primário + Flash fallback (menos 503 no Telegram) |
| v1.2.0 | 2026-06-16 | Fail-closed: validar conta/categoria antes de append; sugerir criação; proibir init/reset falso |
| v1.1.0 | 2026-06-16 | Categorias pt-BR; backup diário (`backup.py`); `ledger append -` (stdin); provider Gemini; skill operator reforçado |
| v1.0.0 | 2026-06-10 | MVP inicial |
