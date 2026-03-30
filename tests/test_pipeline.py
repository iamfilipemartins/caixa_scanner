from __future__ import annotations

from caixa_scanner.pipeline import CaixaScannerPipeline
from caixa_scanner.schemas import PropertyIn


class DummyRepo:
    def __init__(self) -> None:
        self.saved_items = None

    def upsert_many(self, items):
        self.saved_items = list(items)
        return len(self.saved_items)


class DummySessionContext:
    def __init__(self) -> None:
        self.repo = DummyRepo()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_scan_uses_property_contract_and_falls_back_when_detail_enrichment_fails(monkeypatch):
    property_item = PropertyIn(
        property_code="123",
        uf="MG",
        city="Belo Horizonte",
        neighborhood="Savassi",
        address="Rua A 10",
        price=100000.0,
        appraisal_value=200000.0,
        discount_pct=50.0,
        description="Apartamento",
    )
    session_ctx = DummySessionContext()

    monkeypatch.setattr("caixa_scanner.pipeline.init_db", lambda: None)
    monkeypatch.setattr("caixa_scanner.pipeline.SessionLocal", lambda: session_ctx)
    monkeypatch.setattr("caixa_scanner.pipeline.PropertyRepository", lambda session: session.repo)

    pipeline = CaixaScannerPipeline()
    monkeypatch.setattr(pipeline.csv_source, "fetch_many", lambda ufs: [property_item])
    monkeypatch.setattr(pipeline.edital_source, "enrich", lambda item: item)

    def raise_on_enrich(item):
        raise RuntimeError("detail unavailable")

    monkeypatch.setattr(pipeline.detail_source, "enrich", raise_on_enrich)

    total = pipeline.scan(["MG"])

    assert total == 1
    assert session_ctx.repo.saved_items is not None
    saved_item = session_ctx.repo.saved_items[0]
    assert isinstance(saved_item, PropertyIn)
    assert saved_item.property_code == "123"
    assert saved_item.opportunity_score is not None
    assert saved_item.score_reason
