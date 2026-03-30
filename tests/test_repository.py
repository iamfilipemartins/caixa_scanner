from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from caixa_scanner.database import Base
from caixa_scanner.models import Property
from caixa_scanner.repository import PropertyRepository


def build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def test_list_alert_candidates_filters_by_city_score_and_alert_status():
    session = build_session()
    session.add_all(
        [
            Property(
                property_code="A1",
                city="IPATINGA",
                uf="MG",
                score_moradia=85.0,
            ),
            Property(
                property_code="A2",
                city="IPATINGA",
                uf="MG",
                score_moradia=60.0,
            ),
            Property(
                property_code="A3",
                city="BELO HORIZONTE",
                uf="MG",
                score_moradia=90.0,
                last_alerted_at=datetime.utcnow(),
            ),
        ]
    )
    session.commit()

    repo = PropertyRepository(session)
    candidates = repo.list_alert_candidates(
        min_score=80.0,
        cities=["IPATINGA", "BELO HORIZONTE"],
        limit=10,
    )

    assert [item.property_code for item in candidates] == ["A1"]
