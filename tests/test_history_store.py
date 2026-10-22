from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from app.core.history_store import HistoryStore


class HistoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = HistoryStore(self.root / "history.sqlite3")

    def add_one(self, **overrides):
        values = {
            "predicted_label": "Yes",
            "churn_probability": 72.5,
            "tenure": 4,
            "contract": "Month-to-month",
            "monthly_charges": 85.2,
            "internet_service": "Fiber optic",
            "payment_method": "Electronic check",
            "created_at": "2026-10-22T10:00:00+02:00",
        }
        values.update(overrides)
        return self.store.add_prediction(**values)

    def test_add_list_and_summary(self):
        self.add_one()
        self.add_one(predicted_label="No", churn_probability=22.0, contract="Two year")
        rows = self.store.list_predictions()
        summary = self.store.summary()
        self.assertEqual(len(rows), 2)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["flagged"], 1)
        self.assertAlmostEqual(summary["average_probability"], 47.25)

    def test_search_filters_history(self):
        self.add_one()
        self.add_one(predicted_label="No", churn_probability=12.0, contract="Two year")
        self.assertEqual(len(self.store.list_predictions(search="Two year")), 1)
        self.assertEqual(len(self.store.list_predictions(search="Yes")), 1)

    def test_delete_selected_and_clear(self):
        first = self.add_one()
        self.add_one(predicted_label="No", churn_probability=25.0)
        self.assertEqual(self.store.delete_ids([first]), 1)
        self.assertEqual(len(self.store.list_predictions()), 1)
        self.assertEqual(self.store.clear(), 1)
        self.assertEqual(len(self.store.list_predictions()), 0)

    def test_export_csv(self):
        self.add_one()
        destination = self.root / "export.csv"
        count = self.store.export_csv(destination)
        self.assertEqual(count, 1)
        with destination.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["predicted_label"], "Yes")

    def test_rejects_invalid_label(self):
        with self.assertRaises(ValueError):
            self.add_one(predicted_label="Maybe")

    def test_corrupt_database_is_preserved_and_recreated(self):
        self.store.db_path.write_bytes(b"not a sqlite database")
        recovered = HistoryStore(self.store.db_path)
        backups = list(self.root.glob("history.sqlite3.corrupt-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), b"not a sqlite database")
        self.assertEqual(recovered.summary()["total"], 0)


if __name__ == "__main__":
    unittest.main()
