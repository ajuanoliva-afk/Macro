from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Alert


class AlertStore:
    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                symbol TEXT NOT NULL,
                geo TEXT,
                operator TEXT NOT NULL CHECK (operator IN ('above', 'below')),
                threshold REAL NOT NULL,
                last_condition INTEGER,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()

    @staticmethod
    def _to_alert(row: sqlite3.Row) -> Alert:
        raw_condition = row["last_condition"]
        return Alert(
            id=row["id"],
            chat_id=row["chat_id"],
            provider=row["provider"],
            symbol=row["symbol"],
            geo=row["geo"],
            operator=row["operator"],
            threshold=row["threshold"],
            last_condition=None if raw_condition is None else bool(raw_condition),
            active=bool(row["active"]),
        )

    def add(
        self,
        chat_id: int,
        provider: str,
        symbol: str,
        geo: str | None,
        operator: str,
        threshold: float,
        last_condition: bool | None,
    ) -> Alert:
        cursor = self.connection.execute(
            """
            INSERT INTO alerts
                (chat_id, provider, symbol, geo, operator, threshold, last_condition)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                provider,
                symbol,
                geo,
                operator,
                threshold,
                None if last_condition is None else int(last_condition),
            ),
        )
        self.connection.commit()
        row = self.connection.execute(
            "SELECT * FROM alerts WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return self._to_alert(row)

    def list_for_chat(self, chat_id: int) -> list[Alert]:
        rows = self.connection.execute(
            "SELECT * FROM alerts WHERE chat_id = ? AND active = 1 ORDER BY id",
            (chat_id,),
        ).fetchall()
        return [self._to_alert(row) for row in rows]

    def list_active(self) -> list[Alert]:
        rows = self.connection.execute(
            "SELECT * FROM alerts WHERE active = 1 ORDER BY id"
        ).fetchall()
        return [self._to_alert(row) for row in rows]

    def delete(self, chat_id: int, alert_id: int) -> bool:
        cursor = self.connection.execute(
            "UPDATE alerts SET active = 0 WHERE id = ? AND chat_id = ? AND active = 1",
            (alert_id, chat_id),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def set_condition(self, alert_id: int, condition: bool) -> None:
        self.connection.execute(
            "UPDATE alerts SET last_condition = ? WHERE id = ?",
            (int(condition), alert_id),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

