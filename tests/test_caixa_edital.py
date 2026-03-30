from __future__ import annotations

from caixa_scanner.schemas import PropertyIn
from caixa_scanner.sources.caixa_edital import CaixaEditalSource, parse_edital_text


class DummyPdfResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


def test_parse_edital_text_extracts_mode_date_payment_risks_and_flags():
    parsed = parse_edital_text(
        """
        Licitacao aberta. Data do leilao: 15/09/2026.
        Formas de pagamento: a vista, financiamento e FGTS.
        Imovel ocupado, sem visita, condominio e IPTU sob responsabilidade do comprador.
        Existe acao judicial em andamento.
        """
    )

    assert parsed.sale_mode == "Licitacao aberta"
    assert parsed.sale_date == "15/09/2026"
    assert parsed.payment_details == "a vista, financiamento e FGTS"
    assert parsed.has_occupied_risk is True
    assert parsed.has_no_visit_risk is True
    assert parsed.buyer_pays_condo is True
    assert parsed.buyer_pays_iptu is True
    assert parsed.has_judicial_risk is True
    assert "Imovel ocupado" in (parsed.risk_notes or "")
    assert "Despesas sob responsabilidade do comprador" in (parsed.risk_notes or "")


def test_enrich_updates_property_from_parsed_edital(monkeypatch):
    source = CaixaEditalSource()
    monkeypatch.setattr(source.session, "get", lambda *args, **kwargs: DummyPdfResponse(b"%PDF-1.4 fake"))
    monkeypatch.setattr(
        "caixa_scanner.sources.caixa_edital.extract_pdf_text",
        lambda content: (
            "Venda online. Sessao publica 20/10/2026. "
            "Formas de pagamento: somente a vista. "
            "Imovel ocupado e sem visita."
        ),
    )

    item = PropertyIn(
        property_code="123",
        edital_url="https://example.com/edital.pdf",
    )

    enriched = source.enrich(item)

    assert enriched.edital_sale_mode == "Venda online"
    assert enriched.edital_sale_date == "20/10/2026"
    assert enriched.edital_payment_details == "somente a vista"
    assert enriched.edital_risk_notes == "Imovel ocupado; Visitacao restrita"
    assert enriched.edital_has_occupied_risk is True
    assert enriched.edital_has_no_visit_risk is True
    assert enriched.edital_buyer_pays_condo is False
    assert enriched.edital_buyer_pays_iptu is False
    assert enriched.edital_has_judicial_risk is False
