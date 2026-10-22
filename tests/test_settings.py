from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.core.settings import SettingsStore


class SettingsTests(unittest.TestCase):
    def test_theme_persists_between_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            first = SettingsStore(path)
            first.set("theme", "light")
            second = SettingsStore(path)
            self.assertEqual(second.get("theme"), "light")

    def test_invalid_theme_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            with self.assertRaises(ValueError):
                store.set("theme", "neon")


if __name__ == "__main__":
    unittest.main()
