# Roadmap — Aurum

A v2 começa do zero: um agente de fluxo de caixa que entende o dia a dia.

## v2.1 — Entregue

- Contas mensais recorrentes (água, luz, telefone) com dia de vencimento
- Compras no crédito em Nx projetadas na agenda
- Inclusão, edição e remoção das cobranças via mensagem
- `upcoming`: débitos e parcelas em aberto nos próximos meses

## v2.0 — Entregue

- Mensagens em pt-BR → inserir, remover ou editar lançamento
- Categorização por palavras-chave (`mercado` → Alimentação)
- Conta e método de pagamento (débito, crédito, PIX, dinheiro)
- Fluxo de caixa mutável com `id` (`data/cashflow.jsonl`)
- Skill Hermes `cashflow` + `aurum-run apply`
- Distribuição de perfil (`hermes profile install`)

## Próximo (não implementado)

| Item | Notas |
|------|--------|
| Relatório mensal por categoria | Leitura agregada além de `list` |
| Ciclo de fatura do cartão | Fechamento/vencimento além do Nx simples |
| Mentoria sob demanda | Só depois que o fluxo de caixa estiver estável |
| Aliases extras de conta na conversa | “itaú”, “caju”, etc. sem editar JSON |
| Importação OFX/CSV | Fora do núcleo conversacional |
| Migração do ledger v1 | Não há conversão automática de `ledger.jsonl` |

## Fora de escopo por enquanto

- Open Finance
- Cotações de ativos e execução de trades
- Web UI
- Multi-moeda

## Changelog

| Versão | Data | Notas |
|--------|------|--------|
| v2.1.0 | 2026-08-14 | Contas mensais, crédito em Nx e agenda de cobranças futuras |
| v2.0.0 | 2026-08-14 | Reescrita: fluxo de caixa com insert/remove/edit a partir de mensagens |
| v1.4.5 | 2026-06-17 | Última linha da geração event-sourced (ledger append-only) |
