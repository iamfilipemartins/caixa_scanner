from caixa_scanner.valuation.location_scoring import (
    municipality_structure_score,
    neighborhood_structure_score,
)
from caixa_scanner.sources.caixa_csv import normalize_text
import re

def clean_neighborhood_name(neighborhood: str | None) -> str:
    if not neighborhood:
        return ""

    n = neighborhood.upper()

    # remove cidade/UF que vem junto
    if " - " in n:
        n = n.split(" - ")[0]

    return normalize_text(n)

def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))

def calc_score_preco(item) -> float:
    score = 0.0

    if item.discount_pct is not None:
        if item.discount_pct >= 50:
            score += 95
        elif item.discount_pct >= 40:
            score += 85
        elif item.discount_pct >= 30:
            score += 70
        elif item.discount_pct >= 20:
            score += 55
        else:
            score += 35

    if item.price is not None and item.appraisal_value is not None:
        if item.price <= item.appraisal_value:
            score += 5
        else:
            score -= 20

    return clamp(score / 1.0)

def calc_score_imovel(item) -> float:
    score = 42.0

    ptype = normalize_text(item.property_type or "")
    area = item.private_area_m2
    bedrooms = item.bedrooms
    parking = item.parking_spots
    bathrooms = item.bathrooms

    # Tipo
    if "apartamento" in ptype:
        score += 8
    elif "casa" in ptype or "sobrado" in ptype:
        score += 10
    elif "terreno" in ptype or "comercial" in ptype:
        score -= 18
    else:
        score -= 4

    # Área para moradia: 51 m² é boa, mas não excepcional
    if area is not None:
        if 60 <= area <= 110:
            score += 10
        elif 45 <= area < 60:
            score += 3
        elif 110 < area <= 160:
            score += 15
        elif 35 <= area < 45:
            score -= 6
        elif area < 35:
            score -= 12
        else:
            score -= 4
    else:
        score -= 10

    # Quartos
    if bedrooms is not None:
        if bedrooms == 2:
            score += 14
        elif bedrooms == 3:
            score += 16
        elif bedrooms == 1:
            score += 4
        elif bedrooms >= 4:
            score += 8
    else:
        score -= 6

    # Vagas
    if parking is not None:
        if parking >= 1:
            score += 8
        else:
            score -= 6
    else:
        score -= 3

    # Banheiros
    if bathrooms is not None:
        if bathrooms >= 2:
            score += 4

    return clamp(score, 0.0, 92.0)

def calc_score_municipio(item) -> float:
    return clamp(municipality_structure_score(item.city, item.uf))

def calc_score_bairro(item) -> float:
    neighborhood = normalize_text(item.neighborhood or "")
    if not neighborhood:
        return 35.0

    clean_neighborhood = clean_neighborhood_name(item.neighborhood)

    mapped_score = neighborhood_structure_score(item.city, clean_neighborhood, item.uf)
    if mapped_score is not None:
        return clamp(mapped_score)

    score = 58.0

    generic_terms = [
        "zona rural",
        "area rural",
        "povoado",
        "sitio",
        "fazenda",
        "chacara",
    ]

    if any(term in neighborhood for term in generic_terms):
        score -= 18

    if neighborhood == "centro":
        score += 4

    if len(neighborhood) >= 4:
        score += 4

    return clamp(score)

def calc_score_endereco(item) -> float:
    address = normalize_text(item.address or "")

    if not address:
        return 25.0

    score = 55.0

    # endereço com logradouro claro
    if any(token in address for token in ["rua", "avenida", "av ", "alameda", "travessa", "rodovia", "estrada"]):
        score += 20

    # número ajuda bastante
    if " n. " in f" {address} " or " numero " in address or re.search(r"\b\d+\b", address):
        score += 10

    # apto/casa/bloco/lote ajudam na especificidade
    if any(token in address for token in ["apto", "apartamento", "bloco", "casa", "lote", "qd", "quadra", "lt"]):
        score += 8

    return clamp(score)

def calc_score_completude_localizacao(item) -> float:
    score = 40.0

    if item.city:
        score += 20
    if item.neighborhood:
        score += 20
    if item.address:
        score += 20

    return clamp(score)

def calc_score_localizacao(item) -> float:
    score_municipio = calc_score_municipio(item)
    score_bairro = calc_score_bairro(item)
    score_endereco = calc_score_endereco(item)
    score_completude = calc_score_completude_localizacao(item)

    score = (
        0.35 * score_municipio +
        0.40 * score_bairro +
        0.15 * score_endereco +
        0.10 * score_completude
    )

    return clamp(score)

def calc_score_liquidez_residencial(item) -> float:
    score = 45.0

    ptype = normalize_text(item.property_type or "")
    area = item.private_area_m2
    bedrooms = item.bedrooms

    if "apartamento" in ptype:
        score += 10
    elif "casa" in ptype or "sobrado" in ptype:
        score += 8
    elif "terreno" in ptype or "comercial" in ptype:
        score -= 18

    if area is not None:
        if 50 <= area <= 90:
            score += 16
        elif 90 < area <= 140:
            score += 10
        elif 40 <= area < 50:
            score += 7
        elif area < 35:
            score -= 12
        elif area > 200:
            score -= 10

    if bedrooms is not None:
        if bedrooms == 2:
            score += 12
        elif bedrooms == 3:
            score += 14
        elif bedrooms == 1:
            score += 3
        elif bedrooms >= 4:
            score += 5

    return clamp(score, 0.0, 90.0)

def calc_score_risco(item) -> float:
    score = 85.0

    if not item.description:
        score -= 20

    if item.discount_pct == 0:
        score -= 15

    if item.price is not None and item.appraisal_value is not None:
        if item.price > item.appraisal_value:
            score -= 20

    if not item.neighborhood:
        score -= 10

    if not item.address:
        score -= 15

    return clamp(score)


def build_moradia_scores(item):
    score_preco = calc_score_preco(item)
    score_imovel = calc_score_imovel(item)
    score_localizacao = calc_score_localizacao(item)
    score_liquidez = calc_score_liquidez_residencial(item)
    score_risco = calc_score_risco(item)

    score_final = (
        0.20 * score_preco +
        0.15 * score_imovel +
        0.45 * score_localizacao +
        0.10 * score_liquidez +
        0.10 * score_risco
    )

    # Penalização forte para localização ruim
    if score_localizacao < 75:
        score_final *= 0.75

    if score_localizacao < 65:
        score_final *= 0.60

    if score_localizacao < 55:
        score_final *= 0.40

    # Teto por localização
    if score_localizacao < 75:
        score_final = min(score_final, 75)

    if score_localizacao < 65:
        score_final = min(score_final, 65)

    if score_localizacao < 55:
        score_final = min(score_final, 55)

    score_final = clamp(score_final)

    score_municipio = calc_score_municipio(item)
    score_bairro = calc_score_bairro(item)
    score_endereco = calc_score_endereco(item)

    reasons = [
        f"Preço {score_preco:.0f}",
        f"Imóvel {score_imovel:.0f}",
        f"Localização {score_localizacao:.0f} (município {score_municipio:.0f}, bairro {score_bairro:.0f}, endereço {score_endereco:.0f})",
        f"Liquidez residencial {score_liquidez:.0f}",
        f"Risco {score_risco:.0f}",
    ]

    item.score_preco = round(score_preco, 2)
    item.score_imovel = round(score_imovel, 2)
    item.score_localizacao = round(score_localizacao, 2)
    item.score_liquidez_residencial = round(score_liquidez, 2)
    item.score_risco = round(score_risco, 2)
    item.score_moradia = round(score_final, 2)
    item.score_moradia_reason = " | ".join(reasons)

    item.opportunity_score = item.score_moradia
    item.score_reason = item.score_moradia_reason

    return item
