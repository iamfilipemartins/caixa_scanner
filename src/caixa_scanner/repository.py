from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .models import Property
from .schemas import PropertyIn


class PropertyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(self, items: Iterable[PropertyIn]) -> int:
        count = 0
        for item in items:
            self.upsert(item)
            count += 1
        self.session.commit()
        return count

    def upsert(self, item: PropertyIn) -> Property:
        existing = self.session.scalar(
            select(Property).where(Property.property_code == item.property_code)
        )
        payload = item.model_dump()
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            obj = existing
        else:
            obj = Property(**payload)
            self.session.add(obj)
        return obj

    def top_opportunities(self, limit: int = 20) -> list[Property]:
        stmt = (
            select(Property)
            .where(Property.opportunity_score.is_not(None))
            .order_by(Property.opportunity_score.desc(), Property.discount_pct.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def pending_alerts(self, min_score: float) -> list[Property]:
        stmt = (
            select(Property)
            .where(Property.opportunity_score >= min_score)
            .where(Property.last_alerted_at.is_(None))
            .order_by(Property.opportunity_score.desc())
        )
        return list(self.session.scalars(stmt))

    def mark_alerted(self, properties: Iterable[Property]) -> None:
        now = datetime.utcnow()
        for item in properties:
            item.last_alerted_at = now
        self.session.commit()

    def list_alert_candidates(self, min_score: float, cities: list[str], limit: int = 50) -> list[Property]:
        normalized_cities = [c.strip().upper() for c in cities if c and c.strip()]

        stmt = (
            select(Property)
            .where(Property.score_moradia.is_not(None))
            .where(Property.score_moradia >= min_score)
            .where(Property.city.in_(normalized_cities))
            .where(Property.last_alerted_at.is_(None))
            .order_by(Property.score_moradia.desc())
            .limit(limit)
        )

        return list(self.session.execute(stmt).scalars().all())

    def mark_alert_sent(self, property_ids: list[int]) -> int:
        if not property_ids:
            return 0

        now = datetime.utcnow()
        stmt = select(Property).where(Property.id.in_(property_ids))
        items = list(self.session.execute(stmt).scalars().all())

        for item in items:
            item.last_alerted_at = now

        self.session.commit()
        return len(items)

    def list_reprocess_candidates(
        self,
        limit: int = 100,
        pending_only: bool = True,
        scoring_version: str | None = None,
    ) -> list[Property]:
        stmt = select(Property).order_by(Property.updated_at.desc()).limit(limit)

        if pending_only:
            conditions = [
                Property.detail_enriched_at.is_(None),
                Property.edital_enriched_at.is_(None),
                Property.scored_at.is_(None),
            ]
            if scoring_version:
                conditions.append(Property.scoring_version.is_(None))
                conditions.append(Property.scoring_version != scoring_version)
            stmt = stmt.where(or_(*conditions))

        return list(self.session.scalars(stmt))
