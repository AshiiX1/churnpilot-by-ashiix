"""Training, validation, persistence, and prediction for the churn model."""
from __future__ import annotations

import json
import logging
import math
import os
import platform
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.paths import (
    DATASET_CANDIDATES,
    DATASET_PATH,
    MODEL_METADATA_PATH,
    MODEL_PATH,
)

logger = logging.getLogger(__name__)

TARGET_COLUMN = "Churn"
DROP_COLUMNS = ("customerID",)
NUMERIC_FEATURES = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]
FEATURE_COLUMNS = [
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
]
CATEGORICAL_FEATURES = [name for name in FEATURE_COLUMNS if name not in NUMERIC_FEATURES]

FIELD_OPTIONS: dict[str, tuple[str, ...]] = {
    "gender": ("Female", "Male"),
    "Partner": ("Yes", "No"),
    "Dependents": ("Yes", "No"),
    "PhoneService": ("Yes", "No"),
    "MultipleLines": ("No phone service", "No", "Yes"),
    "InternetService": ("DSL", "Fiber optic", "No"),
    "OnlineSecurity": ("No internet service", "No", "Yes"),
    "OnlineBackup": ("No internet service", "No", "Yes"),
    "DeviceProtection": ("No internet service", "No", "Yes"),
    "TechSupport": ("No internet service", "No", "Yes"),
    "StreamingTV": ("No internet service", "No", "Yes"),
    "StreamingMovies": ("No internet service", "No", "Yes"),
    "Contract": ("Month-to-month", "One year", "Two year"),
    "PaperlessBilling": ("Yes", "No"),
    "PaymentMethod": (
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ),
}

INTERNET_DEPENDENT_FIELDS = (
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
)


class ModelServiceError(RuntimeError):
    """A user-actionable model or dataset error."""


@dataclass(frozen=True)
class PredictionResult:
    label: str
    churn_probability: float
    stay_probability: float

    @property
    def risk_band(self) -> str:
        if self.churn_probability >= 65:
            return "High"
        if self.churn_probability >= 35:
            return "Moderate"
        return "Lower"


class ModelService:
    def __init__(
        self,
        dataset_path: Path | None = None,
        model_path: Path = MODEL_PATH,
        metadata_path: Path = MODEL_METADATA_PATH,
    ) -> None:
        # When no path is supplied, use the packaged/runtime-aware resolver.
        # Explicit paths stay explicit, which keeps tests and embedding callers
        # deterministic and avoids accidentally training on another dataset.
        self._use_default_dataset_lookup = dataset_path is None
        self.dataset_path = Path(dataset_path) if dataset_path is not None else Path(DATASET_PATH)
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path)
        self.model: Pipeline | None = None
        self.metadata: dict[str, Any] = {}

    @staticmethod
    def build_pipeline() -> Pipeline:
        numeric_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )
        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]
        )
        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, NUMERIC_FEATURES),
                ("cat", categorical_transformer, CATEGORICAL_FEATURES),
            ]
        )
        return Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("classifier", LogisticRegression(max_iter=1000)),
            ]
        )

    @staticmethod
    def prepare_dataset_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        if TARGET_COLUMN not in frame.columns:
            raise ModelServiceError(f"Dataset is missing the required '{TARGET_COLUMN}' column.")

        prepared = frame.copy()
        prepared = prepared.drop(columns=[name for name in DROP_COLUMNS if name in prepared.columns])
        missing = [name for name in FEATURE_COLUMNS if name not in prepared.columns]
        if missing:
            raise ModelServiceError(
                "Dataset is missing required columns: " + ", ".join(missing)
            )

        prepared["TotalCharges"] = pd.to_numeric(prepared["TotalCharges"], errors="coerce")
        target = prepared[TARGET_COLUMN].astype(str).str.strip()
        invalid_targets = sorted(set(target.unique()) - {"Yes", "No"})
        if invalid_targets:
            raise ModelServiceError(
                "The Churn column may contain only 'Yes' or 'No'. Found: "
                + ", ".join(invalid_targets[:5])
            )
        features = prepared[FEATURE_COLUMNS].copy()
        features["SeniorCitizen"] = pd.to_numeric(features["SeniorCitizen"], errors="coerce")
        features["tenure"] = pd.to_numeric(features["tenure"], errors="coerce")
        features["MonthlyCharges"] = pd.to_numeric(features["MonthlyCharges"], errors="coerce")
        return features, target

    def train(self) -> dict[str, Any]:
        # Resolve immediately before training. The default service may find the
        # CSV beside the EXE, bundled under PyInstaller's _internal directory,
        # or under the current working directory. Explicit test/caller paths
        # are intentionally not replaced with another file.
        if self._use_default_dataset_lookup:
            candidate_paths = [*DATASET_CANDIDATES, self.dataset_path]
        else:
            candidate_paths = [self.dataset_path]

        unique_candidates: list[Path] = []
        seen: set[str] = set()
        for candidate in candidate_paths:
            candidate = Path(candidate)
            key = str(candidate.resolve()).casefold()
            if key not in seen:
                seen.add(key)
                unique_candidates.append(candidate)

        selected_path = next(
            (candidate for candidate in unique_candidates if candidate.is_file()),
            None,
        )
        if selected_path is None:
            checked = "\n".join(f"  - {path}" for path in unique_candidates)
            raise ModelServiceError(
                "Training dataset was not found.\n\n"
                f"Expected file name: {self.dataset_path.name}\n\n"
                "Locations checked:\n"
                f"{checked}\n\n"
                "For a packaged app, place the CSV in a 'data' folder beside "
                "the EXE, or rebuild with the CSV present in the project's data folder."
            )

        try:
            frame = pd.read_csv(selected_path)
        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
            raise ModelServiceError(
                f"Could not read the training dataset at:\n{selected_path}\n\n{exc}"
            ) from exc
        self.dataset_path = selected_path
        return self.train_from_frame(frame, source_path=selected_path)

    def train_from_frame(self, frame: pd.DataFrame, source_path: Path | None = None) -> dict[str, Any]:
        features, target = self.prepare_dataset_frame(frame)
        if len(features) < 20:
            raise ModelServiceError("At least 20 rows are required to train and evaluate the model.")
        if target.nunique() < 2:
            raise ModelServiceError("The Churn column needs both 'Yes' and 'No' examples.")
        if int(target.value_counts().min()) < 2:
            raise ModelServiceError("Each Churn class needs at least two examples for a stratified split.")

        x_train, x_test, y_train, y_test = train_test_split(
            features,
            target,
            test_size=0.2,
            random_state=42,
            stratify=target,
        )
        model = self.build_pipeline()
        try:
            model.fit(x_train, y_train)
            y_pred = model.predict(x_test)
        except Exception as exc:
            logger.exception("Model training failed")
            raise ModelServiceError(f"Model training failed: {exc}") from exc

        report = classification_report(
            y_test,
            y_pred,
            labels=["No", "Yes"],
            output_dict=True,
            zero_division=0,
        )
        matrix = confusion_matrix(y_test, y_pred, labels=["No", "Yes"]).tolist()
        metadata: dict[str, Any] = {
            "trained_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "dataset_name": Path(source_path).name if source_path else "in-memory dataset",
            "dataset_rows": int(len(features)),
            "training_rows": int(len(x_train)),
            "testing_rows": int(len(x_test)),
            "feature_count": int(len(FEATURE_COLUMNS)),
            "target_column": TARGET_COLUMN,
            "model_name": "Logistic Regression",
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision_yes": float(report["Yes"]["precision"]),
            "recall_yes": float(report["Yes"]["recall"]),
            "f1_yes": float(report["Yes"]["f1-score"]),
            "classification_report": report,
            "confusion_matrix_labels": ["No", "Yes"],
            "confusion_matrix": matrix,
            "python_version": platform.python_version(),
            "scikit_learn_version": sklearn.__version__,
            "features": FEATURE_COLUMNS,
        }
        self._save_model(model, metadata)
        self.model = model
        self.metadata = metadata
        logger.info(
            "Model trained and saved. Accuracy=%.4f, churn recall=%.4f",
            metadata["accuracy"], metadata["recall_yes"],
        )
        return metadata

    def _save_model(self, model: Pipeline, metadata: Mapping[str, Any]) -> None:
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        model_tmp: Path | None = None
        meta_tmp: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="model_", suffix=".tmp", dir=self.model_path.parent, delete=False
            ) as handle:
                model_tmp = Path(handle.name)
            joblib.dump(model, model_tmp)
            os.replace(model_tmp, self.model_path)
            model_tmp = None

            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", prefix="metadata_", suffix=".tmp",
                dir=self.metadata_path.parent, delete=False
            ) as handle:
                meta_tmp = Path(handle.name)
                json.dump(dict(metadata), handle, indent=2, ensure_ascii=False)
            os.replace(meta_tmp, self.metadata_path)
            meta_tmp = None
        except OSError as exc:
            logger.exception("Failed to save model files")
            raise ModelServiceError(f"Could not save trained model files: {exc}") from exc
        finally:
            for temporary in (model_tmp, meta_tmp):
                if temporary and temporary.exists():
                    temporary.unlink(missing_ok=True)

    def load(self) -> bool:
        """Load an existing pipeline. Returns False if none exists."""
        if not self.model_path.exists():
            self.model = None
            self.metadata = self.read_metadata()
            return False
        try:
            loaded = joblib.load(self.model_path)
            if not hasattr(loaded, "predict") or not hasattr(loaded, "predict_proba"):
                raise ModelServiceError("The saved model file does not contain a compatible classifier.")
            self.model = loaded
            self.metadata = self.read_metadata()
            logger.info("Loaded model from %s", self.model_path)
            return True
        except Exception as exc:
            logger.exception("Could not load saved model")
            self.model = None
            raise ModelServiceError(
                "The saved model could not be loaded. Retrain it from the Model & Settings page."
            ) from exc

    def read_metadata(self) -> dict[str, Any]:
        if not self.metadata_path.exists():
            return {}
        try:
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            return metadata if isinstance(metadata, dict) else {}
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read model metadata: %s", exc)
            return {}

    @staticmethod
    def validate_customer(values: Mapping[str, Any]) -> dict[str, Any]:
        missing = [field for field in FEATURE_COLUMNS if field not in values or str(values[field]).strip() == ""]
        if missing:
            raise ValueError("Please complete all fields: " + ", ".join(missing))

        customer: dict[str, Any] = {}
        # Convert UI-friendly Yes/No to the numeric feature used by the training data.
        senior_value = values["SeniorCitizen"]
        if senior_value in (1, "1", True, "Yes"):
            customer["SeniorCitizen"] = 1
        elif senior_value in (0, "0", False, "No"):
            customer["SeniorCitizen"] = 0
        else:
            raise ValueError("Senior Citizen must be Yes or No.")

        try:
            tenure_number = float(values["tenure"])
            monthly_charges = float(values["MonthlyCharges"])
            total_charges = float(values["TotalCharges"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Tenure and charge fields must contain valid numbers.") from exc

        if not all(math.isfinite(number) for number in (tenure_number, monthly_charges, total_charges)):
            raise ValueError("Numeric fields must contain finite numbers.")
        if not tenure_number.is_integer():
            raise ValueError("Tenure must be a whole number of months.")
        if not 0 <= tenure_number <= 72:
            raise ValueError("Tenure must be between 0 and 72 months for this dataset.")
        if monthly_charges < 0 or total_charges < 0:
            raise ValueError("Charges cannot be negative.")

        customer["tenure"] = int(tenure_number)
        customer["MonthlyCharges"] = monthly_charges
        customer["TotalCharges"] = total_charges

        for field in CATEGORICAL_FEATURES:
            value = str(values[field]).strip()
            options = FIELD_OPTIONS.get(field)
            if options and value not in options:
                raise ValueError(f"Choose a valid option for {field}.")
            customer[field] = value

        # Catch combinations that cannot exist in the source data.
        if customer["PhoneService"] == "No":
            if customer["MultipleLines"] != "No phone service":
                raise ValueError("When Phone Service is No, Multiple Lines must be 'No phone service'.")
        elif customer["MultipleLines"] == "No phone service":
            raise ValueError("Choose No or Yes for Multiple Lines when Phone Service is Yes.")

        if customer["InternetService"] == "No":
            invalid = [field for field in INTERNET_DEPENDENT_FIELDS if customer[field] != "No internet service"]
            if invalid:
                raise ValueError("When Internet Service is No, internet-dependent services must be 'No internet service'.")
        else:
            invalid = [field for field in INTERNET_DEPENDENT_FIELDS if customer[field] == "No internet service"]
            if invalid:
                raise ValueError("Choose Yes or No for internet-dependent services when internet is available.")

        # Restore the model's training-column order, preserving expected dtypes.
        return {field: customer[field] for field in FEATURE_COLUMNS}

    def predict(self, values: Mapping[str, Any]) -> PredictionResult:
        if self.model is None:
            loaded = self.load()
            if not loaded:
                raise ModelServiceError("No trained model is available. Train the model first.")
        customer = self.validate_customer(values)
        frame = pd.DataFrame([customer], columns=FEATURE_COLUMNS)
        try:
            label = str(self.model.predict(frame)[0])  # type: ignore[union-attr]
            probabilities = self.model.predict_proba(frame)[0]  # type: ignore[union-attr]
            classes = list(self.model.classes_)  # type: ignore[union-attr]
            churn_probability = float(probabilities[classes.index("Yes")] * 100)
        except (ValueError, KeyError, IndexError, AttributeError) as exc:
            logger.exception("Prediction failed")
            raise ModelServiceError(f"Prediction failed. Check the customer information and model file: {exc}") from exc
        return PredictionResult(
            label=label,
            churn_probability=churn_probability,
            stay_probability=100.0 - churn_probability,
        )
