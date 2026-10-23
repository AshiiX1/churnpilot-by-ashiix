Training dataset
================

Copy the original IBM Telco Customer Churn dataset into this folder and name it:

    Telco-Customer-Churn.csv

The CSV is intentionally not committed to Git. The app searches for the file in
this project's data folder during development, and in the external data folder
beside the EXE or PyInstaller's bundled data folder when packaged.

Do not replace the official data with synthetic data for real model training.
