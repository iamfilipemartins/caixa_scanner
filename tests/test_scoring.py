from __future__ import annotations

from caixa_scanner.schemas import PropertyIn
from caixa_scanner.valuation.scoring import OpportunityScorer


def test_structured_edital_flags_reduce_opportunity_score():
    scorer = OpportunityScorer()
    base_item = PropertyIn(
        property_code="base",
        description="Apartamento residencial",
        discount_pct=30.0,
        price=200000.0,
        appraisal_value=300000.0,
        private_area_m2=65.0,
        bedrooms=2,
        parking_spots=1,
    )
    risky_item = base_item.model_copy(
        update={
            "property_code": "risky",
            "edital_has_occupied_risk": True,
            "edital_has_no_visit_risk": True,
            "edital_buyer_pays_condo": True,
            "edital_buyer_pays_iptu": True,
            "edital_has_judicial_risk": True,
        }
    )

    base_score = scorer.score(base_item)
    risky_score = scorer.score(risky_item)

    assert risky_score.score < base_score.score
    assert "risco estruturado: imovel ocupado" in risky_score.reason
    assert "risco estruturado: mencao judicial no edital" in risky_score.reason
