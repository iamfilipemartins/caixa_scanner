from __future__ import annotations

from dataclasses import dataclass

from ..schemas import PropertyIn


RISK_TERMS = {
    "ocupado": -18,
    "invadido": -25,
    "sem visita": -8,
    "sem utilização de fgts": -4,
    "não aceita financiamento": -8,
    "sob responsabilidade do comprador": -5,
}


@dataclass(slots=True)
class ScoreResult:
    score: float
    reason: str


class OpportunityScorer:
    def score(self, item: PropertyIn) -> ScoreResult:
        score = 30.0
        reasons: list[str] = []

        if item.discount_pct is not None:
            if item.discount_pct >= 55:
                score += 28
                reasons.append(f"desconto muito alto ({item.discount_pct:.1f}%)")
            elif item.discount_pct >= 40:
                score += 20
                reasons.append(f"desconto alto ({item.discount_pct:.1f}%)")
            elif item.discount_pct >= 25:
                score += 10
                reasons.append(f"desconto razoável ({item.discount_pct:.1f}%)")

        if item.price and item.appraisal_value and item.price < item.appraisal_value:
            ratio = item.price / item.appraisal_value
            if ratio <= 0.65:
                score += 12
                reasons.append("preço bem abaixo da avaliação")
            elif ratio <= 0.80:
                score += 6
                reasons.append("preço abaixo da avaliação")

        if item.accepts_financing:
            score += 8
            reasons.append("aceita financiamento")
        if item.accepts_fgts:
            score += 6
            reasons.append("aceita FGTS")

        description = (item.description or "").lower()
        expense_rules = (item.expense_rules or "").lower()
        edital_risk_notes = (item.edital_risk_notes or "").lower()
        combined_text = f"{description} {expense_rules} {edital_risk_notes}"
        for term, delta in RISK_TERMS.items():
            if term in combined_text:
                score += delta
                reasons.append(f"penalização por risco: {term}")

        if any(word in description for word in ("apartamento", "casa", "sobrado")):
            score += 4
            reasons.append("tipologia residencial clara")

        if item.private_area_m2:
            if 38 <= item.private_area_m2 <= 90:
                score += 5
                reasons.append("metragem líquida comercialmente comum")
            elif item.private_area_m2 < 25:
                score -= 6
                reasons.append("metragem muito baixa")

        if item.bedrooms:
            score += min(item.bedrooms * 1.5, 4.5)
            reasons.append(f"{item.bedrooms} quarto(s)")

        if item.parking_spots:
            score += min(item.parking_spots * 2, 4)
            reasons.append("possui vaga")

        score = max(0, min(100, round(score, 1)))
        if not reasons:
            reasons.append("score base sem enriquecimento suficiente")
        return ScoreResult(score=score, reason="; ".join(reasons))
