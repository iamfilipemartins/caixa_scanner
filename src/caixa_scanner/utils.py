from __future__ import annotations

import re
from typing import Iterable

import requests

from .config import settings


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": settings.user_agent,
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        }
    )
    return session


def parse_brl_number(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = (
        value.replace("R$", "")
        .replace(".", "")
        .replace("%", "")
        .replace(" ", " ")
        .strip()
        .replace(",", ".")
    )
    cleaned = re.sub(r"[^0-9.-]", "", cleaned)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def compact_spaces(text: str | None) -> str | None:
    if text is None:
        return None
    return re.sub(r"\s+", " ", text).strip() or None


def first_non_empty(values: Iterable[str | None]) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None
