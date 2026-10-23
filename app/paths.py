"""Centralized paths for development and PyInstaller onedir builds.

Read-only resources (such as the bundled CSV and icon) may live under
PyInstaller's bundle directory, while writable files (model, settings,
history, logs) stay beside the executable in frozen builds.
"""
from __future__ import annotations

import sys
from pathlib import Path

DATASET_FILENAME = "Telco-Customer-Churn.csv"
IS_FROZEN = bool(getattr(sys, "frozen", False))

if IS_FROZEN:
    # Stable, writable location beside the executable.
    PROJECT_ROOT = Path(sys.executable).resolve().parent
    # For PyInstaller onedir, this is commonly the _internal directory.
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT)).resolve()
else:
    # app/paths.py -> project root
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    BUNDLE_ROOT = PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"
LOG_DIR = PROJECT_ROOT / "logs"
ASSET_DIR = BUNDLE_ROOT / "assets"


def resource_path(relative_path: str | Path) -> Path:
    """Resolve a bundled resource in both source and frozen execution.

    Bundle resources are preferred, then the sibling-project location. The
    final returned path is deterministic even if the resource is missing, so
    callers can report a useful diagnostic.
    """
    relative = Path(relative_path)
    candidates = (BUNDLE_ROOT / relative, PROJECT_ROOT / relative)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def dataset_candidates(
    *,
    executable_dir: Path | str | None = None,
    bundle_root: Path | str | None = None,
    working_dir: Path | str | None = None,
) -> list[Path]:
    """Return unique plausible CSV locations in priority order.

    1. `data/` beside the EXE/project (allows replacing the dataset).
    2. `data/` bundled by PyInstaller (often inside `_internal`).
    3. `data/` under the current working directory (for shortcut launches).
    """
    exe_root = Path(executable_dir).resolve() if executable_dir else PROJECT_ROOT
    bundle = Path(bundle_root).resolve() if bundle_root else BUNDLE_ROOT
    cwd = Path(working_dir).resolve() if working_dir else Path.cwd().resolve()

    candidates = [
        exe_root / "data" / DATASET_FILENAME,
        bundle / "data" / DATASET_FILENAME,
        cwd / "data" / DATASET_FILENAME,
    ]

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate.resolve()).casefold()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(candidate)
    return unique


def resolve_dataset_path(
    *,
    executable_dir: Path | str | None = None,
    bundle_root: Path | str | None = None,
    working_dir: Path | str | None = None,
) -> Path:
    """Return the first existing CSV path, or the external expected path.

    Returning the external path as a fallback means that if a user adds the
    CSV after startup, the existing ModelService can still find that file
    without needing a process restart.
    """
    candidates = dataset_candidates(
        executable_dir=executable_dir,
        bundle_root=bundle_root,
        working_dir=working_dir,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


DATASET_CANDIDATES = dataset_candidates()
DATASET_PATH = resolve_dataset_path()
MODEL_PATH = MODEL_DIR / "churn_pipeline.joblib"
MODEL_METADATA_PATH = MODEL_DIR / "model_metadata.json"
HISTORY_DB_PATH = DATA_DIR / "prediction_history.sqlite3"
SETTINGS_PATH = DATA_DIR / "settings.json"
LOG_PATH = LOG_DIR / "app.log"

# These directories contain writable state. Do not write model/history/settings
# under sys._MEIPASS because that location may be temporary or read-only.
for _directory in (DATA_DIR, MODEL_DIR, LOG_DIR):
    _directory.mkdir(parents=True, exist_ok=True)
