from __future__ import annotations

from datetime import datetime

from caixa_scanner.pipeline import CaixaScannerPipeline
from caixa_scanner.schemas import PropertyIn


class DummyRepo:
    def __init__(self) -> None:
        self.saved_items = None
        self.reprocess_candidates = []

    def upsert_many(self, items):
        self.saved_items = list(items)
        return len(self.saved_items)

    def list_reprocess_candidates(self, limit=100, pending_only=True, scoring_version=None):
        self.last_reprocess_args = (limit, pending_only, scoring_version)
        return self.reprocess_candidates


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
    fake_now = datetime(2026, 3, 30, 12, 0, 0)

    monkeypatch.setattr("caixa_scanner.pipeline.init_db", lambda: None)
    monkeypatch.setattr("caixa_scanner.pipeline.SessionLocal", lambda: session_ctx)
    monkeypatch.setattr("caixa_scanner.pipeline.PropertyRepository", lambda session: session.repo)
    monkeypatch.setattr(CaixaScannerPipeline, "_utcnow", staticmethod(lambda: fake_now))

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
    assert saved_item.imported_at == fake_now
    assert saved_item.detail_enriched_at is None
    assert saved_item.edital_enriched_at == fake_now
    assert saved_item.scored_at == fake_now
    assert saved_item.scoring_version == "moradia-v1-edital-flags"


def test_reprocess_only_updates_pending_steps(monkeypatch):
    fake_now = datetime(2026, 3, 30, 13, 0, 0)
    session_ctx = DummySessionContext()
    session_ctx.repo.reprocess_candidates = [
        type(
            "PropertyRow",
            (),
            {
                column: value
                for column, value in {
                    "id": 1,
                    "property_code": "123",
                    "uf": "MG",
                    "city": "Belo Horizonte",
                    "neighborhood": "Savassi",
                    "address": "Rua A 10",
                    "price": 100000.0,
                    "appraisal_value": 200000.0,
                    "discount_pct": 50.0,
                    "description": "Apartamento",
                    "detail_url": "https://example.com/detail",
                    "edital_url": "https://example.com/edital.pdf",
                    "detail_enriched_at": None,
                    "edital_enriched_at": None,
                    "scored_at": None,
                    "scoring_version": None,
                    "imported_at": fake_now,
                }.items()
            },
        )()
    ]

    monkeypatch.setattr("caixa_scanner.pipeline.init_db", lambda: None)
    monkeypatch.setattr("caixa_scanner.pipeline.SessionLocal", lambda: session_ctx)
    monkeypatch.setattr("caixa_scanner.pipeline.PropertyRepository", lambda session: session.repo)
    monkeypatch.setattr(CaixaScannerPipeline, "_utcnow", staticmethod(lambda: fake_now))

    pipeline = CaixaScannerPipeline()
    monkeypatch.setattr(
        pipeline.detail_source,
        "enrich",
        lambda item: item.model_copy(update={"description": "Apartamento atualizado"}),
    )
    monkeypatch.setattr(
        pipeline.edital_source,
        "enrich",
        lambda item: item.model_copy(update={"edital_sale_mode": "Venda online"}),
    )

    total = pipeline.reprocess(limit=10, pending_only=True, rescore_only=False)

    assert total == 1
    assert session_ctx.repo.last_reprocess_args == (10, True, "moradia-v1-edital-flags")
    saved_item = session_ctx.repo.saved_items[0]
    assert saved_item.detail_enriched_at == fake_now
    assert saved_item.edital_enriched_at == fake_now
    assert saved_item.scored_at == fake_now
    assert saved_item.scoring_version == "moradia-v1-edital-flags"
    assert saved_item.edital_sale_mode == "Venda online"
