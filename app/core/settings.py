"""Small JSON-backed settings store."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SettingsStore:
    DEFAULTS: dict[str, Any] = {"theme": "dark"}

    def __init__(self, path: Path) -> None:
        self.path = path
        self._values = dict(self.DEFAULTS)
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                theme = loaded.get("theme")
                if theme in {"dark", "light"}:
                    self._values["theme"] = theme
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load settings: %s", exc)

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key == "theme" and value not in {"dark", "light"}:
            raise ValueError("Theme must be 'dark' or 'light'.")
        self._values[key] = value
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            temporary.write_text(
                json.dumps(self._values, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary.replace(self.path)
        except OSError:
            logger.exception("Could not save application settings")
