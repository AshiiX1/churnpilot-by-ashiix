from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.core.model_service import FEATURE_COLUMNS, ModelService, ModelServiceError
from tests.helpers import sample_training_frame, valid_customer


class ModelServiceTests(unittest.TestCase):
    def test_validates_and_normalizes_customer(self):
        customer = valid_customer()
        customer["SeniorCitizen"] = "Yes"
        normalized = ModelService.validate_customer(customer)
        self.assertEqual(normalized["SeniorCitizen"], 1)
        self.assertIsInstance(normalized["tenure"], int)
        self.assertEqual(list(normalized), FEATURE_COLUMNS)

    def test_rejects_missing_field(self):
        customer = valid_customer()
        customer.pop("Contract")
        with self.assertRaisesRegex(ValueError, "Contract"):
            ModelService.validate_customer(customer)

    def test_rejects_invalid_tenure(self):
        customer = valid_customer()
        customer["tenure"] = "90"
        with self.assertRaisesRegex(ValueError, "between 0 and 72"):
            ModelService.validate_customer(customer)

    def test_rejects_inconsistent_service_fields(self):
        customer = valid_customer()
        customer["InternetService"] = "DSL"
        customer["OnlineSecurity"] = "No internet service"
        with self.assertRaisesRegex(ValueError, "internet-dependent"):
            ModelService.validate_customer(customer)

    def test_prepare_frame_coerces_bad_total_charges_to_missing(self):
        frame = sample_training_frame(30)
        frame["TotalCharges"] = frame["TotalCharges"].astype("object")
        frame.loc[0, "TotalCharges"] = " "
        features, target = ModelService.prepare_dataset_frame(frame)
        self.assertTrue(pd.isna(features.loc[0, "TotalCharges"]))
        self.assertEqual(len(target), 30)

    def test_trains_saves_loads_and_predicts(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            service = ModelService(
                dataset_path=base / "dataset.csv",
                model_path=base / "models" / "model.joblib",
                metadata_path=base / "models" / "metadata.json",
            )
            metadata = service.train_from_frame(sample_training_frame(60))
            self.assertTrue(service.model_path.exists())
            self.assertTrue(service.metadata_path.exists())
            self.assertGreaterEqual(metadata["accuracy"], 0.0)
            self.assertLessEqual(metadata["accuracy"], 1.0)
            service.model = None
            self.assertTrue(service.load())
            prediction = service.predict(valid_customer())
            self.assertIn(prediction.label, {"Yes", "No"})
            self.assertGreaterEqual(prediction.churn_probability, 0.0)
            self.assertLessEqual(prediction.churn_probability, 100.0)


    def test_corrupt_model_file_is_reported_as_model_error(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            model_path = base / "broken.joblib"
            model_path.write_bytes(b"not a joblib model")
            service = ModelService(
                dataset_path=base / "dataset.csv",
                model_path=model_path,
                metadata_path=base / "metadata.json",
            )
            with self.assertRaises(ModelServiceError):
                service.load()


    def test_missing_training_dataset_lists_checked_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            service = ModelService(
                dataset_path=base / "data" / "Telco-Customer-Churn.csv",
                model_path=base / "models" / "model.joblib",
                metadata_path=base / "models" / "metadata.json",
            )
            with self.assertRaises(ModelServiceError) as context:
                service.train()
            message = str(context.exception)
            self.assertIn("Training dataset was not found", message)
            self.assertIn("Locations checked:", message)
            self.assertIn("Telco-Customer-Churn.csv", message)

    def test_training_requires_both_target_classes(self):
        frame = sample_training_frame(30)
        frame["Churn"] = "No"
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            service = ModelService(
                dataset_path=base / "dataset.csv",
                model_path=base / "model.joblib",
                metadata_path=base / "metadata.json",
            )
            with self.assertRaises(ModelServiceError):
                service.train_from_frame(frame)


if __name__ == "__main__":
    unittest.main()
