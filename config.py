from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    fred_api_key: str
    database_path: Path
    allowed_chat_ids: frozenset[int]
    alert_poll_seconds: int
    http_timeout_seconds: float
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        fred_key = os.getenv("FRED_API_KEY", "").strip()
        missing = [
            name
            for name, value in (
                ("TELEGRAM_BOT_TOKEN", token),
                ("FRED_API_KEY", fred_key),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Faltan variables obligatorias: " + ", ".join(missing)
            )

        raw_ids = os.getenv("ALLOWED_CHAT_IDS", "").strip()
        allowed = frozenset(
            int(part.strip()) for part in raw_ids.split(",") if part.strip()
        )
        database_path = Path(
            os.getenv("DATABASE_PATH", "data/macrobot.sqlite3")
        ).expanduser()
        database_path.parent.mkdir(parents=True, exist_ok=True)

        return cls(
            telegram_bot_token=token,
            fred_api_key=fred_key,
            database_path=database_path,
            allowed_chat_ids=allowed,
            alert_poll_seconds=max(
                60, int(os.getenv("ALERT_POLL_SECONDS", "900"))
            ),
            http_timeout_seconds=float(
                os.getenv("HTTP_TIMEOUT_SECONDS", "25")
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )

