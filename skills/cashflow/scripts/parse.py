"""Interpreta mensagens do dia a dia em intenções de fluxo de caixa."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from catalog import Catalog

AMOUNT_WITH_UNIT_RE = re.compile(
    r"(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais|reias|real)\b",
    re.IGNORECASE,
)
AMOUNT_RS_RE = re.compile(r"r\$\s*(\d+(?:[.,]\d{1,2})?)", re.IGNORECASE)
AMOUNT_AFTER_VERB_RE = re.compile(
    r"\b(?:gastei|paguei|comprei|recebi|ganhei|entrou)\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\b",
    re.IGNORECASE,
)
OLD_AMOUNT_RE = re.compile(
    r"\b(?:nao|n[aã]o)\s+(?:foi\s+|eram?\s+)?(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)
NEW_AMOUNT_RE = re.compile(
    r"\b(?:foi|para|pra)\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
BR_DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")

ADD_EXPENSE_RE = re.compile(r"\b(gastei|paguei|comprei|gasto|despesa)\b", re.IGNORECASE)
ADD_INCOME_RE = re.compile(r"\b(recebi|ganhei|entrou|salario|salário)\b", re.IGNORECASE)
REMOVE_RE = re.compile(
    r"\b(apaga|apague|remove|remover|cancela|cancelar|desfaz|desfazer|exclui|excluir|deleta|deletar)\b",
    re.IGNORECASE,
)
EDIT_RE = re.compile(
    r"\b(corrige|corrigir|edita|editar|altera|alterar|muda|mudar|na verdade)\b",
    re.IGNORECASE,
)
LIST_RE = re.compile(
    r"\b(quanto gastei|o que gastei|lancamentos|lançamentos|fluxo de caixa|gastos de hoje|lista)\b",
    re.IGNORECASE,
)
LAST_RE = re.compile(r"\b(ultimo|última|ultima)\b", re.IGNORECASE)
CHANGE_CATEGORY_RE = re.compile(r"\b(?:muda|mudar|altera|alterar|corrige|corrigir)\s+(?:a\s+)?categoria\b", re.IGNORECASE)
CHANGE_ACCOUNT_RE = re.compile(r"\b(?:muda|mudar|altera|alterar|corrige|corrigir)\s+(?:a\s+)?conta\b", re.IGNORECASE)
HAS_DATE_CUE_RE = re.compile(r"\b(hoje|ontem)\b", re.IGNORECASE)

METHOD_MAP = (
    ("debito", "debito"),
    ("credito", "credito"),
    ("cartao", "credito"),
    ("pix", "pix"),
    ("dinheiro", "dinheiro"),
    ("especie", "dinheiro"),
)


@dataclass
class ParsedIntent:
    action: str
    entry_type: str | None = None
    amount: float | None = None
    category: str | None = None
    account: str | None = None
    method: str | None = None
    description: str | None = None
    date: str | None = None
    last: bool = False
    fields: dict[str, Any] = field(default_factory=dict)
    raw: str = ""


def normalize_text(text: str) -> str:
    lowered = text.lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents)


def compact_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(text))


def _parse_simple_amount(raw: str) -> float:
    return float(raw.replace(",", "."))


def extract_amount(text: str) -> float | None:
    for pattern in (AMOUNT_WITH_UNIT_RE, AMOUNT_RS_RE, AMOUNT_AFTER_VERB_RE):
        match = pattern.search(text)
        if match:
            return _parse_simple_amount(match.group(1))
    return None


def extract_old_and_new_amount(text: str) -> tuple[float | None, float | None]:
    old_match = OLD_AMOUNT_RE.search(text)
    new_match = NEW_AMOUNT_RE.search(text)
    old_amount = _parse_simple_amount(old_match.group(1)) if old_match else None
    new_amount = _parse_simple_amount(new_match.group(1)) if new_match else None
    return old_amount, new_amount


def parse_date_from_text(text: str, today: date) -> str | None:
    norm = normalize_text(text)
    if re.search(r"\bhoje\b", norm):
        return today.isoformat()
    if re.search(r"\bontem\b", norm):
        return (today - timedelta(days=1)).isoformat()
    iso = ISO_DATE_RE.search(text)
    if iso:
        return iso.group(1)
    br = BR_DATE_RE.search(text)
    if br:
        day, month = int(br.group(1)), int(br.group(2))
        year = int(br.group(3)) if br.group(3) else today.year
        if year < 100:
            year += 2000
        return date(year, month, day).isoformat()
    return None


def detect_method(text: str) -> str | None:
    norm = normalize_text(text)
    for needle, method in METHOD_MAP:
        if re.search(rf"\b{needle}\b", norm):
            return method
    return None


def contains_term(norm: str, needle: str) -> bool:
    if not needle:
        return False
    if " " in needle:
        return needle in norm
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", norm))


def _longest_keyword_match(norm: str, mapping: dict[str, tuple[str, ...]]) -> str | None:
    hits: list[tuple[int, str]] = []
    for label, words in mapping.items():
        for word in words:
            needle = normalize_text(word)
            if contains_term(norm, needle):
                hits.append((len(needle), label))
    if not hits:
        return None
    hits.sort(reverse=True)
    return hits[0][1]


def resolve_category(text: str, catalog: Catalog, entry_type: str) -> str | None:
    norm = normalize_text(text)
    keywords = catalog.expense_keywords if entry_type == "expense" else catalog.income_keywords
    matched = _longest_keyword_match(norm, keywords)
    if matched:
        return matched

    pool = catalog.expense_categories if entry_type == "expense" else catalog.income_categories
    compact = compact_key(text)
    for category in pool:
        key = compact_key(category)
        if key and key in compact:
            return category
    return None


def resolve_description(text: str, catalog: Catalog, category: str | None) -> str:
    norm = normalize_text(text)
    matched = _longest_keyword_match(norm, catalog.description_keywords)
    if matched:
        return matched
    return category or "Lançamento"


def resolve_account(text: str, catalog: Catalog) -> str | None:
    norm = normalize_text(text)
    hits: list[tuple[int, str]] = []
    for account in catalog.accounts:
        for alias in (account.name, *account.aliases):
            needle = normalize_text(alias)
            if contains_term(norm, needle):
                hits.append((len(needle), account.name))
    if not hits:
        return None
    hits.sort(reverse=True)
    return hits[0][1]


def detect_action(text: str) -> str:
    if REMOVE_RE.search(text):
        return "remove"
    if EDIT_RE.search(text) and not ADD_EXPENSE_RE.search(text) and not ADD_INCOME_RE.search(text):
        return "edit"
    if ADD_INCOME_RE.search(text):
        return "add"
    if ADD_EXPENSE_RE.search(text):
        return "add"
    if LIST_RE.search(text):
        return "list"
    old_amount, new_amount = extract_old_and_new_amount(text)
    if old_amount is not None or new_amount is not None:
        return "edit"
    return "unknown"


def detect_entry_type(text: str) -> str | None:
    if ADD_INCOME_RE.search(text) and not ADD_EXPENSE_RE.search(text):
        return "income"
    if ADD_EXPENSE_RE.search(text):
        return "expense"
    return None


def parse_message(text: str, catalog: Catalog, today: date) -> ParsedIntent:
    stripped = text.strip()
    action = detect_action(stripped)
    entry_type = detect_entry_type(stripped)
    amount = extract_amount(stripped)
    old_amount, new_amount = extract_old_and_new_amount(stripped)
    method = detect_method(stripped)
    category = resolve_category(stripped, catalog, entry_type or "expense")
    account = resolve_account(stripped, catalog)
    description = resolve_description(stripped, catalog, category)
    parsed_date = parse_date_from_text(stripped, today)
    last = bool(LAST_RE.search(normalize_text(stripped)))

    fields: dict[str, Any] = {}
    match_amount = amount

    if action == "edit":
        if new_amount is not None:
            fields["amount"] = new_amount
            match_amount = old_amount
        elif amount is not None:
            fields["amount"] = amount
            match_amount = old_amount
        if CHANGE_CATEGORY_RE.search(stripped) and category:
            fields["category"] = category
        if CHANGE_ACCOUNT_RE.search(stripped) and account:
            fields["account"] = account
        if method and re.search(r"\b(?:muda|mudar|altera|alterar)\s+(?:o\s+)?(?:metodo|método|pagamento)\b", stripped, re.I):
            fields["method"] = method
        if parsed_date and (HAS_DATE_CUE_RE.search(stripped) or ISO_DATE_RE.search(stripped) or BR_DATE_RE.search(stripped)):
            if re.search(r"\b(?:muda|mudar|altera|para)\s+(?:a\s+)?data\b", normalize_text(stripped)):
                fields["date"] = parsed_date
        last = last or (match_amount is None and account is None and category is None)

    if action == "remove":
        match_amount = old_amount or amount
        last = last or (match_amount is None and account is None and category is None)

    if action == "add":
        match_amount = amount

    return ParsedIntent(
        action=action,
        entry_type=entry_type if action != "unknown" else None,
        amount=match_amount,
        category=category,
        account=account,
        method=method if action == "add" else None,
        description=description if action == "add" else None,
        date=parsed_date,
        last=last,
        fields=fields,
        raw=stripped,
    )
