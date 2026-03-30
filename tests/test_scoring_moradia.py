from __future__ import annotations

from caixa_scanner.schemas import PropertyIn
from caixa_scanner.valuation.scoring_moradia import build_moradia_scores


def make_item(**overrides) -> PropertyIn:
    base = {
        "property_code": "1",
        "uf": "MG",
        "city": "Belo Horizonte",
        "neighborhood": "Savassi",
        "address": "Rua A 123",
        "price": 200000.0,
        "appraisal_value": 300000.0,
        "discount_pct": 33.0,
        "description": "Apartamento",
        "property_type": "apartamento",
        "private_area_m2": 70.0,
        "bedrooms": 2,
        "parking_spots": 1,
    }
    base.update(overrides)
    return PropertyIn(**base)


def test_build_moradia_scores_populates_component_scores():
    item = build_moradia_scores(make_item())

    assert item.score_preco is not None
    assert item.score_imovel is not None
    assert item.score_localizacao is not None
    assert item.score_liquidez_residencial is not None
    assert item.score_risco is not None
    assert item.score_moradia is not None
    assert item.opportunity_score == item.score_moradia
    assert "Localiza" in item.score_moradia_reason


def test_build_moradia_scores_penalizes_bad_location():
    premium = build_moradia_scores(make_item(property_code="premium", neighborhood="Savassi"))
    poor_location = build_moradia_scores(
        make_item(
            property_code="poor",
            city="Cidade Desconhecida",
            neighborhood="Zona Rural",
            address="",
        )
    )

    assert premium.score_localizacao > poor_location.score_localizacao
    assert premium.score_moradia > poor_location.score_moradia


def test_build_moradia_scores_rewards_better_discount():
    lower_discount = build_moradia_scores(make_item(property_code="low", discount_pct=20.0))
    higher_discount = build_moradia_scores(make_item(property_code="high", discount_pct=50.0))

    assert higher_discount.score_preco > lower_discount.score_preco
    assert higher_discount.score_moradia >= lower_discount.score_moradia
