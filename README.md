# ChurnPilot by ashiix — Customer Churn Predictor

A local-first Python desktop application that uses the existing IBM Telco Customer Churn dataset and a scikit-learn preprocessing/model pipeline to estimate whether a customer is likely to churn (`Churn = Yes`). It is a continuation of the project built in the previous conversation, not a replacement with synthetic training data.

## Technical assessment and design

The first version used pandas, `ColumnTransformer`, `SimpleImputer`, `OneHotEncoder`, `StandardScaler`, and `LogisticRegression`, then saved the trained pipeline with joblib. The saved test result reported in the previous project was 80.55% accuracy and 56% recall for the churn (`Yes`) class.

This upgrade preserves that model family and feature schema and adds:

- **Overview dashboard** with prediction totals, saved churn flags, average score, model accuracy, recent predictions, and model/data status.
- **Prediction form** with all 19 features expected by the trained model, numeric validation, service-dependency checks, probability display, and friendly errors.
- **Light and dark themes**, persisted locally.
- **Prediction history** stored in SQLite, searchable, deletable, and exportable to CSV. To reduce local data retention, history stores only a summary (prediction, score, tenure, contract, monthly charge, internet service, and payment method), not the full form.
- **Model & Settings page** with model status, dataset/train/test row counts, evaluation metrics, local file paths, and a background-threaded train/retrain action.
- **Keyboard shortcuts**, tooltips, status feedback, application logging, and automated tests.
- **Path handling** that does not depend on the terminal's current folder and is compatible with an onedir PyInstaller build.

The interface uses Tkinter/ttk (no CustomTkinter dependency) so it stays lightweight and avoids adding an additional GUI framework.

## Project structure

```text
customer-churn-predictor-pro/
├── main.py                    # Start the GUI; --train trains/evaluates the model
├── requirements.txt           # Runtime dependencies
├── README.md
├── .gitignore
├── app/
│   ├── paths.py               # Central path configuration
│   ├── core/
│   │   ├── model_service.py   # Dataset validation, pipeline, prediction, model files
│   │   ├── history_store.py   # SQLite history
│   │   └── settings.py        # Local theme preferences
│   └── ui/
│       ├── app.py             # Main Tkinter application and pages
│       ├── theme.py           # Light/dark design system
│       └── widgets.py         # Reusable metric cards and tooltips
├── data/
│   └── README.txt             # Instructions for the original CSV
├── models/
│   └── README.txt             # Generated model files go here
├── logs/                      # Created automatically
└── tests/
    ├── helpers.py
    ├── test_model_service.py
    ├── test_history_store.py
    └── test_settings.py
```

## 1. Requirements

- Python 3.11 or newer; the project was syntax-checked and its tests were run using Python 3.13 in the build environment.
- Tkinter/Tcl-Tk support in your Python installation. On Windows, the standard installer from python.org normally provides it.
- The original `Telco-Customer-Churn.csv` dataset from your existing project.

## 2. Install on Windows

Open a terminal in the extracted project folder.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If you already have a working `.venv` in the old project, you may use that interpreter instead of creating another environment.

### Add the real dataset

The source CSV could not be included in this delivery because the original Windows folder is not accessible from this build environment. Copy the file you already downloaded from the old project:

```text
<old-project>\data\Telco-Customer-Churn.csv
```

to this project's:

```text
customer-churn-predictor-pro\data\Telco-Customer-Churn.csv
```

The app deliberately does not generate fake customers or silently train on made-up data. If you need to obtain the public dataset again, the source used in the original project was:

`https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv`

The CSV must include the `Churn` target and the feature columns used by the IBM Telco dataset.

## 3. Train the model

Run this from the project folder:

```powershell
.\.venv\Scripts\python.exe main.py --train
```

Training uses an 80/20 stratified split with a fixed random seed, evaluates a held-out test split, and saves:

- `models/churn_pipeline.joblib`
- `models/model_metadata.json`

The saved pipeline includes preprocessing so prediction inputs are transformed in the same way as training inputs. Training metrics are not a guarantee of performance on future customers.

## 4. Launch the desktop application

```powershell
.\.venv\Scripts\python.exe main.py
```

You can also launch the application and train from **Model & Settings → Train / refresh model**. Training is performed in a worker thread, so the Tkinter interface remains responsive. The dataset must be present before training.

For convenience on Windows, `run_app.bat` launches the GUI, `train_model.bat` trains the model, and `run_tests.bat` runs the automated tests (each uses the project-local `.venv`).

### Main workflow

1. Open **Predict** and fill all fields.
2. Select **Predict churn**. The app validates numeric values and service combinations before calling the trained pipeline.
3. Review the predicted label and model-estimated `Churn = Yes` probability.
4. Open **History** to search, export or delete saved prediction summaries.
5. Use the theme control for dark/light mode.

The probability is a model estimate, not a certainty, and should not be treated as a standalone decision about an individual customer. The baseline model reported about 56% recall on the `Yes` class in the earlier test run, so it missed a meaningful portion of customers who churned. Re-evaluate and improve the model before using it for consequential business decisions.

## 5. Automated tests

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

Tests cover customer input validation, dataset conversion, training/saving/loading/prediction, and SQLite create/search/delete/export behavior. The model test uses generated in-memory fixtures only to test the pipeline mechanics; the application itself never uses those fixtures as real training data.

## 6. Files and privacy

- Prediction summaries are stored in `data/prediction_history.sqlite3` on the local machine.
- The UI does **not** save the entire customer input form in the history database.
- Theme preference is stored in `data/settings.json`.
- Application logs are written to `logs/app.log`.
- Model binaries and local data are ignored by Git; they are generated or supplied locally.
- **Do not load `joblib` model files from untrusted sources**: joblib uses Python object serialization and is not a safe format for untrusted files.

Delete history from the History page when no longer needed. Exported CSVs are user-created files and are not removed automatically.

## 7. Optional Windows executable (PyInstaller)

First install PyInstaller in the same environment:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name ChurnPilot-by-ashiix main.py
```

Then copy your original dataset into `dist\ChurnPilot-by-ashiix\data\Telco-Customer-Churn.csv`. Run `dist\ChurnPilot-by-ashiix\ChurnPilot-by-ashiix.exe` and train the model from Model & Settings, or train it with the source environment before copying the resulting `models` folder beside the executable. The app stores generated model/history/log files beside the executable in an onedir build, so use a folder where your Windows account has write permissions.

## Known limitations / sensible next steps

- The baseline remains Logistic Regression; there has not yet been hyperparameter tuning or threshold optimization.
- Reported metrics depend on the source dataset and train/test split. The model page shows metrics produced when the local model was trained.
- This is a local desktop prototype, not a hosted or production customer-management system. It has no remote telemetry, login, or network API.
