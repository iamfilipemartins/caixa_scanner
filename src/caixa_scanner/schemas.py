from __future__ import annotations

from pydantic import BaseModel, Field


class PropertyIn(BaseModel):
    property_code: str
    uf: str | None = None
    city: str | None = None
    neighborhood: str | None = None
    address: str | None = None
    price: float | None = None
    appraisal_value: float | None = None
    discount_pct: float | None = None
    financing_text: str | None = None
    description: str | None = None
    detail_url: str | None = None
    edital_url: str | None = None
    matricula_url: str | None = None
    accepts_fgts: bool | None = None
    accepts_financing: bool | None = None
    expense_rules: str | None = None
    payment_rules: str | None = None
    bedrooms: int | None = None
    parking_spots: int | None = None
    opportunity_score: float | None = Field(default=None, ge=0, le=100)
    score_reason: str | None = None
    property_type: str | None = None
    private_area_m2: float | None = None
    total_area_m2: float | None = None
    land_area_m2: float | None = None
    bathrooms: int | None = None

    score_preco: float | None = None
    score_imovel: float | None = None
    score_localizacao: float | None = None
    score_liquidez_residencial: float | None = None
    score_risco: float | None = None
    score_moradia: float | None = None
    score_moradia_reason: str | None = None
