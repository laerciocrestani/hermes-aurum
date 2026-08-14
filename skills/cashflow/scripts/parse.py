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
    r"\b(?:gastei|paguei|comprei|recebi|ganhei|entrou|pago)\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\b",
    re.IGNORECASE,
)
AMOUNT_COMPRA_RE = re.compile(
    r"\bcompra\s+de\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\b",
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
INSTALLMENTS_RE = re.compile(r"(?:em\s+)?(\d+)\s*x\b", re.IGNORECASE)
DUE_DAY_RE = re.compile(
    r"\b(?:todo\s+dia|dia|vence(?:m)?|vencimento)\s+(\d{1,2})\b",
    re.IGNORECASE,
)
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
BR_DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d{1,2})?")

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
UPCOMING_RE = re.compile(
    r"\b(cobrancas|cobranças|vencimentos|o que vence|contas do mes|contas do mês|"
    r"parcelas|futuro|proximos vencimentos|próximos vencimentos|agenda)\b",
    re.IGNORECASE,
)
LAST_RE = re.compile(r"\b(ultimo|última|ultima)\b", re.IGNORECASE)
CHANGE_CATEGORY_RE = re.compile(r"\b(?:muda|mudar|altera|alterar|corrige|corrigir)\s+(?:a\s+)?categoria\b", re.IGNORECASE)
CHANGE_ACCOUNT_RE = re.compile(
    r"\b(?:muda|mudar|altera|alterar|corrige|corrigir)\s+(?:a\s+)?conta\s+para\b",
    re.IGNORECASE,
)
HAS_DATE_CUE_RE = re.compile(r"\b(hoje|ontem)\b", re.IGNORECASE)
RECURRING_RE = re.compile(
    r"\b(mensal|todo mes|por mes|recorrente|assinatura|todo dia|toda mes)\b",
    re.IGNORECASE,
)
BILL_RE = re.compile(
    r"\b(conta de|agua|luz|telefone|celular|energia|internet|aluguel|condominio)\b",
    re.IGNORECASE,
)
PARCEL_RE = re.compile(r"\b(parcela|parcelas|parcelado|parcelamento|cartao|cartão)\b", re.IGNORECASE)
LANCAMENTO_RE = re.compile(r"\b(lancamento|lançamento)\b", re.IGNORECASE)
COMPRA_RE = re.compile(r"\b(compra|comprei)\b", re.IGNORECASE)
ACCOUNT_CREATE_RE = re.compile(
    r"\b(nova conta|novo cartao|adiciona(?:r)? (?:a |o )?(?:conta|cartao)|"
    r"cadastra(?:r)? (?:a |o )?(?:conta|cartao)|abre conta|cria(?:r)? (?:a |o )?conta|"
    r"configura(?:r)? (?:a |o )?(?:conta|cartao))\b",
    re.IGNORECASE,
)
BALANCES_RE = re.compile(
    r"\b(quanto tenho|saldo|saldos|minhas contas|saldo da carteira)\b",
    re.IGNORECASE,
)
INITIAL_BALANCE_RE = re.compile(
    r"\b(?:saldo(?: inicial)?(?: de)?|com saldo(?: de)?)\s+(?:de\s+)?(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)"
    r"|\bcom\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais|reias|real)\b",
    re.IGNORECASE,
)
CLOSING_DAY_RE = re.compile(
    r"\b(?:fechamento|fecha(?:mento)?)\s+(?:em\s+|dia\s+)?(\d{1,2})\b",
    re.IGNORECASE,
)
PAYMENT_DAY_RE = re.compile(
    r"\b(?:pagamento(?: da fatura)?|fatura|paga(?:mento)?)\s+(?:em\s+|dia\s+)?(\d{1,2})\b",
    re.IGNORECASE,
)

KNOWN_BANKS = (
    ("banco inter", "Banco Inter"),
    ("c6 bank", "C6 Bank"),
    ("c6bank", "C6 Bank"),
    ("c6banck", "C6 Bank"),
    ("nubank", "Nubank"),
    ("carteira", "Carteira"),
    ("picpay", "PicPay"),
    ("bradesco", "Bradesco"),
    ("santander", "Santander"),
    ("banco itau", "Itaú"),
    ("itau", "Itaú"),
    ("caixa", "Caixa"),
    ("inter", "Banco Inter"),
    ("c6", "C6 Bank"),
)

METHOD_MAP = (
    ("debito", "debito"),
    ("credito", "credito"),
    ("cartao", "credito"),
    ("pix", "pix"),
    ("dinheiro", "dinheiro"),
    ("especie", "dinheiro"),
)

BILL_LABELS = (
    ("conta de agua", "Água"),
    ("conta de luz", "Luz"),
    ("telefone", "Telefone"),
    ("celular", "Telefone"),
    ("internet", "Internet"),
    ("aluguel", "Aluguel"),
    ("condominio", "Condomínio"),
    ("energia", "Luz"),
    ("agua", "Água"),
    ("luz", "Luz"),
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
    target: str = "entry"
    kind: str | None = None
    installments: int | None = None
    due_day: int | None = None
    account_kind: str | None = None
    initial_balance: float | None = None
    closing_day: int | None = None
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


def extract_installments(text: str) -> int | None:
    match = INSTALLMENTS_RE.search(text)
    if not match:
        return None
    count = int(match.group(1))
    return count if count > 1 else None


def extract_due_day(text: str) -> int | None:
    match = DUE_DAY_RE.search(text)
    if not match:
        return None
    day = int(match.group(1))
    if 1 <= day <= 31:
        return day
    return None


def extract_closing_day(text: str) -> int | None:
    match = CLOSING_DAY_RE.search(text)
    if not match:
        return None
    day = int(match.group(1))
    return day if 1 <= day <= 31 else None


def extract_payment_day(text: str) -> int | None:
    match = PAYMENT_DAY_RE.search(text)
    if not match:
        return None
    day = int(match.group(1))
    return day if 1 <= day <= 31 else None


def extract_initial_balance(text: str) -> float | None:
    match = INITIAL_BALANCE_RE.search(text)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    return _parse_simple_amount(raw)


def extract_account_kind(text: str) -> str | None:
    norm = normalize_text(text)
    if re.search(r"\b(cartao|credito)\b", norm) and not re.search(r"\bdebito\b", norm):
        return "credit"
    if re.search(r"\b(debito|carteira|pix)\b", norm):
        return "debit"
    if extract_closing_day(text) or extract_payment_day(text):
        return "credit"
    if extract_initial_balance(text) is not None:
        return "debit"
    return None


def extract_new_account_name(text: str, catalog: Catalog | None = None) -> str | None:
    norm = normalize_text(text)
    hits: list[tuple[int, str]] = []
    if catalog:
        for account in catalog.accounts:
            for alias in (account.name, *account.aliases):
                needle = normalize_text(alias)
                if contains_term(norm, needle):
                    hits.append((len(needle), account.name))
    for alias, name in KNOWN_BANKS:
        if contains_term(norm, alias):
            hits.append((len(alias), name))
    if hits:
        hits.sort(reverse=True)
        return hits[0][1]
    match = re.search(
        r"(?:conta(?: de)?(?: debito)?|cartao(?: de credito)?)\s+([a-z0-9][a-z0-9 ]{1,30}?)(?:\s+com|\s+saldo|\s+fecha|\s+fechamento|\s+fatura|\s+pagamento|$)",
        norm,
    )
    if not match:
        return None
    raw = match.group(1).strip()
    if not raw:
        return None
    return " ".join(part.capitalize() for part in raw.split())


def extract_amount(text: str) -> float | None:
    for pattern in (AMOUNT_WITH_UNIT_RE, AMOUNT_RS_RE, AMOUNT_COMPRA_RE, AMOUNT_AFTER_VERB_RE):
        match = pattern.search(text)
        if match:
            return _parse_simple_amount(match.group(1))
    due_day = extract_due_day(text)
    skip_spans = [m.span() for m in INSTALLMENTS_RE.finditer(text)]
    for match in NUMBER_RE.finditer(text):
        if any(match.start() >= start and match.end() <= end for start, end in skip_spans):
            continue
        raw = match.group(0)
        if due_day is not None and raw.isdigit() and int(raw) == due_day:
            continue
        value = _parse_simple_amount(raw)
        if value > 0:
            return value
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


def resolve_bill_description(text: str) -> str | None:
    norm = normalize_text(text)
    hits: list[tuple[int, str]] = []
    for needle, label in BILL_LABELS:
        if contains_term(norm, needle):
            hits.append((len(needle), label))
    if not hits:
        return None
    hits.sort(reverse=True)
    return hits[0][1]


def resolve_description(text: str, catalog: Catalog, category: str | None) -> str:
    bill = resolve_bill_description(text)
    if bill:
        return bill
    norm = normalize_text(text)
    matched = _longest_keyword_match(norm, catalog.description_keywords)
    if matched:
        return matched
    if COMPRA_RE.search(text):
        return "Compra"
    return category or "Lançamento"


def resolve_account(text: str, catalog: Catalog, prefer_kind: str | None = None) -> str | None:
    norm = normalize_text(text)
    hits: list[tuple[int, int, str]] = []
    for account in catalog.accounts:
        for alias in (account.name, *account.aliases):
            needle = normalize_text(alias)
            if contains_term(norm, needle):
                kind_bonus = 1 if prefer_kind and account.kind == prefer_kind else 0
                hits.append((len(needle), kind_bonus, account.name))
    if not hits:
        return None
    hits.sort(reverse=True)
    return hits[0][2]


def is_account_setup(text: str) -> bool:
    norm = normalize_text(text)
    if ACCOUNT_CREATE_RE.search(norm):
        return True
    if extract_installments(text) or ADD_EXPENSE_RE.search(text) or COMPRA_RE.search(text):
        return False
    if extract_closing_day(text) and extract_payment_day(text):
        return True
    if extract_initial_balance(text) is not None and re.search(
        r"\b(conta|debito|carteira)\b", norm
    ) and not is_bill(text):
        return True
    return False


def is_recurring(text: str) -> bool:
    return bool(RECURRING_RE.search(normalize_text(text)))


def is_bill(text: str) -> bool:
    return bool(BILL_RE.search(normalize_text(text)))


def is_schedule_message(text: str, *, installments: int | None) -> bool:
    if installments:
        return True
    if LANCAMENTO_RE.search(text):
        return False
    norm = normalize_text(text)
    if is_recurring(text) or is_bill(text):
        return True
    if PARCEL_RE.search(norm) or "cobranca" in norm:
        return True
    return False


def detect_action(text: str) -> str:
    if UPCOMING_RE.search(text):
        return "upcoming"
    if BALANCES_RE.search(text) and not ADD_EXPENSE_RE.search(text) and not is_account_setup(text):
        return "balances"
    if is_account_setup(text):
        if REMOVE_RE.search(text):
            return "remove"
        if EDIT_RE.search(text) and not ACCOUNT_CREATE_RE.search(normalize_text(text)):
            return "edit"
        return "add"
    if REMOVE_RE.search(text):
        return "remove"
    if EDIT_RE.search(text) and not ADD_EXPENSE_RE.search(text) and not ADD_INCOME_RE.search(text):
        return "edit"
    if ADD_INCOME_RE.search(text):
        return "add"
    if ADD_EXPENSE_RE.search(text):
        return "add"
    if COMPRA_RE.search(text) and extract_installments(text):
        return "add"
    if is_recurring(text) or (is_bill(text) and extract_amount(text)):
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
    installments = extract_installments(stripped)
    closing_day = extract_closing_day(stripped)
    payment_day = extract_payment_day(stripped)
    initial_balance = extract_initial_balance(stripped)
    account_kind = extract_account_kind(stripped)
    action = detect_action(stripped)
    setup = action != "unknown" and is_account_setup(stripped)
    due_day = payment_day if setup else (payment_day or extract_due_day(stripped))
    entry_type = detect_entry_type(stripped)
    amount = extract_amount(stripped)
    old_amount, new_amount = extract_old_and_new_amount(stripped)
    method = detect_method(stripped)
    category = resolve_category(stripped, catalog, entry_type or "expense")
    prefer_kind = "credit" if (method == "credito" or installments or account_kind == "credit") else "debit"
    account = resolve_account(stripped, catalog, prefer_kind=prefer_kind)
    if is_account_setup(stripped):
        account = extract_new_account_name(stripped, catalog) or account
    description = resolve_description(stripped, catalog, category)
    parsed_date = parse_date_from_text(stripped, today)
    last = bool(LAST_RE.search(normalize_text(stripped)))

    kind: str | None = None
    target = "entry"
    paying_now = bool(ADD_EXPENSE_RE.search(stripped)) and not installments and not is_recurring(stripped)

    if action == "balances":
        target = "account"
    elif is_account_setup(stripped):
        target = "account"
        kind = account_kind or ("credit" if closing_day or payment_day else "debit")
        method = "credito" if kind == "credit" else (method or "debito")
    elif action == "upcoming":
        target = "schedule"
    elif installments:
        kind = "installment"
        target = "schedule"
        method = method or "credito"
        entry_type = "expense"
    elif (is_recurring(stripped) or (is_bill(stripped) and not paying_now)) and action in {
        "add",
        "remove",
        "edit",
    }:
        kind = "recurring"
        target = "schedule"
        entry_type = "expense"
    elif action in {"remove", "edit"} and is_schedule_message(stripped, installments=installments):
        target = "schedule"
        kind = "installment" if PARCEL_RE.search(stripped) else "recurring"

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
        if due_day and re.search(r"\b(vencimento|vence|dia)\b", normalize_text(stripped)):
            fields["due_day"] = due_day
        if parsed_date and (HAS_DATE_CUE_RE.search(stripped) or ISO_DATE_RE.search(stripped) or BR_DATE_RE.search(stripped)):
            if re.search(r"\b(?:muda|mudar|altera|para)\s+(?:a\s+)?data\b", normalize_text(stripped)):
                fields["date"] = parsed_date
        last = last or (match_amount is None and account is None and category is None and description in {None, category, "Lançamento"})

    if action == "remove":
        match_amount = old_amount or amount
        last = last or (match_amount is None and account is None and category is None and not resolve_bill_description(stripped))

    if action == "add":
        match_amount = amount

    return ParsedIntent(
        action=action,
        entry_type=entry_type if action != "unknown" else None,
        amount=match_amount,
        category=category,
        account=account,
        method=method if action == "add" else None,
        description=description if action in {"add", "remove", "edit"} else None,
        date=parsed_date,
        last=last,
        target=target,
        kind=kind,
        installments=installments,
        due_day=due_day,
        account_kind=account_kind if target == "account" else None,
        initial_balance=initial_balance,
        closing_day=closing_day,
        fields=fields,
        raw=stripped,
    )
