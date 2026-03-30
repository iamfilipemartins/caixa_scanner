from __future__ import annotations

import logging

from caixa_scanner.config import settings
from caixa_scanner.telegram import TelegramNotifier

from .database import SessionLocal, init_db
from .repository import PropertyRepository
from .schemas import PropertyIn
from .sources.caixa_csv import CaixaCsvSource
from .sources.caixa_detail import CaixaDetailSource
from .sources.caixa_edital import CaixaEditalSource
from .valuation.scoring import OpportunityScorer
from .valuation.scoring_moradia import build_moradia_scores


logger = logging.getLogger(__name__)


class CaixaScannerPipeline:
    def __init__(self) -> None:
        self.csv_source = CaixaCsvSource()
        self.detail_source = CaixaDetailSource()
        self.edital_source = CaixaEditalSource()
        self.scorer = OpportunityScorer()
        self.alerter = TelegramNotifier()

    def scan(self, ufs: list[str]) -> int:
        init_db()
        base_items = self.csv_source.fetch_many(ufs)
        enriched_items: list[PropertyIn] = []

        for item in base_items:
            try:
                enriched = self.detail_source.enrich(item)
            except Exception as exc:
                logger.warning(
                    "Failed to enrich property %s: %s",
                    item.property_code,
                    exc,
                )
                enriched = item

            try:
                enriched = self.edital_source.enrich(enriched)
            except Exception as exc:
                logger.warning(
                    "Failed to parse edital for property %s: %s",
                    enriched.property_code,
                    exc,
                )

            result = self.scorer.score(enriched)
            enriched_items.append(
                enriched.model_copy(
                    update={
                        "opportunity_score": result.score,
                        "score_reason": result.reason,
                    }
                )
            )

        with SessionLocal() as session:
            repo = PropertyRepository(session)
            return repo.upsert_many(enriched_items)

    def download_csvs(self, ufs: list[str], output_dir: str) -> list[str]:
        downloaded_files: list[str] = []

        for uf in ufs:
            try:
                file_path = self.csv_source.download_csv_for_uf(uf, output_dir)
                downloaded_files.append(file_path)
            except Exception as exc:
                logger.error("Download failed for UF=%s: %s", uf, exc)

        return downloaded_files

    def import_csv(self, file_path: str) -> int:
        init_db()
        base_items = self.csv_source.fetch_properties_from_csv_file(file_path)
        scored_items = [build_moradia_scores(item) for item in base_items]

        with SessionLocal() as session:
            repo = PropertyRepository(session)
            saved = repo.upsert_many(scored_items)

        return saved

    def import_csv_batch(self, file_paths: list[str]) -> int:
        init_db()
        all_items: list[PropertyIn] = []

        for file_path in file_paths:
            logger.info("Importing CSV file in batch: %s", file_path)
            items = self.csv_source.fetch_properties_from_csv_file(file_path)
            all_items.extend(items)

        unique_items: dict[str, PropertyIn] = {}
        for item in all_items:
            unique_items[item.property_code] = item

        deduped_items = list(unique_items.values())
        scored_items = [build_moradia_scores(item) for item in deduped_items]

        with SessionLocal() as session:
            repo = PropertyRepository(session)
            saved = repo.upsert_many(scored_items)

        return saved

    def download_and_import_csvs(self, ufs: list[str], output_dir: str) -> int:
        files = self.download_csvs(ufs, output_dir)
        if not files:
            return 0
        return self.import_csv_batch(files)

    def send_alerts(
        self,
        min_score: float | None = None,
        cities: list[str] | None = None,
        limit: int = 50,
    ) -> int:
        init_db()

        effective_score = min_score if min_score is not None else settings.alert_min_score
        effective_cities = cities if cities is not None else list(settings.alert_cities)

        with SessionLocal() as session:
            repo = PropertyRepository(session)
            candidates = repo.list_alert_candidates(
                min_score=effective_score,
                cities=effective_cities,
                limit=limit,
            )

            if not candidates:
                logger.info("No eligible properties found for alert sending.")
                return 0

            sent_ids: list[int] = []

            for item in candidates:
                try:
                    text = self.alerter.build_property_message(item)
                    ok = self.alerter.send_message(text)
                    if ok:
                        sent_ids.append(item.id)
                        logger.info(
                            "Alert sent for property %s (%s/%s)",
                            item.property_code,
                            item.city,
                            item.uf,
                        )
                    else:
                        logger.warning("Alert sending failed for property %s", item.property_code)
                except Exception as exc:
                    logger.error("Error sending alert for property %s: %s", item.property_code, exc)

            if sent_ids:
                repo.mark_alert_sent(sent_ids)

            return len(sent_ids)
