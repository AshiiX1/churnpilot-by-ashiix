"""Centralized application paths, independent of the current working directory.

When frozen with PyInstaller, writable data is stored beside the executable
(onedir distribution). For a normal Python run, paths live in the project root.
"""
from pathlib import Path
import sys

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"
LOG_DIR = PROJECT_ROOT / "logs"

DATASET_PATH = DATA_DIR / "Telco-Customer-Churn.csv"
MODEL_PATH = MODEL_DIR / "churn_pipeline.joblib"
MODEL_METADATA_PATH = MODEL_DIR / "model_metadata.json"
HISTORY_DB_PATH = DATA_DIR / "prediction_history.sqlite3"
SETTINGS_PATH = DATA_DIR / "settings.json"
LOG_PATH = LOG_DIR / "app.log"

for _directory in (DATA_DIR, MODEL_DIR, LOG_DIR):
    _directory.mkdir(parents=True, exist_ok=True)
