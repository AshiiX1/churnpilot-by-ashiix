"""Application entry point.

Run `python main.py` to launch the desktop app or `python main.py --train`
for headless model training/evaluation.
"""
from __future__ import annotations

import argparse
import logging
import sys

from app.paths import LOG_PATH
from app.core.model_service import ModelService, ModelServiceError


def configure_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler(sys.stderr)],
    )


def train_model() -> int:
    service = ModelService()
    try:
        metrics = service.train()
    except ModelServiceError as exc:
        print(f"Training failed: {exc}", file=sys.stderr)
        return 1
    print("\nModel training completed and saved.")
    print(f"Dataset rows: {metrics['dataset_rows']}")
    print(f"Training rows: {metrics['training_rows']}")
    print(f"Testing rows: {metrics['testing_rows']}")
    print(f"Accuracy: {metrics['accuracy']:.2%}")
    print(f"Precision (Churn=Yes): {metrics['precision_yes']:.2%}")
    print(f"Recall (Churn=Yes): {metrics['recall_yes']:.2%}")
    print(f"F1 (Churn=Yes): {metrics['f1_yes']:.2%}")
    print(f"Model: {service.model_path}")
    print(f"Metadata: {service.metadata_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Customer Churn Predictor")
    parser.add_argument(
        "--train",
        action="store_true",
        help="Train and evaluate the model from data/Telco-Customer-Churn.csv, then exit.",
    )
    args = parser.parse_args()
    configure_logging()

    if args.train:
        return train_model()

    try:
        from app.ui.app import launch_app
        launch_app()
        return 0
    except ModuleNotFoundError as exc:
        if exc.name == "tkinter":
            print("Tkinter is not installed in this Python environment.", file=sys.stderr)
            print("On Windows, install/use Python from python.org with Tcl/Tk support.", file=sys.stderr)
            return 2
        raise


if __name__ == "__main__":
    raise SystemExit(main())
