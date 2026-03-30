from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

from ..config import settings
from ..schemas import PropertyIn
from ..utils import build_session, compact_spaces


SALE_MODE_PATTERNS = [
    ("licitação aberta", "Licitação aberta"),
    ("licitacao aberta", "Licitação aberta"),
    ("licitação fechada", "Licitação fechada"),
    ("licitacao fechada", "Licitação fechada"),
    ("venda online", "Venda online"),
    ("concorrência pública", "Concorrência pública"),
    ("concorrencia publica", "Concorrência pública"),
    ("1º leilão", "1º leilão"),
    ("2º leilão", "2º leilão"),
]

RISK_PATTERNS = [
    ("ocupado", "Imóvel ocupado"),
    ("sem visita", "Visitação restrita"),
    ("responsabilidade do comprador", "Despesas sob responsabilidade do comprador"),
    ("condomínio", "Validar débitos de condomínio"),
    ("condominio", "Validar débitos de condomínio"),
    ("iptu", "Validar débitos de IPTU"),
    ("ação judicial", "Existe menção a ação judicial"),
    ("acao judicial", "Existe menção a ação judicial"),
]


@dataclass(slots=True)
class EditalInfo:
    sale_mode: str | None = None
    sale_date: str | None = None
    payment_details: str | None = None
    risk_notes: str | None = None


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def normalize_pdf_text(text: str) -> str:
    return compact_spaces(text.replace("\r", "\n")) or ""


def parse_edital_text(text: str) -> EditalInfo:
    normalized = normalize_pdf_text(text)
    lowered = normalized.lower()

    sale_mode = None
    for token, label in SALE_MODE_PATTERNS:
        if token in lowered:
            sale_mode = label
            break

    sale_date = None
    date_patterns = [
        r"(?:1º leilão|2º leilão|data do leilão|sessão pública)[^0-9]{0,40}(\d{2}/\d{2}/\d{4})",
        r"(?:1o leilao|2o leilao|data do leilao|sessao publica)[^0-9]{0,40}(\d{2}/\d{2}/\d{4})",
        r"(\d{2}/\d{2}/\d{4})",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            sale_date = match.group(1)
            break

    payment_details = None
    payment_match = re.search(
        r"(formas? de pagamento[^:]*:?\s*)(.*?)(?:\.\s|responsabilidade|ocupado|im[oó]vel|$)",
        normalized,
        flags=re.IGNORECASE,
    )
    if payment_match:
        payment_details = compact_spaces(payment_match.group(2))

    risk_notes = []
    for token, label in RISK_PATTERNS:
        if token in lowered:
            risk_notes.append(label)

    return EditalInfo(
        sale_mode=sale_mode,
        sale_date=sale_date,
        payment_details=payment_details,
        risk_notes="; ".join(dict.fromkeys(risk_notes)) or None,
    )


class CaixaEditalSource:
    def __init__(self) -> None:
        self.session = build_session()

    def enrich(self, item: PropertyIn) -> PropertyIn:
        if not item.edital_url:
            return item

        response = self.session.get(item.edital_url, timeout=settings.request_timeout)
        response.raise_for_status()
        parsed = parse_edital_text(extract_pdf_text(response.content))

        return item.model_copy(
            update={
                "edital_sale_mode": parsed.sale_mode or item.edital_sale_mode,
                "edital_sale_date": parsed.sale_date or item.edital_sale_date,
                "edital_payment_details": parsed.payment_details or item.edital_payment_details,
                "edital_risk_notes": parsed.risk_notes or item.edital_risk_notes,
            }
        )
