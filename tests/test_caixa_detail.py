from __future__ import annotations

from caixa_scanner.schemas import PropertyIn
from caixa_scanner.sources.caixa_detail import CaixaDetailSource, parse_fgts, parse_financing


class DummyResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_parse_fgts_and_financing_cover_positive_negative_and_unknown():
    assert parse_fgts("Aceita FGTS e financiamento") is True
    assert parse_fgts("Não aceita FGTS") is False
    assert parse_fgts("sem informação relevante") is None

    assert parse_financing("Aceita financiamento bancário") is True
    assert parse_financing("Não aceita financiamento") is False
    assert parse_financing("sem informação relevante") is None


def test_enrich_extracts_urls_sections_and_flags(monkeypatch):
    html = """
    <html>
      <body>
        <div>FORMAS DE PAGAMENTO ACEITAS: À vista e financiamento Baixar edital</div>
        <div>REGRAS PARA PAGAMENTO DAS DESPESAS: Condomínio por conta do comprador Topo</div>
        <div>Aceita FGTS e financiamento</div>
        <a href="/editais/123.pdf">Baixar edital</a>
        <a href="/docs/matricula.pdf">Matrícula do imóvel</a>
      </body>
    </html>
    """
    source = CaixaDetailSource()
    monkeypatch.setattr(source.session, "get", lambda *args, **kwargs: DummyResponse(html))

    item = PropertyIn(
        property_code="123",
        detail_url="https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=123",
        description="Apartamento com 2 quartos e 1 vaga",
    )

    enriched = source.enrich(item)

    assert enriched.accepts_fgts is True
    assert enriched.accepts_financing is True
    assert enriched.edital_url == "https://venda-imoveis.caixa.gov.br/editais/123.pdf"
    assert enriched.matricula_url == "https://venda-imoveis.caixa.gov.br/docs/matricula.pdf"
    assert enriched.payment_rules == "À vista e financiamento"
    assert enriched.expense_rules == "Condomínio por conta do comprador"


def test_enrich_infers_area_bedrooms_and_parking_when_missing(monkeypatch):
    html = "<html><body>Casa com 85 m2, 3 quartos e 2 vagas</body></html>"
    source = CaixaDetailSource()
    monkeypatch.setattr(source.session, "get", lambda *args, **kwargs: DummyResponse(html))

    item = PropertyIn(
        property_code="456",
        detail_url="https://example.com/imovel/456",
        description="Casa com 85 m2, 3 quartos e 2 vagas",
    )

    enriched = source.enrich(item)

    assert enriched.private_area_m2 == 85.0
    assert enriched.bedrooms == 3
    assert enriched.parking_spots == 2
