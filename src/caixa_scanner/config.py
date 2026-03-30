from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from dotenv import load_dotenv


load_dotenv()

def str_to_bool(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in ("1", "true", "yes", "on")


def parse_csv_list(value: str | None, default: str = "") -> tuple[str, ...]:
    raw_value = value if value is not None else default
    return tuple(item.strip().upper() for item in raw_value.split(",") if item.strip())


@dataclass(slots=True)
class Settings:
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")
    telegram_enabled: bool = str_to_bool(os.getenv("TELEGRAM_ENABLED"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///caixa_scanner.db")
    default_ufs: tuple[str, ...] = parse_csv_list(os.getenv("DEFAULT_UFS"), "SP,MG,RJ")
    alert_min_score: float = float(os.getenv("ALERT_MIN_SCORE", "80"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    user_agent: str = os.getenv(
        "USER_AGENT", "Mozilla/5.0 (compatible; CaixaScanner/1.0)"
    )
    alert_cities: tuple[str, ...] = parse_csv_list(
        os.getenv("ALERT_CITIES"),
        "IPATINGA,BELO HORIZONTE",
    )

    def normalize_ufs(self, ufs: Iterable[str] | None) -> list[str]:
        if not ufs:
            return list(self.default_ufs)
        return [uf.strip().upper() for uf in ufs if uf.strip()]

    @property
    def telegram_available(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)


settings = Settings()
