from __future__ import annotations

import pandas as pd

from app.core.model_service import FEATURE_COLUMNS


def valid_customer() -> dict:
    return {
        "gender": "Female",
        "SeniorCitizen": "No",
        "Partner": "Yes",
        "Dependents": "No",
        "tenure": "12",
        "PhoneService": "No",
        "MultipleLines": "No phone service",
        "InternetService": "No",
        "OnlineSecurity": "No internet service",
        "OnlineBackup": "No internet service",
        "DeviceProtection": "No internet service",
        "TechSupport": "No internet service",
        "StreamingTV": "No internet service",
        "StreamingMovies": "No internet service",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": "30.00",
        "TotalCharges": "360.00",
    }


def sample_training_frame(rows: int = 60) -> pd.DataFrame:
    records = []
    methods = [
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ]
    contracts = ["Month-to-month", "One year", "Two year"]
    for i in range(rows):
        internet = ["DSL", "Fiber optic", "No"][i % 3]
        internet_value = "No internet service" if internet == "No" else ("Yes" if i % 2 else "No")
        phone = "No" if i % 4 == 0 else "Yes"
        multiple = "No phone service" if phone == "No" else ("Yes" if i % 2 else "No")
        customer = {
            "gender": "Female" if i % 2 else "Male",
            "SeniorCitizen": i % 2,
            "Partner": "Yes" if i % 3 else "No",
            "Dependents": "Yes" if i % 5 == 0 else "No",
            "tenure": (i * 7) % 73,
            "PhoneService": phone,
            "MultipleLines": multiple,
            "InternetService": internet,
            "OnlineSecurity": internet_value,
            "OnlineBackup": internet_value,
            "DeviceProtection": internet_value,
            "TechSupport": internet_value,
            "StreamingTV": internet_value,
            "StreamingMovies": internet_value,
            "Contract": contracts[i % len(contracts)],
            "PaperlessBilling": "Yes" if i % 2 else "No",
            "PaymentMethod": methods[i % len(methods)],
            "MonthlyCharges": float(25 + (i * 13) % 150),
            "TotalCharges": float((25 + (i * 13) % 150) * ((i * 7) % 73)),
            "Churn": "Yes" if i % 3 == 0 else "No",
        }
        # Every internet-dependent value must match InternetService.
        if internet == "No":
            for field in ("OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"):
                customer[field] = "No internet service"
        else:
            for field in ("OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"):
                customer[field] = "Yes" if i % 2 else "No"
        assert all(field in customer for field in FEATURE_COLUMNS)
        records.append(customer)
    return pd.DataFrame(records)
