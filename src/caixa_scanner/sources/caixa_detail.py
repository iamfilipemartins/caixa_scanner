from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..config import settings
from ..schemas import PropertyIn
from ..utils import build_session, compact_spaces, parse_brl_number


BASE_URL = "https://venda-imoveis.caixa.gov.br"


def parse_fgts(text: str):
    text_norm = (text or "").lower()

    if "não aceita fgts" in text_norm or "nao aceita fgts" in text_norm:
        return False

    if "não permite utilização do fgts" in text_norm or "nao permite utilizacao do fgts" in text_norm:
        return False

    if "fgts" in text_norm:
        return True

    return None


def parse_financing(text: str):
    text_norm = (text or "").lower()

    if "não aceita financiamento" in text_norm or "nao aceita financiamento" in text_norm:
        return False

    if "financiamento" in text_norm:
        return True

    return None


class CaixaDetailSource:
    def __init__(self) -> None:
        self.session = build_session()

    def enrich(self, item: PropertyIn) -> PropertyIn:
        if not item.detail_url:
            return item

        response = self.session.get(item.detail_url, timeout=settings.request_timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        text = soup.get_text("\n", strip=True)
        page_text_norm = (text or "").lower()

        accepts_fgts = parse_fgts(page_text_norm)
        accepts_financing = parse_financing(page_text_norm)

        edital_url = None
        matricula_url = None
        for anchor in soup.find_all("a", href=True):
            label = compact_spaces(anchor.get_text(" ", strip=True)) or ""
            href = urljoin(BASE_URL, anchor["href"])
            low = label.lower()
            if "edital" in low:
                edital_url = href
            if "matrícula" in low or "matricula" in low:
                matricula_url = href

        expense_rules = self._extract_section(text, "REGRAS PARA PAGAMENTO DAS DESPESAS")
        payment_rules = self._extract_section(text, "FORMAS DE PAGAMENTO ACEITAS")

        if item.private_area_m2 is None or item.bedrooms is None or item.parking_spots is None:
            area, bedrooms, parking = self._infer_from_text(item.description or text)
        else:
            area, bedrooms, parking = item.private_area_m2, item.bedrooms, item.parking_spots

        return item.model_copy(
            update={
                "edital_url": edital_url or item.edital_url,
                "matricula_url": matricula_url or item.matricula_url,
                "accepts_fgts": accepts_fgts,
                "accepts_financing": accepts_financing,
                "expense_rules": expense_rules,
                "payment_rules": payment_rules,
                "private_area_m2": area,
                "bedrooms": bedrooms,
                "parking_spots": parking,
            }
        )

    @staticmethod
    def _extract_section(text: str, section_title: str) -> str | None:
        pattern = rf"{re.escape(section_title)}:(.*?)(?:Baixar edital|Dê seu lance|Topo|$)"
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        return compact_spaces(match.group(1))

    @staticmethod
    def _infer_from_text(text: str) -> tuple[float | None, int | None, int | None]:
        normalized = compact_spaces(text) or ""
        area = None
        bedrooms = None
        parking = None

        area_match = re.search(r"(\d+[\.,]?\d*)\s*m2", normalized, flags=re.IGNORECASE)
        if area_match:
            area = parse_brl_number(area_match.group(1))

        bed_match = re.search(r"(\d+)\s*quartos?", normalized, flags=re.IGNORECASE)
        if bed_match:
            bedrooms = int(bed_match.group(1))

        parking_match = re.search(r"(\d+)\s*(vagas?|garagens?)", normalized, flags=re.IGNORECASE)
        if parking_match:
            parking = int(parking_match.group(1))

        return area, bedrooms, parking
