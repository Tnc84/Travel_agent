import re
from datetime import date, datetime

import dateparser

_MONTH_TOKEN_NORMALIZATION = {
    "ian": "ianuarie",
    "feb": "februarie",
    "mar": "martie",
    "apr": "aprilie",
    "iun": "iunie",
    "iul": "iulie",
    "aug": "august",
    "sep": "septembrie",
    "sept": "septembrie",
    "oct": "octombrie",
    "nov": "noiembrie",
    "dec": "decembrie",
}


def normalize_user_date_to_iso(raw_date: str, year: int | None = None) -> str:
    cleaned = re.sub(r"\s+", " ", raw_date.strip().lower())
    cleaned = _normalize_month_tokens(cleaned)
    if not cleaned:
        raise ValueError("Data nu poate fi goala.")

    today = date.today()
    target_year = year or today.year

    # Enforce explicit ambiguity policy for numeric dates.
    if _is_ambiguous_numeric(cleaned):
        raise ValueError(
            "Format numeric ambiguu. Foloseste luna in text (ex: 15 Aug / 23 Iul) "
            "sau un format clar neambiguu (ex: 25-04 ori 10-23)."
        )

    parsed = _parse_with_dateparser(cleaned, target_year)
    if parsed is None:
        raise ValueError(
            "Data nu este recunoscuta. Exemple valide: 15 Aug, 23 Iul, Jul 23, August 15, 12-07, 10-23."
        )

    # Business rule: if parsed date already passed this year, roll to next year.
    if parsed.date() < today:
        parsed = _parse_with_dateparser(cleaned, target_year + 1)
        if parsed is None:
            raise ValueError(f"Data invalida: {raw_date}")

    return parsed.date().isoformat()


def _parse_with_dateparser(cleaned: str, base_year: int) -> datetime | None:
    return dateparser.parse(
        cleaned,
        languages=["ro", "en"],
        settings={
            "PREFER_DAY_OF_MONTH": "first",
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": datetime(base_year, 1, 1, 12, 0, 0),
            "REQUIRE_PARTS": ["day", "month"],
            "DATE_ORDER": _explicit_date_order(cleaned),
        },
    )


def _normalize_month_tokens(cleaned: str) -> str:
    tokens = re.split(r"(\W+)", cleaned)
    normalized = []
    for token in tokens:
        normalized.append(_MONTH_TOKEN_NORMALIZATION.get(token, token))
    return "".join(normalized)


def _explicit_date_order(cleaned: str) -> str:
    numeric = re.fullmatch(r"\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*", cleaned)
    if not numeric:
        return "DMY"
    first = int(numeric.group(1))
    second = int(numeric.group(2))
    if first > 12:
        return "DMY"
    if second > 12:
        return "MDY"
    # Ambiguous numeric is handled upstream and rejected explicitly.
    return "DMY"


def _is_ambiguous_numeric(cleaned: str) -> bool:
    numeric = re.fullmatch(r"\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*", cleaned)
    if not numeric:
        return False
    first = int(numeric.group(1))
    second = int(numeric.group(2))
    return first <= 12 and second <= 12
