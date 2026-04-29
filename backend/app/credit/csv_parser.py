"""F29 - Parser CSV generique normalise pour statements Mobile Money.

Format attendu (entete obligatoire) :
``date_iso,amount_xof,direction,counterparty?``

- ``date_iso`` : ISO 8601 ``YYYY-MM-DD`` (ou ``YYYY-MM-DDTHH:MM:SS``).
- ``amount_xof`` : entier strictement positif.
- ``direction`` : ``in`` ou ``out``.
- ``counterparty`` : libre (peut etre vide).

Limites MVP :
- max 5 MB et 10 000 lignes (au-dela -> ``StatementTooLargeError``).
- mappers Wave/Orange/MTN/Free Money sont [DEFERRED].
"""

from __future__ import annotations

import csv
import io
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

MAX_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 10_000
REQUIRED_COLUMNS = ("date_iso", "amount_xof", "direction")
ALLOWED_DIRECTIONS = ("in", "out")


class StatementParseError(ValueError):
    """Erreur de parsing (format, encodage, colonnes)."""


class StatementTooLargeError(ValueError):
    """Fichier au-dela des limites MVP (taille ou nombre de lignes)."""


@dataclass(frozen=True)
class NormalizedTransaction:
    date_iso: str
    amount_xof: int
    direction: str
    counterparty: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "date_iso": self.date_iso,
            "amount_xof": self.amount_xof,
            "direction": self.direction,
            "counterparty": self.counterparty,
        }


def _parse_date(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise StatementParseError("date_iso vide")
    try:
        if "T" in value:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            date.fromisoformat(value)
    except ValueError as exc:
        raise StatementParseError(f"date_iso invalide: {value!r}") from exc
    return value


def _parse_amount(value: str) -> int:
    value = (value or "").strip()
    if not value:
        raise StatementParseError("amount_xof vide")
    try:
        amount = int(value)
    except ValueError as exc:
        raise StatementParseError(
            f"amount_xof doit etre un entier: {value!r}"
        ) from exc
    if amount <= 0:
        raise StatementParseError(f"amount_xof doit etre > 0: {amount}")
    return amount


def _parse_direction(value: str) -> str:
    value = (value or "").strip().lower()
    if value not in ALLOWED_DIRECTIONS:
        raise StatementParseError(
            f"direction doit etre dans {ALLOWED_DIRECTIONS}, recu: {value!r}"
        )
    return value


def parse_statement(raw_bytes: bytes) -> dict[str, Any]:
    """Parse un CSV normalise et retourne {transactions, indicators}."""
    if len(raw_bytes) > MAX_BYTES:
        raise StatementTooLargeError(
            f"fichier trop volumineux: {len(raw_bytes)} > {MAX_BYTES}"
        )
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise StatementParseError("encodage non supporte") from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise StatementParseError("CSV vide ou sans entete")
    headers = [h.strip() for h in reader.fieldnames]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise StatementParseError(f"colonnes manquantes: {missing}")

    transactions: list[NormalizedTransaction] = []
    for idx, row in enumerate(reader, start=2):
        if len(transactions) >= MAX_ROWS:
            raise StatementTooLargeError(
                f"trop de transactions: > {MAX_ROWS}"
            )
        try:
            tx = NormalizedTransaction(
                date_iso=_parse_date(row.get("date_iso", "")),
                amount_xof=_parse_amount(row.get("amount_xof", "")),
                direction=_parse_direction(row.get("direction", "")),
                counterparty=(row.get("counterparty") or "").strip() or None,
            )
        except StatementParseError as exc:
            raise StatementParseError(f"ligne {idx}: {exc}") from exc
        transactions.append(tx)

    return {
        "transactions": [tx.to_dict() for tx in transactions],
        "indicators": _compute_indicators(transactions),
    }


def _compute_indicators(txs: list[NormalizedTransaction]) -> dict[str, Any]:
    nb = len(txs)
    if nb == 0:
        return {
            "nb_transactions": 0,
            "monthly_mean_xof": 0.0,
            "monthly_stdev_xof": 0.0,
            "ratio_in_out": None,
            "total_in_xof": 0,
            "total_out_xof": 0,
            "months_covered": 0,
        }

    monthly_total: dict[str, int] = {}
    total_in = 0
    total_out = 0

    for tx in txs:
        month_key = tx.date_iso[:7]
        monthly_total[month_key] = monthly_total.get(month_key, 0) + tx.amount_xof
        if tx.direction == "in":
            total_in += tx.amount_xof
        else:
            total_out += tx.amount_xof

    months = list(monthly_total.values())
    monthly_mean = statistics.mean(months) if months else 0.0
    monthly_stdev = statistics.pstdev(months) if len(months) > 1 else 0.0
    ratio_in_out = (total_in / total_out) if total_out > 0 else None

    return {
        "nb_transactions": nb,
        "monthly_mean_xof": float(monthly_mean),
        "monthly_stdev_xof": float(monthly_stdev),
        "ratio_in_out": ratio_in_out,
        "total_in_xof": total_in,
        "total_out_xof": total_out,
        "months_covered": len(months),
    }
