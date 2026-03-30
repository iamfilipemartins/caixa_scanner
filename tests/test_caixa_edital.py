from __future__ import annotations

from caixa_scanner.schemas import PropertyIn
from caixa_scanner.sources.caixa_edital import CaixaEditalSource, EditalInfo, parse_edital_text


class DummyPdfResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


def test_parse_edital_text_extracts_mode_date_payment_and_risks():
    parsed = parse_edital_text(
        """
        Licitação aberta. Data do leilão: 15/09/2026.
        Formas de pagamento: à vista, financiamento e FGTS.
        Imóvel ocupado e condomínio sob responsabilidade do comprador.
        """
    )

    assert parsed.sale_mode == "Licitação aberta"
    assert parsed.sale_date == "15/09/2026"
    assert parsed.payment_details == "à vista, financiamento e FGTS"
    assert "Imóvel ocupado" in parsed.risk_notes
    assert "Despesas sob responsabilidade do comprador" in parsed.risk_notes


def test_enrich_updates_property_from_parsed_edital(monkeypatch):
    source = CaixaEditalSource()
    monkeypatch.setattr(source.session, "get", lambda *args, **kwargs: DummyPdfResponse(b"%PDF-1.4 fake"))
    monkeypatch.setattr(
        "caixa_scanner.sources.caixa_edital.extract_pdf_text",
        lambda content: "Venda online. Sessão pública 20/10/2026. Formas de pagamento: somente à vista. Imóvel ocupado.",
    )

    item = PropertyIn(
        property_code="123",
        edital_url="https://example.com/edital.pdf",
    )

    enriched = source.enrich(item)

    assert enriched.edital_sale_mode == "Venda online"
    assert enriched.edital_sale_date == "20/10/2026"
    assert enriched.edital_payment_details == "somente à vista"
    assert enriched.edital_risk_notes == "Imóvel ocupado"
