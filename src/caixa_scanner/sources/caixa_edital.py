from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

from ..config import settings
from ..schemas import PropertyIn
from ..utils import build_session, compact_spaces


SALE_MODE_PATTERNS = [
    ("licitacao aberta", "Licitacao aberta"),
    ("licitacao fechada", "Licitacao fechada"),
    ("venda online", "Venda online"),
    ("concorrencia publica", "Concorrencia publica"),
    ("1o leilao", "1o leilao"),
    ("2o leilao", "2o leilao"),
]


@dataclass(slots=True)
class EditalInfo:
    sale_mode: str | None = None
    sale_date: str | None = None
    payment_details: str | None = None
    risk_notes: str | None = None
    has_occupied_risk: bool | None = None
    has_no_visit_risk: bool | None = None
    buyer_pays_condo: bool | None = None
    buyer_pays_iptu: bool | None = None
    has_judicial_risk: bool | None = None


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def normalize_pdf_text(text: str) -> str:
    normalized = text.replace("\r", "\n")
    normalized = normalized.replace("licitação", "licitacao")
    normalized = normalized.replace("licitação", "licitacao")
    normalized = normalized.replace("concorrência", "concorrencia")
    normalized = normalized.replace("leilão", "leilao")
    normalized = normalized.replace("sessão", "sessao")
    normalized = normalized.replace("visitação", "visitacao")
    normalized = normalized.replace("condomínio", "condominio")
    normalized = normalized.replace("ação", "acao")
    normalized = normalized.replace("imóvel", "imovel")
    normalized = normalized.replace("à vista", "a vista")
    return compact_spaces(normalized) or ""


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
        r"(formas? de pagamento[^:]*:?\s*)(.*?)(?:\.\s|responsabilidade|ocupado|imovel|$)",
        normalized,
        flags=re.IGNORECASE,
    )
    if payment_match:
        payment_details = compact_spaces(payment_match.group(2))

    has_occupied_risk = "ocupado" in lowered
    has_no_visit_risk = "sem visita" in lowered or "visitacao nao permitida" in lowered
    buyer_pays_condo = "condominio" in lowered
    buyer_pays_iptu = "iptu" in lowered
    has_judicial_risk = "acao judicial" in lowered
    buyer_responsibility = "responsabilidade do comprador" in lowered

    risk_notes: list[str] = []
    if has_occupied_risk:
        risk_notes.append("Imovel ocupado")
    if has_no_visit_risk:
        risk_notes.append("Visitacao restrita")
    if buyer_pays_condo:
        risk_notes.append("Validar debitos de condominio")
    if buyer_pays_iptu:
        risk_notes.append("Validar debitos de IPTU")
    if has_judicial_risk:
        risk_notes.append("Existe mencao a acao judicial")
    if buyer_responsibility:
        risk_notes.append("Despesas sob responsabilidade do comprador")

    return EditalInfo(
        sale_mode=sale_mode,
        sale_date=sale_date,
        payment_details=payment_details,
        risk_notes="; ".join(dict.fromkeys(risk_notes)) or None,
        has_occupied_risk=has_occupied_risk,
        has_no_visit_risk=has_no_visit_risk,
        buyer_pays_condo=buyer_pays_condo,
        buyer_pays_iptu=buyer_pays_iptu,
        has_judicial_risk=has_judicial_risk,
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
                "edital_has_occupied_risk": parsed.has_occupied_risk,
                "edital_has_no_visit_risk": parsed.has_no_visit_risk,
                "edital_buyer_pays_condo": parsed.buyer_pays_condo,
                "edital_buyer_pays_iptu": parsed.buyer_pays_iptu,
                "edital_has_judicial_risk": parsed.has_judicial_risk,
            }
        )
