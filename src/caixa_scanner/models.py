from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    uf: Mapped[str | None] = mapped_column(String(2), index=True)
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    neighborhood: Mapped[str | None] = mapped_column(String(200), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Float)
    appraisal_value: Mapped[float | None] = mapped_column(Float)
    discount_pct: Mapped[float | None] = mapped_column(Float)
    financing_text: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)

    detail_url: Mapped[str | None] = mapped_column(Text)
    edital_url: Mapped[str | None] = mapped_column(Text)
    matricula_url: Mapped[str | None] = mapped_column(Text)
    edital_sale_mode: Mapped[str | None] = mapped_column(String(120))
    edital_sale_date: Mapped[str | None] = mapped_column(String(40))
    edital_payment_details: Mapped[str | None] = mapped_column(Text)
    edital_risk_notes: Mapped[str | None] = mapped_column(Text)
    edital_has_occupied_risk: Mapped[bool | None] = mapped_column(Boolean)
    edital_has_no_visit_risk: Mapped[bool | None] = mapped_column(Boolean)
    edital_buyer_pays_condo: Mapped[bool | None] = mapped_column(Boolean)
    edital_buyer_pays_iptu: Mapped[bool | None] = mapped_column(Boolean)
    edital_has_judicial_risk: Mapped[bool | None] = mapped_column(Boolean)

    accepts_fgts: Mapped[bool | None] = mapped_column(Boolean)
    accepts_financing: Mapped[bool | None] = mapped_column(Boolean)
    expense_rules: Mapped[str | None] = mapped_column(Text)
    payment_rules: Mapped[str | None] = mapped_column(Text)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime)
    detail_enriched_at: Mapped[datetime | None] = mapped_column(DateTime)
    edital_enriched_at: Mapped[datetime | None] = mapped_column(DateTime)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime)
    scoring_version: Mapped[str | None] = mapped_column(String(64))

    bedrooms: Mapped[int | None] = mapped_column(Integer)
    parking_spots: Mapped[int | None] = mapped_column(Integer)

    opportunity_score: Mapped[float | None] = mapped_column(Float, index=True)
    score_reason: Mapped[str | None] = mapped_column(Text)
    last_alerted_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    property_type: Mapped[str | None] = mapped_column(String(120))
    private_area_m2: Mapped[float | None] = mapped_column(Float)
    total_area_m2: Mapped[float | None] = mapped_column(Float)
    land_area_m2: Mapped[float | None] = mapped_column(Float)
    bathrooms: Mapped[int | None] = mapped_column(Integer)

    score_preco: Mapped[float | None] = mapped_column(Float)
    score_imovel: Mapped[float | None] = mapped_column(Float)
    score_localizacao: Mapped[float | None] = mapped_column(Float)
    score_liquidez_residencial: Mapped[float | None] = mapped_column(Float)
    score_risco: Mapped[float | None] = mapped_column(Float)
    score_moradia: Mapped[float | None] = mapped_column(Float)
    score_moradia_reason: Mapped[str | None] = mapped_column(Text)
