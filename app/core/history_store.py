"""SQLite persistence for compact prediction summaries.

The history intentionally stores only summary fields, not every customer input.
All values are local to the user's machine.
"""
from __future__ import annotations

import csv
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HistoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._initialize()
        except sqlite3.DatabaseError as exc:
            if not self.db_path.exists():
                raise
            backup = self.db_path.with_name(
                f"{self.db_path.name}.corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
            )
            try:
                os.replace(self.db_path, backup)
                for suffix in ("-wal", "-shm"):
                    sidecar = Path(str(self.db_path) + suffix)
                    if sidecar.exists():
                        os.replace(sidecar, Path(str(backup) + suffix))
                self._initialize()
                logger.error(
                    "Prediction history database was corrupt and has been preserved as %s: %s",
                    backup, exc,
                )
            except OSError:
                logger.exception("Could not preserve/recreate corrupt prediction history database")
                raise sqlite3.DatabaseError(
                    f"Prediction history database is corrupt and could not be recovered. Original backup location: {backup}"
                ) from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS prediction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    predicted_label TEXT NOT NULL CHECK(predicted_label IN ('Yes', 'No')),
                    churn_probability REAL NOT NULL CHECK(churn_probability >= 0 AND churn_probability <= 100),
                    tenure INTEGER NOT NULL,
                    contract TEXT NOT NULL,
                    monthly_charges REAL NOT NULL,
                    internet_service TEXT NOT NULL,
                    payment_method TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_created_at ON prediction_history(created_at DESC)"
            )

    def add_prediction(
        self,
        *,
        predicted_label: str,
        churn_probability: float,
        tenure: int,
        contract: str,
        monthly_charges: float,
        internet_service: str,
        payment_method: str,
        created_at: str | None = None,
    ) -> int:
        if predicted_label not in {"Yes", "No"}:
            raise ValueError("predicted_label must be 'Yes' or 'No'.")
        if not 0 <= float(churn_probability) <= 100:
            raise ValueError("churn_probability must be between 0 and 100.")
        created_at = created_at or datetime.now().astimezone().isoformat(timespec="seconds")
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO prediction_history (
                    created_at, predicted_label, churn_probability, tenure,
                    contract, monthly_charges, internet_service, payment_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    predicted_label,
                    float(churn_probability),
                    int(tenure),
                    str(contract),
                    float(monthly_charges),
                    str(internet_service),
                    str(payment_method),
                ),
            )
            return int(cursor.lastrowid)

    def list_predictions(self, search: str = "", limit: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM prediction_history"
        parameters: list[Any] = []
        if search.strip():
            term = f"%{search.strip()}%"
            query += " WHERE predicted_label LIKE ? OR contract LIKE ? OR internet_service LIKE ? OR payment_method LIKE ? OR created_at LIKE ?"
            parameters.extend([term, term, term, term, term])
        query += " ORDER BY id DESC"
        if limit is not None:
            if limit < 1:
                return []
            query += " LIMIT ?"
            parameters.append(int(limit))
        with self._connection() as connection:
            return [dict(row) for row in connection.execute(query, parameters).fetchall()]

    def summary(self) -> dict[str, float | int]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN predicted_label = 'Yes' THEN 1 ELSE 0 END) AS flagged,
                       AVG(churn_probability) AS average_probability
                FROM prediction_history
                """
            ).fetchone()
        return {
            "total": int(row["total"] or 0),
            "flagged": int(row["flagged"] or 0),
            "average_probability": float(row["average_probability"] or 0.0),
        }

    def delete_ids(self, ids: list[int]) -> int:
        safe_ids = sorted({int(item) for item in ids if int(item) > 0})
        if not safe_ids:
            return 0
        placeholders = ",".join("?" for _ in safe_ids)
        with self._connection() as connection:
            cursor = connection.execute(
                f"DELETE FROM prediction_history WHERE id IN ({placeholders})",
                safe_ids,
            )
            return int(cursor.rowcount)

    def clear(self) -> int:
        with self._connection() as connection:
            count = int(connection.execute("SELECT COUNT(*) FROM prediction_history").fetchone()[0])
            connection.execute("DELETE FROM prediction_history")
            return count

    def export_csv(self, destination: Path, search: str = "") -> int:
        rows = self.list_predictions(search=search)
        fields = [
            "id", "created_at", "predicted_label", "churn_probability", "tenure",
            "contract", "monthly_charges", "internet_service", "payment_method",
        ]
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8-sig") as file_handle:
            writer = csv.DictWriter(file_handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return len(rows)
