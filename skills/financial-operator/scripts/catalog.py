"""Catálogo de intenções do Aurum — fonte única para hint, help e do."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

CATALOG_VERSION = "1.4.2"

AURUM_RUN = "$HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run"

LEGACY_COMMANDS = [
    "report",
    "ledger",
    "state",
    "backup",
    "append",
    "accounts",
    "categories",
    "check",
    "repair",
    "reset",
]


@dataclass(frozen=True)
class Intent:
    name: str
    kind: str
    description_pt: str
    triggers_pt: tuple[str, ...]
    args_schema: dict[str, Any] = field(default_factory=dict)


INTENTS: tuple[Intent, ...] = (
    Intent(
        name="list-accounts",
        kind="read",
        description_pt="Lista contas de débito e crédito",
        triggers_pt=(
            "contas",
            "conta",
            "débito",
            "debito",
            "crédito",
            "credito",
            "listar contas",
            "quais contas",
            "ativo",
            "passivo",
            "banco",
        ),
    ),
    Intent(
        name="list-categories",
        kind="read",
        description_pt="Lista categorias de despesa e receita",
        triggers_pt=("categorias", "categoria", "listar categorias"),
    ),
    Intent(
        name="monthly-report",
        kind="read",
        description_pt="Relatório de despesas e receitas do mês",
        triggers_pt=(
            "despesas do mês",
            "despesas deste mês",
            "quanto gastei",
            "gastos do mês",
            "relatório mensal",
            "relatorio mensal",
            "este mês",
        ),
        args_schema={"month": {"type": "string", "format": "YYYY-MM", "required": False}},
    ),
    Intent(
        name="summary",
        kind="read",
        description_pt="Resumo financeiro do mês atual",
        triggers_pt=("resumo", "resumo do mês", "resumo mensal"),
    ),
    Intent(
        name="balances",
        kind="read",
        description_pt="Saldos, patrimônio líquido e fundos disponíveis",
        triggers_pt=(
            "saldo",
            "saldos",
            "quanto tenho",
            "patrimônio",
            "patrimonio",
            "fundos disponíveis",
            "net worth",
        ),
    ),
    Intent(
        name="category-report",
        kind="read",
        description_pt="Gastos em uma categoria",
        triggers_pt=("gastos em", "quanto gastei em", "categoria"),
        args_schema={
            "name": {"type": "string", "required": True},
            "month": {"type": "string", "format": "YYYY-MM", "required": False},
        },
    ),
    Intent(
        name="ledger-check",
        kind="read",
        description_pt="Diagnóstico do ledger (corrupção, split brain)",
        triggers_pt=("ledger corrompido", "erro no ledger", "diagnóstico", "check ledger"),
    ),
    Intent(
        name="preflight",
        kind="read",
        description_pt="Contas e categorias antes de registrar transação",
        triggers_pt=("preflight", "antes de registrar", "validar conta"),
    ),
    Intent(
        name="record-expense",
        kind="write",
        description_pt="Registrar uma despesa",
        triggers_pt=(
            "gastei",
            "despesa",
            "registrar despesa",
            "paguei",
            "comprei",
            "mercado",
            "gasto",
            "roupas",
            "vestuário",
            "vestuario",
        ),
        args_schema={
            "amount": {"type": "number", "required": True},
            "account": {"type": "string", "required": True},
            "category": {"type": "string", "required": True},
            "description": {"type": "string", "required": False},
            "date": {"type": "string", "format": "YYYY-MM-DD", "required": False},
            "installments": {"type": "integer", "required": False},
        },
    ),
    Intent(
        name="record-transfer",
        kind="write",
        description_pt="Transferir valor entre contas (saque, PIX entre contas próprias)",
        triggers_pt=(
            "transferi",
            "transferência",
            "transferencia",
            "transfiro",
            "saque",
            "saquei",
            "sacar",
            "enviei para",
            "mandei para",
            "mudei para",
            "da conta",
            "para a carteira",
            "para carteira",
        ),
        args_schema={
            "from": {"type": "string", "required": True},
            "to": {"type": "string", "required": True},
            "amount": {"type": "number", "required": True},
            "description": {"type": "string", "required": False},
            "date": {"type": "string", "format": "YYYY-MM-DD", "required": False},
        },
    ),
    Intent(
        name="record-mixed-expense",
        kind="write",
        description_pt="Despesa com pagamento misto (ex.: parte carteira + parte cartão parcelado)",
        triggers_pt=(
            "pagamento misto",
            "parte com",
            "resto no cartão",
            "resto no credito",
            "resto no crédito",
            "uma parte",
            "o restante",
            "parcelado",
            "em 2x",
            "em 3x",
            "em 9x",
            "metade",
        ),
        args_schema={
            "category": {"type": "string", "required": True},
            "description": {"type": "string", "required": False},
            "date": {"type": "string", "format": "YYYY-MM-DD", "required": False},
            "parts": {
                "type": "array",
                "required": True,
                "items": {
                    "amount": "number",
                    "account": "string",
                    "installments": "integer?",
                },
            },
        },
    ),
    Intent(
        name="add-category",
        kind="write",
        description_pt="Adicionar categoria de despesa ou receita",
        triggers_pt=(
            "nova categoria",
            "adicionar categoria",
            "criar categoria",
            "cadastrar categoria",
        ),
        args_schema={
            "name": {"type": "string", "required": True},
            "kind": {"type": "string", "enum": ["expense", "income"], "required": False},
        },
    ),
    Intent(
        name="add-account",
        kind="write",
        description_pt="Cadastrar conta (corrente ou cartão de crédito)",
        triggers_pt=(
            "nova conta",
            "adicionar conta",
            "criar conta",
            "cadastrar conta",
            "cadastrar cartão",
            "cadastrar cartao",
            "novo cartão",
        ),
        args_schema={
            "name": {"type": "string", "required": True},
            "kind": {"type": "string", "enum": ["asset", "liability"], "required": True},
            "credit_limit": {"type": "number", "required": False},
            "closing_day": {"type": "integer", "required": False},
            "due_day": {"type": "integer", "required": False},
            "billing_profile": {"type": "string", "required": False},
        },
    ),
    Intent(
        name="update-account",
        kind="write",
        description_pt="Atualizar configuração de cartão de crédito (limite, fechamento, vencimento)",
        triggers_pt=(
            "atualizar cartão",
            "atualizar cartao",
            "limite do cartão",
            "dia de fechamento",
            "dia de vencimento",
            "account config",
        ),
        args_schema={
            "account": {"type": "string", "required": True},
            "credit_limit": {"type": "number", "required": False},
            "closing_day": {"type": "integer", "required": False},
            "due_day": {"type": "integer", "required": False},
            "billing_profile": {"type": "string", "required": False},
        },
    ),
    Intent(
        name="record-income",
        kind="write",
        description_pt="Registrar uma receita",
        triggers_pt=("recebi", "receita", "registrar receita", "entrada", "salário", "salario"),
        args_schema={
            "amount": {"type": "number", "required": True},
            "account": {"type": "string", "required": True},
            "category": {"type": "string", "required": True},
            "description": {"type": "string", "required": False},
            "date": {"type": "string", "format": "YYYY-MM-DD", "required": False},
        },
    ),
)

_INTENT_BY_NAME = {intent.name: intent for intent in INTENTS}


def intent_command(name: str) -> str:
    return f"{AURUM_RUN} do {name}"


def shell_command(*parts: str) -> str:
    """Comando completo para a tool Hermes terminal (única tool válida)."""
    return " ".join([AURUM_RUN, *parts])


def get_intent(name: str) -> Intent | None:
    return _INTENT_BY_NAME.get(name)


def normalize_text(text: str) -> str:
    lowered = text.lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents)


def _score_intent(query: str, intent: Intent) -> float:
    score = 0.0
    for trigger in intent.triggers_pt:
        trigger_norm = normalize_text(trigger)
        if trigger_norm in query:
            score += len(trigger_norm.split()) + 1
    for token in query.split():
        if len(token) < 3:
            continue
        for trigger in intent.triggers_pt:
            trigger_norm = normalize_text(trigger)
            if token in trigger_norm.split() or any(token in part for part in trigger_norm.split()):
                score += 0.5
    return score


def serialize_intent(intent: Intent) -> dict[str, Any]:
    return {
        "name": intent.name,
        "kind": intent.kind,
        "command": intent_command(intent.name),
        "description_pt": intent.description_pt,
        "triggers_pt": list(intent.triggers_pt),
        "args": intent.args_schema,
    }


def help_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": CATALOG_VERSION,
        "intents": [serialize_intent(intent) for intent in INTENTS],
        "legacy_commands": LEGACY_COMMANDS,
        "helper": {
            "tool": "terminal",
            "hint": f'{AURUM_RUN} hint "<palavras do usuário>"',
            "help_json": f"{AURUM_RUN} help --json",
            "menu": f"{AURUM_RUN} menu",
        },
        "forbidden_tools": [
            "aurum_run",
            "aurum-run",
            "aurum run",
            "financial_operator",
            "financial-operator",
            "reports",
            "ledger",
            "do",
            "hint",
            "help",
        ],
    }


def hint_payload(query: str) -> dict[str, Any]:
    normalized = normalize_text(query)
    if not normalized:
        return {
            "status": "error",
            "message": "Consulta vazia",
            "suggestion": f"{AURUM_RUN} help --json",
        }

    ranked: list[tuple[float, Intent]] = []
    for intent in INTENTS:
        score = _score_intent(normalized, intent)
        if score > 0:
            ranked.append((score, intent))

    ranked.sort(key=lambda item: item[0], reverse=True)

    if not ranked:
        alternatives = [serialize_intent(intent) for intent in INTENTS[:5]]
        return {
            "status": "ok",
            "query": query,
            "match": None,
            "alternatives": [
                {"intent": item["name"], "command": item["command"], "description_pt": item["description_pt"]}
                for item in alternatives
            ],
            "suggestion": f"{AURUM_RUN} help --json",
        }

    best_score, best = ranked[0]
    second_score = ranked[1][0] if len(ranked) > 1 else 0.0
    confidence = "high" if best_score >= 2 and best_score >= second_score * 1.5 else "low"

    match = {
        "intent": best.name,
        "confidence": confidence,
        "tool": "terminal",
        "command": intent_command(best.name),
        "description_pt": best.description_pt,
    }

    alternatives = [
        {
            "intent": intent.name,
            "tool": "terminal",
            "command": intent_command(intent.name),
            "description_pt": intent.description_pt,
            "score": score,
        }
        for score, intent in ranked[1:4]
    ]

    payload: dict[str, Any] = {
        "status": "ok",
        "query": query,
        "match": match if confidence == "high" else None,
        "alternatives": alternatives,
    }
    if confidence != "high":
        payload["suggestion"] = f"{AURUM_RUN} help --json"
        if confidence == "low" and best_score > 0:
            payload["best_guess"] = match
    return payload


def menu_text() -> str:
    return """Aurum — comandos básicos (use a tool terminal com estes comandos shell)

Listar contas (débito e crédito):
  $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run do list-accounts

Despesas do mês:
  $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run do monthly-report

Saldo e patrimônio:
  $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run do balances

Registrar despesa (ex.: mercado R$ 50 Inter débito):
  $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run do record-expense '{"amount":50,"account":"Banco Inter","category":"Alimentação","description":"Mercado"}'

Transferência / saque:
  $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run do record-transfer '{"from":"Banco Inter","to":"Carteira","amount":50}'

Dúvida? $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/aurum-run hint "sua pergunta"

NÃO existe tool aurum_run — só terminal com o caminho acima."""


def help_text() -> str:
    lines = [
        f"Aurum — comandos por intenção (v{CATALOG_VERSION})",
        "",
        "Use a tool terminal (NÃO existe tool aurum_run):",
        f"  {AURUM_RUN} hint \"<pergunta>\"",
        f"  {AURUM_RUN} help --json",
        f"  {AURUM_RUN} menu",
        "",
        "Leitura:",
    ]
    for intent in INTENTS:
        if intent.kind == "read":
            lines.append(f"  {intent_command(intent.name)}  — {intent.description_pt}")
    lines.append("")
    lines.append("Escrita:")
    for intent in INTENTS:
        if intent.kind == "write":
            lines.append(f"  {intent_command(intent.name)} '<json>'  — {intent.description_pt}")
    lines.append("")
    lines.append("Legado: report, ledger, state, backup")
    return "\n".join(lines)
