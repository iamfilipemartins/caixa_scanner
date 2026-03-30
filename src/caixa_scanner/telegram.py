from __future__ import annotations

import logging
from typing import Any

import requests

from caixa_scanner.config import settings


logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self) -> None:
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id

    @property
    def enabled(self) -> bool:
        return bool(settings.telegram_enabled and settings.telegram_available)

    def send_message(self, text: str) -> bool:
        if not self.enabled:
            logger.info("Telegram sending is disabled or credentials are missing.")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        response = requests.post(
            url,
            json={
                "chat_id": self.chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=settings.request_timeout,
        )

        if response.status_code >= 400:
            logger.error("Telegram error %s: %s", response.status_code, response.text)
            return False

        return True

    def build_property_message(self, item: Any) -> str:
        city = item.city or ""
        uf = item.uf or ""
        neighborhood = item.neighborhood or ""
        address = item.address or ""
        property_type = (item.property_type or "").title()
        area = f"{item.private_area_m2:.2f} m²" if item.private_area_m2 is not None else "N/I"
        bedrooms = str(item.bedrooms) if item.bedrooms is not None else "N/I"
        parking = str(item.parking_spots) if item.parking_spots is not None else "N/I"
        price = (
            f"R$ {item.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if item.price is not None
            else "N/I"
        )
        appraisal = (
            f"R$ {item.appraisal_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if item.appraisal_value is not None
            else "N/I"
        )
        discount = f"{item.discount_pct:.2f}%" if item.discount_pct is not None else "N/I"
        score = f"{item.score_moradia:.2f}" if item.score_moradia is not None else "N/I"
        sale_mode = item.edital_sale_mode or "N/I"
        sale_date = item.edital_sale_date or "N/I"
        edital_risks = item.edital_risk_notes or "N/I"

        return (
            "Oportunidade para moradia\n\n"
            f"Cidade: {city}/{uf}\n"
            f"Bairro: {neighborhood}\n"
            f"Endereço: {address}\n"
            f"Tipo: {property_type}\n"
            f"Área privativa: {area}\n"
            f"Quartos: {bedrooms}\n"
            f"Vagas: {parking}\n\n"
            f"Preço: {price}\n"
            f"Avaliação: {appraisal}\n"
            f"Desconto: {discount}\n"
            f"Score moradia: {score}\n"
            f"Modalidade do edital: {sale_mode}\n"
            f"Data relevante do edital: {sale_date}\n"
            f"Riscos do edital: {edital_risks}\n\n"
            f"Motivo: {item.score_moradia_reason or item.score_reason or 'N/I'}\n\n"
            f"Link: {item.detail_url or ''}"
        )
