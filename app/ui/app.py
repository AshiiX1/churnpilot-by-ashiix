"""Premium, responsive Tkinter interface for Customer Churn Predictor."""
from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import Image, ImageTk

from app.core.history_store import HistoryStore
from app.core.model_service import (
    FIELD_OPTIONS,
    INTERNET_DEPENDENT_FIELDS,
    ModelService,
    ModelServiceError,
    PredictionResult,
)
from app.core.settings import SettingsStore
from app.paths import (
    DATASET_CANDIDATES,
    DATASET_PATH,
    HISTORY_DB_PATH,
    MODEL_METADATA_PATH,
    MODEL_PATH,
    SETTINGS_PATH,
    resolve_dataset_path,
    resource_path,
)
from app.ui.theme import apply_theme
from app.ui.widgets import MetricCard, ToolTip

logger = logging.getLogger(__name__)

FIELD_LABELS = {
    "gender": "Gender",
    "SeniorCitizen": "Senior citizen",
    "Partner": "Has partner",
    "Dependents": "Has dependents",
    "tenure": "Tenure (months)",
    "PhoneService": "Phone service",
    "MultipleLines": "Multiple lines",
    "InternetService": "Internet service",
    "OnlineSecurity": "Online security",
    "OnlineBackup": "Online backup",
    "DeviceProtection": "Device protection",
    "TechSupport": "Tech support",
    "StreamingTV": "Streaming TV",
    "StreamingMovies": "Streaming movies",
    "Contract": "Contract",
    "PaperlessBilling": "Paperless billing",
    "PaymentMethod": "Payment method",
    "MonthlyCharges": "Monthly charges",
    "TotalCharges": "Total charges",
}

LEFT_FIELDS = [
    "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
    "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
]
RIGHT_FIELDS = [
    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod", "MonthlyCharges", "TotalCharges",
]


class CustomerChurnApp:
    NAV_ITEMS = [
        ("Overview", "◈", "Overview"),
        ("Predict", "✦", "New prediction"),
        ("History", "▤", "Prediction history"),
        ("Model & Settings", "⚙", "Model & settings"),
    ]

    def __init__(self, root: tk.Tk | None = None) -> None:
        self.root = root or tk.Tk()
        self.root.title("ChurnPilot by ashiix | Customer Analytics")

        # Set the custom window/taskbar icon from the packaged or source assets.
        icon_path = resource_path("assets/churnpilot.ico")
        self._window_icons: list[ImageTk.PhotoImage] = []
        try:
            if icon_path.is_file():
                with Image.open(icon_path) as source_icon:
                    icon_rgba = source_icon.convert("RGBA")
                self._window_icons = [
                    ImageTk.PhotoImage(
                        icon_rgba.resize((size, size), Image.Resampling.LANCZOS),
                        master=self.root,
                    )
                    for size in (16, 24, 32, 48, 64)
                ]
                self.root.iconphoto(True, *self._window_icons)
                logger.info("Application icon loaded from %s", icon_path)
            else:
                logger.warning("Application icon file not found: %s", icon_path)
        except Exception:
            # A bad/missing icon must never prevent the app from opening.
            logger.exception("Could not load application icon from %s", icon_path)

        self.root.geometry("1320x860")
        self.root.minsize(1080, 700)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.settings = SettingsStore(SETTINGS_PATH)
        self.theme_name = self.settings.get("theme", "dark")
        self.colors = apply_theme(self.root, self.theme_name)
        self.model_service = ModelService()
        self.history = HistoryStore(HISTORY_DB_PATH)
        self.model_ready = False
        self.model_load_error: str | None = None
        try:
            self.model_ready = self.model_service.load()
        except ModelServiceError as exc:
            self.model_load_error = str(exc)
            logger.warning("Model unavailable at launch: %s", exc)

        self.current_page = "Overview"
        self.current_page_frame: ttk.Frame | None = None
        self.navigation_buttons: dict[str, ttk.Button] = {}
        self.train_buttons: list[ttk.Button] = []
        self.training_busy = False
        self.event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.form_vars: dict[str, tk.StringVar] = {}
        self.form_widgets: dict[str, ttk.Widget] = {}
        self.form_state: dict[str, str] = {}
        self.last_prediction: PredictionResult | None = None
        self.footer_var = tk.StringVar(value="Ready")

        self._build_shell()
        self._bind_shortcuts()
        self.show_page("Overview")
        self.root.after(120, self._poll_worker_events)

    # ----- Shell and navigation -------------------------------------------------
    def _build_shell(self) -> None:
        self.shell = ttk.Frame(self.root, style="App.TFrame")
        self.shell.pack(fill="both", expand=True)
        self.shell.grid_rowconfigure(0, weight=1)
        self.shell.grid_columnconfigure(1, weight=1)

        self.sidebar = ttk.Frame(self.shell, style="Sidebar.TFrame", width=230, padding=(14, 18))
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        brand = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        brand.pack(fill="x", padx=6, pady=(2, 28))
        mark = tk.Label(
            brand, text="C", font=("Segoe UI Semibold", 17), width=2, height=1,
            background=self.colors["accent"], foreground="#FFFFFF", padx=2, pady=3,
        )
        mark.pack(side="left", padx=(0, 10))
        brand_text = ttk.Frame(brand, style="Sidebar.TFrame")
        brand_text.pack(side="left", fill="x", expand=True)
        ttk.Label(brand_text, text="CHURNPILOT", style="SidebarBrand.TLabel").pack(anchor="w")
        ttk.Label(brand_text, text="by ashiix · CUSTOMER ANALYTICS", style="SidebarHint.TLabel").pack(anchor="w", pady=(2, 0))

        ttk.Label(self.sidebar, text="WORKSPACE", style="SidebarHint.TLabel").pack(anchor="w", padx=10, pady=(0, 8))
        for key, glyph, label in self.NAV_ITEMS:
            button = ttk.Button(
                self.sidebar,
                text=f"{glyph}    {label}",
                style="Nav.TButton",
                command=lambda page=key: self.show_page(page),
            )
            button.pack(fill="x", pady=3)
            self.navigation_buttons[key] = button
            ToolTip(button, f"Open {label}")

        spacer = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        spacer.pack(fill="both", expand=True)

        self.sidebar_status = ttk.Frame(self.sidebar, style="Card.TFrame", padding=12)
        self.sidebar_status.pack(fill="x", pady=(18, 8))
        ttk.Label(self.sidebar_status, text="MODEL STATUS", style="CardTitle.TLabel").pack(anchor="w")
        self.model_status_text = ttk.Label(self.sidebar_status, text="Checking model…", style="CardBody.TLabel", wraplength=175)
        self.model_status_text.pack(anchor="w", pady=(7, 0))
        ttk.Label(self.sidebar, text="Local-first • Your history stays here", style="SidebarHint.TLabel", wraplength=190).pack(anchor="w", padx=8, pady=(8, 0))

        self.content = ttk.Frame(self.shell, style="Content.TFrame", padding=(24, 18, 24, 12))
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(1, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.header = ttk.Frame(self.content, style="Content.TFrame")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self.header.grid_columnconfigure(0, weight=1)
        title_group = ttk.Frame(self.header, style="Content.TFrame")
        title_group.grid(row=0, column=0, sticky="w")
        self.page_title = ttk.Label(title_group, text="Overview", style="Title.TLabel")
        self.page_title.pack(anchor="w")
        self.page_subtitle = ttk.Label(title_group, text="A clear view of customer churn predictions.", style="Subtitle.TLabel")
        self.page_subtitle.pack(anchor="w", pady=(3, 0))

        actions = ttk.Frame(self.header, style="Content.TFrame")
        actions.grid(row=0, column=1, sticky="e", padx=(14, 0))
        self.header_status = ttk.Label(actions, text="● Model ready" if self.model_ready else "● Model needed", style="Pill.TLabel")
        self.header_status.pack(side="left", padx=(0, 10))
        self.theme_button = ttk.Button(actions, text=self._theme_button_text(), command=self.toggle_theme)
        self.theme_button.pack(side="left")
        ToolTip(self.theme_button, "Switch between dark and light appearance")
        self.progress = ttk.Progressbar(self.header, mode="indeterminate", length=180)
        self.header.grid_rowconfigure(1, weight=0)

        self.page_host = ttk.Frame(self.content, style="Content.TFrame")
        self.page_host.grid(row=1, column=0, sticky="nsew")
        self.page_host.grid_rowconfigure(0, weight=1)
        self.page_host.grid_columnconfigure(0, weight=1)

        footer = ttk.Frame(self.content, style="Content.TFrame")
        footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Separator(footer, orient="horizontal").pack(fill="x", pady=(0, 8))
        footer_status = ttk.Frame(footer, style="Content.TFrame")
        footer_status.pack(fill="x")
        ttk.Label(footer_status, textvariable=self.footer_var, style="Muted.TLabel").pack(side="left")
        ttk.Label(footer_status, text="Predictions are estimates, not guarantees.", style="Muted.TLabel").pack(side="right")
        ttk.Label(
            footer,
            text="by ashiix  ·  Built with Python & Machine Learning",
            style="BrandFooter.TLabel",
        ).pack(anchor="center", pady=(5, 0))
        self._update_model_status()

    def _bind_shortcuts(self) -> None:
        self.root.bind_all("<Control-1>", lambda _event: self.show_page("Overview"))
        self.root.bind_all("<Control-2>", lambda _event: self.show_page("Predict"))
        self.root.bind_all("<Control-3>", lambda _event: self.show_page("History"))
        self.root.bind_all("<Control-4>", lambda _event: self.show_page("Model & Settings"))
        self.root.bind_all("<Control-l>", lambda _event: self.toggle_theme())
        self.root.bind_all("<Control-L>", lambda _event: self.toggle_theme())
        self.root.bind_all("<Control-Return>", self._shortcut_predict)
        self.root.bind_all("<Escape>", self._shortcut_escape)

    def _shortcut_predict(self, _event=None):
        if self.current_page == "Predict":
            self.predict()
        else:
            self.show_page("Predict")
        return "break"

    def _shortcut_escape(self, _event=None):
        if self.current_page == "Predict":
            self.reset_form()
        return "break"

    def _theme_button_text(self) -> str:
        return "☼  Light mode" if self.theme_name == "dark" else "◐  Dark mode"

    def toggle_theme(self) -> None:
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.settings.set("theme", self.theme_name)
        self.colors = apply_theme(self.root, self.theme_name)
        self.theme_button.configure(text=self._theme_button_text())
        # Redraw visible page so custom surfaces follow the palette.
        self.show_page(self.current_page)
        self.footer_var.set(f"Appearance changed to {self.theme_name} mode")

    def show_page(self, page: str) -> None:
        if page not in self.navigation_buttons:
            return
        if self.current_page == "Predict" and self.form_vars:
            self.form_state = {field: variable.get() for field, variable in self.form_vars.items()}
        self.current_page = page
        self.train_buttons = []
        self.page_title.configure(text=page)
        subtitle = {
            "Overview": "A clear view of customer churn predictions.",
            "Predict": "Enter a customer's service profile to estimate churn probability.",
            "History": "Review, filter, remove, or export saved prediction summaries.",
            "Model & Settings": "Model health, evaluation results, and application preferences.",
        }
        self.page_subtitle.configure(text=subtitle[page])
        for key, button in self.navigation_buttons.items():
            button.configure(style="NavActive.TButton" if key == page else "Nav.TButton")
        if self.current_page_frame is not None:
            self.current_page_frame.destroy()
            self.current_page_frame = None
        frame = ttk.Frame(self.page_host, style="Content.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        self.current_page_frame = frame
        if page == "Overview":
            self._build_overview(frame)
        elif page == "Predict":
            self._build_predict_page(frame)
        elif page == "History":
            self._build_history_page(frame)
        else:
            self._build_settings_page(frame)
        self._update_model_status()

    def _update_model_status(self) -> None:
        if not hasattr(self, "model_status_text"):
            return
        if self.model_ready:
            self.model_status_text.configure(text="Ready · Logistic Regression")
            self.header_status.configure(text="● Model ready")
        elif self.training_busy:
            self.model_status_text.configure(text="Training model…")
            self.header_status.configure(text="● Training")
        elif self.model_load_error:
            self.model_status_text.configure(text="Model unavailable · retrain in settings")
            self.header_status.configure(text="● Model issue")
        else:
            self.model_status_text.configure(text="Not trained · train from the real dataset")
            self.header_status.configure(text="● Model needed")

    # ----- Overview -------------------------------------------------------------
    def _build_overview(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        hero = ttk.Frame(parent, style="Card.TFrame", padding=(20, 18))
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        hero.grid_columnconfigure(0, weight=1)
        hero_left = ttk.Frame(hero, style="Card.TFrame")
        hero_left.grid(row=0, column=0, sticky="ew")
        eyebrow = ttk.Label(hero_left, text="CUSTOMER RETENTION WORKSPACE", style="CardTitle.TLabel")
        eyebrow.pack(anchor="w")
        ttk.Label(
            hero_left,
            text="Turn customer data into a useful churn signal.",
            font=("Segoe UI Semibold", 18),
            background=self.colors["surface"],
            foreground=self.colors["text"],
        ).pack(anchor="w", pady=(7, 5))
        ttk.Label(
            hero_left,
            text="Run a prediction, review your recent work, and keep the trained model version in one place.",
            style="MutedCard.TLabel",
            wraplength=620,
        ).pack(anchor="w")
        hero_actions = ttk.Frame(hero, style="Card.TFrame")
        hero_actions.grid(row=0, column=1, sticky="e", padx=(16, 0))
        ttk.Button(hero_actions, text="✦  New prediction", style="Accent.TButton", command=lambda: self.show_page("Predict")).pack(fill="x", pady=(0, 8))
        train_button = ttk.Button(hero_actions, text="↻  Train / refresh model", command=self.start_training, state="disabled" if self.training_busy else "normal")
        train_button.pack(fill="x")
        ToolTip(train_button, "Train using the original Telco Customer Churn CSV in data/")
        self.train_buttons.append(train_button)

        summary = self.history.summary()
        metadata = self.model_service.metadata
        cards = ttk.Frame(parent, style="Content.TFrame")
        cards.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        for index in range(4):
            cards.grid_columnconfigure(index, weight=1, uniform="metrics")
        values = [
            ("Predictions run", f"{summary['total']:,}", "Saved locally in this workspace"),
            ("Flagged as churn", f"{summary['flagged']:,}", "Model predicted churn = Yes"),
            ("Average churn score", f"{summary['average_probability']:.1f}%", "Across saved predictions"),
            ("Test accuracy", f"{float(metadata.get('accuracy', 0.0)):.1%}" if metadata.get("accuracy") is not None else "—", "Held-out test split"),
        ]
        for index, (title, value, hint) in enumerate(values):
            card = MetricCard(cards, title, value, hint)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 6, 0 if index == 3 else 6))

        lower = ttk.Frame(parent, style="Content.TFrame")
        lower.grid(row=2, column=0, sticky="nsew")
        lower.grid_rowconfigure(0, weight=1)
        lower.grid_columnconfigure(0, weight=3)
        lower.grid_columnconfigure(1, weight=2)
        recent_panel = ttk.Frame(lower, style="Card.TFrame", padding=14)
        recent_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        recent_panel.grid_rowconfigure(1, weight=1)
        recent_panel.grid_columnconfigure(0, weight=1)
        title_row = ttk.Frame(recent_panel, style="Card.TFrame")
        title_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(title_row, text="Recent predictions", font=("Segoe UI Semibold", 12), background=self.colors["surface"], foreground=self.colors["text"]).pack(side="left")
        ttk.Button(title_row, text="View history  →", command=lambda: self.show_page("History")).pack(side="right")
        tree_frame = ttk.Frame(recent_panel, style="Card.TFrame")
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree = self._make_tree(tree_frame, [
            ("created_at", "Time", 155),
            ("predicted_label", "Prediction", 90),
            ("churn_probability", "Churn score", 100),
            ("contract", "Contract", 120),
        ], height=7)
        for row in self.history.list_predictions(limit=7):
            tree.insert("", "end", iid=str(row["id"]), values=(self._display_time(row["created_at"]), row["predicted_label"], f"{row['churn_probability']:.1f}%", row["contract"]), tags=("yes" if row["predicted_label"] == "Yes" else "no",))
        if not self.history.list_predictions(limit=1):
            ttk.Label(recent_panel, text="No predictions yet. Create the first one from New prediction.", style="MutedCard.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 0))

        info_panel = ttk.Frame(lower, style="Card.TFrame", padding=16)
        info_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ttk.Label(info_panel, text="Project health", font=("Segoe UI Semibold", 12), background=self.colors["surface"], foreground=self.colors["text"]).pack(anchor="w", pady=(0, 14))
        self._health_row(info_panel, "Trained model", "Available" if self.model_ready else "Needs training", self.colors["success"] if self.model_ready else self.colors["warning"])
        self._health_row(info_panel, "Training data", "Found" if DATASET_PATH.exists() else "Not in package", self.colors["success"] if DATASET_PATH.exists() else self.colors["warning"])
        self._health_row(info_panel, "Prediction history", "SQLite · local file", self.colors["muted"])
        ttk.Separator(info_panel, orient="horizontal").pack(fill="x", pady=12)
        ttk.Label(info_panel, text="How to read churn scores", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            info_panel,
            text="The score is the model's estimated probability for the Churn = Yes class. It is not a guarantee. The current baseline's recall for churn was about 56% on its held-out split, so some customers who leave may be missed.",
            style="MutedCard.TLabel",
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=(7, 0))

    def _health_row(self, parent: ttk.Frame, label: str, value: str, color: str) -> None:
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=5)
        ttk.Label(row, text=label, style="MutedCard.TLabel").pack(side="left")
        ttk.Label(row, text=value, background=self.colors["surface"], foreground=color, font=("Segoe UI Semibold", 9)).pack(side="right")

    # ----- Prediction form ------------------------------------------------------
    def _build_predict_page(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=0)
        top = ttk.Frame(parent, style="Content.TFrame")
        top.grid(row=0, column=0, sticky="nsew")
        top.grid_columnconfigure(0, weight=1, uniform="forms")
        top.grid_columnconfigure(1, weight=1, uniform="forms")
        left = ttk.LabelFrame(top, text="  Customer profile  ", padding=(14, 10))
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
        right = ttk.LabelFrame(top, text="  Services & billing  ", padding=(14, 10))
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 12))
        left.grid_columnconfigure(1, weight=1)
        right.grid_columnconfigure(1, weight=1)
        self.form_vars = {}
        self.form_widgets = {}
        self._create_fields(left, LEFT_FIELDS)
        self._create_fields(right, RIGHT_FIELDS)

        form_actions = ttk.Frame(top, style="Content.TFrame")
        form_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        form_actions.grid_columnconfigure(0, weight=1)
        ttk.Label(form_actions, text="All fields are required. Only the prediction summary is saved to local history.", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(form_actions, text="Reset", command=self.reset_form).grid(row=0, column=1, padx=(6, 6))
        predict_button = ttk.Button(form_actions, text="✦  Predict churn", style="Accent.TButton", command=self.predict, state="normal" if self.model_ready else "disabled")
        predict_button.grid(row=0, column=2)
        ToolTip(predict_button, "Estimate churn probability using the saved machine-learning pipeline")

        result = ttk.Frame(parent, style="Card.TFrame", padding=(18, 12))
        result.grid(row=1, column=0, sticky="ew", pady=(0, 2))
        result.grid_columnconfigure(0, weight=1)
        self.result_title = ttk.Label(result, text="Prediction result will appear here", font=("Segoe UI Semibold", 13), background=self.colors["surface"], foreground=self.colors["text"])
        self.result_title.grid(row=0, column=0, sticky="w")
        self.result_detail = ttk.Label(result, text="Complete the form, then select Predict churn.", style="MutedCard.TLabel", wraplength=680)
        self.result_detail.grid(row=1, column=0, sticky="w", pady=(4, 8))
        self.result_score = ttk.Progressbar(result, mode="determinate", maximum=100, value=0, length=260)
        self.result_score.grid(row=2, column=0, sticky="ew")
        self.result_score_text = ttk.Label(result, text="Churn probability: —", style="MutedCard.TLabel")
        self.result_score_text.grid(row=2, column=1, sticky="e", padx=(12, 0))

        if not self.model_ready:
            warning = ttk.Label(result, text="Model is not ready. Open Model & Settings and train it from the original CSV first.", style="Warning.TLabel", wraplength=820)
            warning.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self._restore_form_state()
        if self.last_prediction:
            self._display_prediction(self.last_prediction)

    def _create_fields(self, parent: ttk.LabelFrame, fields: list[str]) -> None:
        for row, field in enumerate(fields):
            label = ttk.Label(parent, text=FIELD_LABELS[field], style="CardBody.TLabel")
            label.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
            variable = tk.StringVar(value="")
            self.form_vars[field] = variable
            if field in FIELD_OPTIONS:
                values = FIELD_OPTIONS[field]
                widget = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=27)
                if field == "PhoneService":
                    widget.configure(postcommand=None)
                    widget.bind("<<ComboboxSelected>>", self._on_phone_service_change, add="+")
                if field == "InternetService":
                    widget.bind("<<ComboboxSelected>>", self._on_internet_service_change, add="+")
            elif field == "SeniorCitizen":
                widget = ttk.Combobox(parent, textvariable=variable, values=("No", "Yes"), state="readonly", width=27)
            else:
                widget = ttk.Entry(parent, textvariable=variable, width=29)
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            self.form_widgets[field] = widget
            ToolTip(widget, self._field_tooltip(field))

    @staticmethod
    def _field_tooltip(field: str) -> str:
        hints = {
            "tenure": "Number of months this customer has stayed with the company (0–72 in this dataset).",
            "MonthlyCharges": "Current monthly charge; enter a non-negative number.",
            "TotalCharges": "Total charges to date; enter a non-negative number.",
            "SeniorCitizen": "Choose Yes or No. The app converts this to the numeric value used by the model.",
            "PaymentMethod": "Select the customer's recorded payment method.",
        }
        return hints.get(field, f"Select the recorded {FIELD_LABELS[field].lower()} value.")

    def _on_phone_service_change(self, _event=None) -> None:
        phone = self.form_vars.get("PhoneService")
        multiple_var = self.form_vars.get("MultipleLines")
        multiple_widget = self.form_widgets.get("MultipleLines")
        if not phone or not multiple_var or not multiple_widget:
            return
        if phone.get() == "No":
            multiple_widget.configure(values=("No phone service",))
            multiple_var.set("No phone service")
        elif phone.get() == "Yes":
            multiple_widget.configure(values=("No", "Yes"))
            if multiple_var.get() == "No phone service":
                multiple_var.set("")

    def _on_internet_service_change(self, _event=None) -> None:
        internet = self.form_vars.get("InternetService")
        if not internet:
            return
        for field in INTERNET_DEPENDENT_FIELDS:
            variable = self.form_vars.get(field)
            widget = self.form_widgets.get(field)
            if not variable or not widget:
                continue
            if internet.get() == "No":
                widget.configure(values=("No internet service",))
                variable.set("No internet service")
            elif internet.get() in {"DSL", "Fiber optic"}:
                widget.configure(values=("No", "Yes"))
                if variable.get() == "No internet service":
                    variable.set("")

    def _restore_form_state(self) -> None:
        if not self.form_state or not self.form_vars:
            return
        phone_value = self.form_state.get("PhoneService", "")
        internet_value = self.form_state.get("InternetService", "")
        if "PhoneService" in self.form_vars:
            self.form_vars["PhoneService"].set(phone_value)
            self._on_phone_service_change()
        if "InternetService" in self.form_vars:
            self.form_vars["InternetService"].set(internet_value)
            self._on_internet_service_change()
        for field, value in self.form_state.items():
            if field in self.form_vars:
                self.form_vars[field].set(value)

    def predict(self) -> None:
        if not self.model_ready:
            messagebox.showwarning("Model unavailable", "Train the model first from Model & Settings.", parent=self.root)
            return
        values = {field: variable.get() for field, variable in self.form_vars.items()}
        try:
            validated = self.model_service.validate_customer(values)
            result = self.model_service.predict(validated)
        except ValueError as exc:
            messagebox.showwarning("Check the form", str(exc), parent=self.root)
            self.footer_var.set("Prediction not run · check the highlighted form values")
            return
        except ModelServiceError as exc:
            logger.exception("Prediction request failed")
            messagebox.showerror("Prediction failed", str(exc), parent=self.root)
            self.footer_var.set("Prediction failed")
            return

        self.last_prediction = result
        self._display_prediction(result)
        try:
            self.history.add_prediction(
                predicted_label=result.label,
                churn_probability=result.churn_probability,
                tenure=validated["tenure"],
                contract=validated["Contract"],
                monthly_charges=validated["MonthlyCharges"],
                internet_service=validated["InternetService"],
                payment_method=validated["PaymentMethod"],
            )
            self.footer_var.set("Prediction complete · summary saved to local history")
        except Exception as exc:
            logger.exception("Prediction succeeded but history could not be saved")
            self.footer_var.set("Prediction complete · history could not be saved")
            messagebox.showwarning("History not saved", f"The prediction was made, but history could not be saved.\n\n{exc}", parent=self.root)

    def _display_prediction(self, result: PredictionResult) -> None:
        if not hasattr(self, "result_title") or not self.result_title.winfo_exists():
            return
        churn_percent = result.churn_probability
        if result.label == "Yes":
            self.result_title.configure(text=f"Prediction: likely to churn  ·  {result.risk_band} score", foreground=self.colors["danger"] if result.risk_band == "High" else self.colors["warning"])
            self.result_detail.configure(text="The model classified this customer as Churn = Yes. Use this as a signal for further review, not as a certainty.")
        else:
            self.result_title.configure(text=f"Prediction: likely to stay  ·  {result.risk_band} score", foreground=self.colors["success"])
            self.result_detail.configure(text="The model classified this customer as Churn = No. This does not guarantee the customer will stay.")
        self.result_score.configure(value=churn_percent)
        self.result_score_text.configure(text=f"Churn probability: {churn_percent:.1f}%")

    def reset_form(self) -> None:
        self.form_state = {}
        for variable in self.form_vars.values():
            variable.set("")
        # Restore complete dropdown options after dependent-field changes.
        for field in ("MultipleLines",):
            widget = self.form_widgets.get(field)
            if widget:
                widget.configure(values=FIELD_OPTIONS[field])
        for field in INTERNET_DEPENDENT_FIELDS:
            widget = self.form_widgets.get(field)
            if widget:
                widget.configure(values=FIELD_OPTIONS[field])
        if hasattr(self, "result_title") and self.result_title.winfo_exists():
            self.result_title.configure(text="Prediction result will appear here", foreground=self.colors["text"])
            self.result_detail.configure(text="Complete the form, then select Predict churn.")
            self.result_score.configure(value=0)
            self.result_score_text.configure(text="Churn probability: —")
        self.last_prediction = None
        self.footer_var.set("Form cleared")

    # ----- History --------------------------------------------------------------
    def _build_history_page(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        toolbar = ttk.Frame(parent, style="Content.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        ttk.Label(toolbar, text="Search history", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        search_row = ttk.Frame(toolbar, style="Content.TFrame")
        search_row.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.history_search_var = tk.StringVar(value="")
        search_entry = ttk.Entry(search_row, textvariable=self.history_search_var, width=34)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.bind("<KeyRelease>", lambda _event: self._refresh_history_tree())
        ToolTip(search_entry, "Filter by prediction, contract, internet service, payment method, or date")
        ttk.Button(search_row, text="Export CSV", command=self.export_history).pack(side="left", padx=(8, 0))
        ttk.Button(search_row, text="Delete selected", command=self.delete_selected_history).pack(side="left", padx=(8, 0))
        ttk.Button(search_row, text="Clear all", style="Danger.TButton", command=self.clear_history).pack(side="left", padx=(8, 0))

        panel = ttk.Frame(parent, style="Card.TFrame", padding=12)
        panel.grid(row=1, column=0, sticky="nsew")
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        self.history_tree = self._make_tree(panel, [
            ("created_at", "Created", 155),
            ("predicted_label", "Prediction", 95),
            ("churn_probability", "Churn score", 100),
            ("tenure", "Tenure", 70),
            ("contract", "Contract", 145),
            ("monthly_charges", "Monthly charge", 115),
            ("internet_service", "Internet", 110),
            ("payment_method", "Payment method", 195),
        ], height=15)
        self.history_count_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.history_count_var, style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._refresh_history_tree()

    def _refresh_history_tree(self) -> None:
        tree = getattr(self, "history_tree", None)
        if tree is None or not tree.winfo_exists():
            return
        for item in tree.get_children():
            tree.delete(item)
        search = self.history_search_var.get() if hasattr(self, "history_search_var") else ""
        rows = self.history.list_predictions(search=search)
        for row in rows:
            tree.insert(
                "", "end", iid=str(row["id"]),
                values=(
                    self._display_time(row["created_at"]),
                    row["predicted_label"],
                    f"{row['churn_probability']:.1f}%",
                    row["tenure"],
                    row["contract"],
                    f"{row['monthly_charges']:.2f}",
                    row["internet_service"],
                    row["payment_method"],
                ),
                tags=("yes" if row["predicted_label"] == "Yes" else "no",),
            )
        if hasattr(self, "history_count_var"):
            self.history_count_var.set(f"{len(rows)} record(s) shown · saved locally in {HISTORY_DB_PATH.name}")

    def delete_selected_history(self) -> None:
        tree = getattr(self, "history_tree", None)
        if tree is None:
            return
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Nothing selected", "Select one or more history rows first.", parent=self.root)
            return
        if not messagebox.askyesno("Delete selected", f"Delete {len(selected)} selected prediction(s)? This cannot be undone.", parent=self.root):
            return
        try:
            deleted = self.history.delete_ids([int(item) for item in selected])
            self._refresh_history_tree()
            self.footer_var.set(f"Deleted {deleted} history record(s)")
        except Exception as exc:
            logger.exception("Could not delete selected history")
            messagebox.showerror("Delete failed", f"Could not delete history records.\n\n{exc}", parent=self.root)

    def clear_history(self) -> None:
        if not messagebox.askyesno("Clear prediction history", "Delete every saved prediction summary? This cannot be undone.", icon="warning", parent=self.root):
            return
        try:
            count = self.history.clear()
            self._refresh_history_tree()
            self.footer_var.set(f"Cleared {count} history record(s)")
        except Exception as exc:
            logger.exception("Could not clear history")
            messagebox.showerror("Clear failed", f"Could not clear history.\n\n{exc}", parent=self.root)

    def export_history(self) -> None:
        destination = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export prediction history",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"churn-history-{datetime.now():%Y%m%d}.csv",
        )
        if not destination:
            return
        try:
            search = self.history_search_var.get() if hasattr(self, "history_search_var") else ""
            count = self.history.export_csv(destination, search=search)
            self.footer_var.set(f"Exported {count} record(s) to CSV")
            messagebox.showinfo("Export complete", f"Exported {count} prediction summary record(s).", parent=self.root)
        except Exception as exc:
            logger.exception("History export failed")
            messagebox.showerror("Export failed", f"Could not export history.\n\n{exc}", parent=self.root)

    # ----- Model & Settings -----------------------------------------------------
    def _build_settings_page(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        model_panel = ttk.Frame(parent, style="Card.TFrame", padding=18)
        model_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 16))
        ttk.Label(model_panel, text="Model health", font=("Segoe UI Semibold", 13), background=self.colors["surface"], foreground=self.colors["text"]).pack(anchor="w")
        ttk.Label(model_panel, text="The saved pipeline includes input imputation, category encoding, scaling, and Logistic Regression.", style="MutedCard.TLabel", wraplength=470, justify="left").pack(anchor="w", pady=(8, 14))
        self._settings_value(model_panel, "Status", "Ready" if self.model_ready else "Not trained" if not self.model_load_error else "Load error")
        self._settings_value(model_panel, "Algorithm", str(self.model_service.metadata.get("model_name", "Logistic Regression")))
        self._settings_value(model_panel, "Training rows", str(self.model_service.metadata.get("training_rows", "—")))
        self._settings_value(model_panel, "Test rows", str(self.model_service.metadata.get("testing_rows", "—")))
        self._settings_value(model_panel, "Last trained", self._format_timestamp(self.model_service.metadata.get("trained_at")))
        actions = ttk.Frame(model_panel, style="Card.TFrame")
        actions.pack(fill="x", pady=(14, 0))
        self.settings_train_button = ttk.Button(actions, text="Train / refresh model", style="Accent.TButton", command=self.start_training, state="disabled" if self.training_busy else "normal")
        self.settings_train_button.pack(side="left")
        self.train_buttons.append(self.settings_train_button)
        ttk.Button(actions, text="Reload saved model", command=self.reload_model).pack(side="left", padx=(8, 0))

        metrics_panel = ttk.Frame(parent, style="Card.TFrame", padding=18)
        metrics_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 16))
        ttk.Label(metrics_panel, text="Evaluation snapshot", font=("Segoe UI Semibold", 13), background=self.colors["surface"], foreground=self.colors["text"]).pack(anchor="w")
        ttk.Label(metrics_panel, text="Metrics are calculated on a held-out stratified test split during training.", style="MutedCard.TLabel", wraplength=430, justify="left").pack(anchor="w", pady=(8, 14))
        metadata = self.model_service.metadata
        metric_rows = [
            ("Accuracy", self._percent(metadata.get("accuracy"))),
            ("Precision · churn Yes", self._percent(metadata.get("precision_yes"))),
            ("Recall · churn Yes", self._percent(metadata.get("recall_yes"))),
            ("F1 · churn Yes", self._percent(metadata.get("f1_yes"))),
            ("Training dataset rows", str(metadata.get("dataset_rows", "—"))),
            ("Dataset file", DATASET_PATH.name),
        ]
        for label, value in metric_rows:
            self._settings_value(metrics_panel, label, value)

        preferences = ttk.Frame(parent, style="Card.TFrame", padding=18)
        preferences.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(preferences, text="Appearance & keyboard", font=("Segoe UI Semibold", 13), background=self.colors["surface"], foreground=self.colors["text"]).pack(anchor="w")
        ttk.Label(preferences, text="Choose a comfortable theme. Your selection is saved locally.", style="MutedCard.TLabel", wraplength=420).pack(anchor="w", pady=(8, 12))
        theme_row = ttk.Frame(preferences, style="Card.TFrame")
        theme_row.pack(fill="x")
        ttk.Label(theme_row, text=f"Current theme: {self.theme_name.title()}", style="CardBody.TLabel").pack(side="left")
        ttk.Button(theme_row, text=self._theme_button_text(), command=self.toggle_theme).pack(side="right")
        ttk.Separator(preferences, orient="horizontal").pack(fill="x", pady=14)
        shortcuts = [
            ("Ctrl + 1–4", "Navigate between pages"),
            ("Ctrl + L", "Toggle light / dark mode"),
            ("Ctrl + Enter", "Open prediction or run it"),
            ("Escape", "Clear the prediction form"),
        ]
        for key, description in shortcuts:
            row = ttk.Frame(preferences, style="Card.TFrame")
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=key, font=("Consolas", 9), background=self.colors["surface_alt"], foreground=self.colors["text"], padding=(7, 4)).pack(side="left")
            ttk.Label(row, text=description, style="MutedCard.TLabel").pack(side="left", padx=(10, 0))

        paths_panel = ttk.Frame(parent, style="Card.TFrame", padding=18)
        paths_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        ttk.Label(paths_panel, text="Local files & privacy", font=("Segoe UI Semibold", 13), background=self.colors["surface"], foreground=self.colors["text"]).pack(anchor="w")
        ttk.Label(paths_panel, text="This app runs locally. The history database stores summary fields only, not the full customer form. Nothing is sent to a server by the application.", style="MutedCard.TLabel", wraplength=430, justify="left").pack(anchor="w", pady=(8, 14))
        for name, path in [
            ("Model file", MODEL_PATH),
            ("Model metadata", MODEL_METADATA_PATH),
            ("Training data", resolve_dataset_path()),
            ("Prediction history", HISTORY_DB_PATH),
        ]:
            ttk.Label(paths_panel, text=name, style="CardTitle.TLabel").pack(anchor="w", pady=(8, 2))
            ttk.Label(paths_panel, text=str(path), style="MutedCard.TLabel", wraplength=430).pack(anchor="w")

    def _settings_value(self, parent: ttk.Frame, label: str, value: str) -> None:
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, style="MutedCard.TLabel").pack(side="left")
        ttk.Label(row, text=value, style="CardBody.TLabel", font=("Segoe UI Semibold", 10)).pack(side="right")

    # ----- Training and background worker --------------------------------------
    def start_training(self) -> None:
        if self.training_busy:
            return
        # Re-check candidate locations at click time. This avoids relying on
        # the import-time DATASET_PATH if the CSV was copied after app startup.
        dataset_candidates = list(dict.fromkeys([
            *DATASET_CANDIDATES,
            DATASET_PATH,
            resolve_dataset_path(),
        ]))
        existing_dataset = next(
            (candidate for candidate in dataset_candidates if candidate.is_file()),
            None,
        )
        if existing_dataset is None:
            checked_paths = "\n".join(f"  - {candidate}" for candidate in dataset_candidates)
            messagebox.showerror(
                "Training dataset not found",
                "The real Telco churn CSV was not found. The app checked these locations:\n\n"
                f"{checked_paths}\n\n"
                "Copy your original Telco-Customer-Churn.csv into a 'data' folder beside the EXE, "
                "or rebuild while the CSV is present in the project's data folder.\n\n"
                "Synthetic training data will not be used.",
                parent=self.root,
            )
            self.footer_var.set("Training blocked · dataset missing")
            return
        self.training_busy = True
        self.footer_var.set("Training model in background…")
        self.progress.grid(row=1, column=1, sticky="e", pady=(8, 0))
        self.progress.start(10)
        for button in self.train_buttons:
            try:
                button.configure(state="disabled")
            except tk.TclError:
                pass
        self._update_model_status()

        def worker() -> None:
            try:
                metadata = self.model_service.train()
                self.event_queue.put(("training_success", metadata))
            except Exception as exc:
                logger.exception("Background training failed")
                self.event_queue.put(("training_error", str(exc)))

        threading.Thread(target=worker, name="churn-model-training", daemon=True).start()

    def _poll_worker_events(self) -> None:
        try:
            while True:
                event, payload = self.event_queue.get_nowait()
                if event == "training_success":
                    self.training_busy = False
                    self.model_ready = True
                    self.model_load_error = None
                    self.progress.stop()
                    self.progress.grid_remove()
                    for button in self.train_buttons:
                        try:
                            button.configure(state="normal")
                        except tk.TclError:
                            pass
                    self.footer_var.set(f"Model trained · test accuracy {float(payload.get('accuracy', 0.0)):.1%}")
                    self.show_page(self.current_page)
                    messagebox.showinfo(
                        "Training complete",
                        "The model was trained and saved successfully.\n\n"
                        f"Test accuracy: {float(payload.get('accuracy', 0.0)):.1%}\n"
                        f"Churn recall: {float(payload.get('recall_yes', 0.0)):.1%}",
                        parent=self.root,
                    )
                elif event == "training_error":
                    self.training_busy = False
                    self.progress.stop()
                    self.progress.grid_remove()
                    for button in self.train_buttons:
                        try:
                            button.configure(state="normal")
                        except tk.TclError:
                            pass
                    self.footer_var.set("Training failed")
                    self._update_model_status()
                    messagebox.showerror("Training failed", str(payload), parent=self.root)
        except queue.Empty:
            pass
        try:
            self.root.after(120, self._poll_worker_events)
        except tk.TclError:
            pass

    def reload_model(self) -> None:
        try:
            loaded = self.model_service.load()
            self.model_ready = loaded
            self.model_load_error = None if loaded else self.model_load_error
            if loaded:
                self.footer_var.set("Saved model loaded")
                self.show_page("Model & Settings")
            else:
                messagebox.showwarning("Model not found", "Train the model first; no saved model file was found.", parent=self.root)
                self._update_model_status()
        except ModelServiceError as exc:
            self.model_ready = False
            self.model_load_error = str(exc)
            messagebox.showerror("Could not load model", str(exc), parent=self.root)
            self._update_model_status()

    # ----- Shared helpers -------------------------------------------------------
    def _make_tree(self, parent: ttk.Frame, columns: list[tuple[str, str, int]], height: int = 10) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=[item[0] for item in columns], show="headings", height=height, selectmode="extended")
        for key, label, width in columns:
            tree.heading(key, text=label)
            tree.column(key, width=width, minwidth=60, anchor="w", stretch=True)
        vertical = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        tree.tag_configure("yes", foreground=self.colors["danger"])
        tree.tag_configure("no", foreground=self.colors["success"])
        return tree

    @staticmethod
    def _display_time(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
            return parsed.strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_timestamp(value: Any) -> str:
        if not value:
            return "—"
        try:
            return datetime.fromisoformat(str(value)).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return str(value)

    @staticmethod
    def _percent(value: Any) -> str:
        try:
            return f"{float(value):.1%}"
        except (TypeError, ValueError):
            return "—"

    def close(self) -> None:
        try:
            self.settings.set("theme", self.theme_name)
        except Exception:
            logger.exception("Could not save settings on close")
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def launch_app() -> None:
    try:
        app = CustomerChurnApp()
        app.run()
    except Exception:
        logger.exception("Fatal application startup error")
        raise
