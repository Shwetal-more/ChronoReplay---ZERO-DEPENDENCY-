"""
ChronoReplay graphical user interface.

Architecture:
- Event Simulator: Generate, validate, and append structured business events.
  Automatic ID generation for user_id and order_id without manual inputs.
- Event History & Time Machine: Chronological business event stream with user separation
  and storage filtering, centralized Time Machine playback, invariant diagnostics,
  and state reconstruction. Excludes file workspace events.
- Workspace & File Recovery: Dedicated directory browser, scanner, version history,
  and non-destructive point-in-time file restoration.

Only Python standard-library modules are used.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from copy import deepcopy

from src.event import Event
from src.validator import EventValidator
from src.store import EventStore
from src.history import VersionHistory
from src.restore import RestoreManager
from src.replay import ReplayEngine
from src.state import StateEngine
from src.simulator import EventSimulator
from src.workspace import WorkspaceManager


class ChronoReplayUI:
    """
    Main ChronoReplay application: Local event-sourced debugging & recovery platform.
    """

    # =========================================================
    # COLORS & PALETTE
    # =========================================================

    BG_COLOR = "#0f172a"
    PANEL_COLOR = "#111c2e"
    CARD_COLOR = "#172338"
    INPUT_COLOR = "#0b1220"

    BORDER_COLOR = "#263650"

    TEXT_COLOR = "#f8fafc"
    MUTED_COLOR = "#94a3b8"

    ACCENT_COLOR = "#38bdf8"
    SUCCESS_COLOR = "#22c55e"
    ERROR_COLOR = "#ef4444"
    WARNING_COLOR = "#f59e0b"

    BUTTON_COLOR = "#263650"
    BUTTON_ACTIVE = "#334766"

    # =========================================================
    # BUSINESS EVENT DEFINITIONS
    # =========================================================

    EVENT_OPTIONS = [
        ("User Created", "user.created"),
        ("Profile Updated", "profile.updated"),
        ("Status Changed", "status.changed"),
        ("Balance Added", "balance.added"),
        ("Order Created", "order.created"),
        ("Payment Completed", "payment.completed"),
        ("Order Updated", "order.updated"),
        ("User Deleted", "user.deleted"),
    ]

    LABEL_TO_TYPE = {label: etype for label, etype in EVENT_OPTIONS}
    TYPE_TO_LABEL = {etype: label for label, etype in EVENT_OPTIONS}

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self, root, database_path="chronoreplay.db"):
        self.root = root
        self.root.title("ChronoReplay — Event Debugging & Workspace Recovery")
        self.root.geometry("1200x800")
        self.root.minsize(960, 640)
        self.root.configure(bg=self.BG_COLOR)

        self.store = EventStore(database_path)
        self.replay_engine = ReplayEngine(self.store)
        self.simulator = EventSimulator(self.store)

        self.selected_event_label_var = tk.StringVar(value="User Created")
        self.status_var = tk.StringVar(value="Ready")
        self.workspace_path_var = tk.StringVar(value=os.path.abspath("."))
        self.selected_workspace_file = tk.StringVar()

        # User & Date filters in Event History
        self.history_user_filter_var = tk.StringVar(value="ALL")
        self.history_date_filter_var = tk.StringVar(value="ALL")

        self.workspace_path = self.workspace_path_var.get()
        self.version_history = VersionHistory(self.store)
        self.restore_manager = RestoreManager(self.workspace_path, self.store)
        self.workspace_manager = WorkspaceManager(self.workspace_path, self.store)

        # Dynamic form field variables
        self.field_vars = {}

        self._configure_styles()
        self._build_header()
        self._build_navigation()
        self._build_scrollable_main()

        self.show_dashboard()

    # =========================================================
    # STYLES
    # =========================================================

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Chrono.TButton",
            background=self.BUTTON_COLOR,
            foreground=self.TEXT_COLOR,
            borderwidth=0,
            padding=(18, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Chrono.TButton",
            background=[("active", self.BUTTON_ACTIVE)],
            foreground=[("active", self.TEXT_COLOR)],
        )

        style.configure(
            "Accent.TButton",
            background=self.ACCENT_COLOR,
            foreground="#07111f",
            borderwidth=0,
            padding=(18, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#7dd3fc")],
            foreground=[("active", "#07111f")],
        )

        style.configure(
            "Chrono.TCombobox",
            fieldbackground=self.INPUT_COLOR,
            background=self.INPUT_COLOR,
            foreground=self.TEXT_COLOR,
            arrowcolor=self.ACCENT_COLOR,
            borderwidth=1,
            padding=8,
            font=("Segoe UI", 10),
        )

        style.configure(
            "Chrono.Vertical.TScrollbar",
            background=self.BUTTON_COLOR,
            troughcolor=self.BG_COLOR,
            bordercolor=self.BG_COLOR,
            arrowcolor=self.TEXT_COLOR,
            width=14,
        )

    # =========================================================
    # HEADER & NAVIGATION
    # =========================================================

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.PANEL_COLOR, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="⏱  CHRONOREPLAY",
            bg=self.PANEL_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 20, "bold"),
        )
        title.pack(side="left", padx=26)

        subtitle = tk.Label(
            header,
            text="LOCAL EVENT-SOURCED DEBUGGING PLATFORM",
            bg=self.PANEL_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 9, "bold"),
        )
        subtitle.pack(side="left")

        status_frame = tk.Frame(header, bg=self.PANEL_COLOR)
        status_frame.pack(side="right", padx=26)

        dot = tk.Label(
            status_frame,
            text="●",
            bg=self.PANEL_COLOR,
            fg=self.SUCCESS_COLOR,
            font=("Segoe UI", 13),
        )
        dot.pack(side="left", padx=(0, 6))

        status = tk.Label(
            status_frame,
            text="SYSTEM READY",
            bg=self.PANEL_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 10, "bold"),
        )
        status.pack(side="left")

    def _build_navigation(self):
        navigation = tk.Frame(self.root, bg=self.BG_COLOR, height=60)
        navigation.pack(fill="x", padx=20, pady=(10, 0))
        navigation.pack_propagate(False)

        ttk.Button(
            navigation,
            text="EVENT SIMULATOR",
            style="Chrono.TButton",
            command=self.show_dashboard,
        ).pack(side="left", padx=4)

        ttk.Button(
            navigation,
            text="EVENT HISTORY & TIME MACHINE",
            style="Chrono.TButton",
            command=self.show_event_history,
        ).pack(side="left", padx=4)

        ttk.Button(
            navigation,
            text="WORKSPACE & FILE RECOVERY",
            style="Chrono.TButton",
            command=self.show_workspace,
        ).pack(side="left", padx=4)

    # =========================================================
    # SCROLLABLE MAIN CONTAINER
    # =========================================================

    def _build_scrollable_main(self):
        outer = tk.Frame(self.root, bg=self.BG_COLOR)
        outer.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = tk.Canvas(outer, bg=self.BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=self.canvas.yview,
            style="Chrono.Vertical.TScrollbar",
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.main_container = tk.Frame(self.canvas, bg=self.BG_COLOR)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.main_container, anchor="nw"
        )

        self.main_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width),
        )

        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            if e.delta
            else None,
        )
        self.canvas.bind_all(
            "<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units")
        )
        self.canvas.bind_all(
            "<Button-5>", lambda e: self.canvas.yview_scroll(3, "units")
        )

    def _clear_main_area(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()
        self.canvas.yview_moveto(0)

    # =========================================================
    # 1. EVENT SIMULATOR VIEW
    # =========================================================

    def show_dashboard(self):
        self._clear_main_area()

        heading = tk.Label(
            self.main_container,
            text="EVENT SIMULATOR",
            bg=self.BG_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 22, "bold"),
        )
        heading.pack(anchor="w", pady=(10, 2))

        subtitle = tk.Label(
            self.main_container,
            text="Simulate business transactions with automatic internal ID generation. ChronoReplay assigns user IDs and order IDs automatically.",
            bg=self.BG_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 11),
        )
        subtitle.pack(anchor="w", pady=(0, 18))

        self._build_active_user_banner()
        self._build_simulator_card()
        self._build_history_preview()

    def _build_active_user_banner(self):
        """Display the active user details, multi-user switcher, and balance, or a warning if none exists."""
        current_user = self.simulator.get_current_user()
        all_users = self.simulator.get_all_users()

        banner_frame = tk.Frame(
            self.main_container,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        banner_frame.pack(fill="x", pady=(0, 16))

        if current_user:
            # Calculate current user balance from state reconstruction
            engine = self.replay_engine.replay_with_engine()[1]
            state = engine.get_state()
            user_data = state.get("users", {}).get(current_user["user_id"], {})
            balance = user_data.get("balance", 0.0)

            # Left side: user badge & user switcher
            left_box = tk.Frame(banner_frame, bg=self.CARD_COLOR)
            left_box.pack(side="left", padx=20, pady=14)

            tk.Label(
                left_box,
                text="👤 CURRENT ACTIVE USER",
                bg=self.CARD_COLOR,
                fg=self.ACCENT_COLOR,
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w")

            user_label = f"{current_user['user_id']}  ─  {current_user['name']} ({current_user['email']})"
            tk.Label(
                left_box,
                text=user_label,
                bg=self.CARD_COLOR,
                fg=self.TEXT_COLOR,
                font=("Segoe UI", 13, "bold"),
            ).pack(anchor="w", pady=(2, 4))

            # Multi-user switcher combobox
            if len(all_users) > 1:
                switcher_box = tk.Frame(left_box, bg=self.CARD_COLOR)
                switcher_box.pack(anchor="w", pady=(2, 0))

                tk.Label(
                    switcher_box,
                    text="Switch User Context:",
                    bg=self.CARD_COLOR,
                    fg=self.MUTED_COLOR,
                    font=("Segoe UI", 8, "bold"),
                ).pack(side="left", padx=(0, 6))

                user_options = [
                    f"{u['user_id']} : {u['name']}" for u in all_users
                ]
                current_val = f"{current_user['user_id']} : {current_user['name']}"
                self.user_switch_var = tk.StringVar(value=current_val)

                user_combo = ttk.Combobox(
                    switcher_box,
                    textvariable=self.user_switch_var,
                    values=user_options,
                    state="readonly",
                    style="Chrono.TCombobox",
                    font=("Segoe UI", 8),
                    width=28,
                )
                user_combo.pack(side="left")
                user_combo.bind("<<ComboboxSelected>>", self._on_user_switched)

            # Right side: balance badge
            right_box = tk.Frame(banner_frame, bg=self.CARD_COLOR)
            right_box.pack(side="right", padx=20, pady=14)

            tk.Label(
                right_box,
                text="WALLET BALANCE",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="e")

            bal_color = self.SUCCESS_COLOR if balance >= 0 else self.ERROR_COLOR
            tk.Label(
                right_box,
                text=f"₹{balance:.2f}",
                bg=self.CARD_COLOR,
                fg=bal_color,
                font=("Segoe UI", 14, "bold"),
            ).pack(anchor="e")

        else:
            no_user_box = tk.Frame(banner_frame, bg=self.CARD_COLOR)
            no_user_box.pack(fill="x", padx=20, pady=14)

            tk.Label(
                no_user_box,
                text="⚠  NO USER EXISTS",
                bg=self.CARD_COLOR,
                fg=self.WARNING_COLOR,
                font=("Segoe UI", 11, "bold"),
            ).pack(side="left")

            tk.Label(
                no_user_box,
                text="— Create a user first before recording orders or payment events.",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 10),
            ).pack(side="left", padx=8)

            tk.Button(
                no_user_box,
                text="CREATE USER",
                bg=self.ACCENT_COLOR,
                fg="#07111f",
                relief="flat",
                bd=0,
                padx=12,
                pady=4,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                command=self._switch_to_create_user,
            ).pack(side="right")

    def _on_user_switched(self, event=None):
        val = getattr(self, "user_switch_var", None)
        if val:
            selected_str = val.get()
            user_id = selected_str.split(":")[0].strip()
            self.simulator.switch_user(user_id)
            self._show_status(f"Switched active user context to {user_id}", success=True)
            self.show_dashboard()

    def _switch_to_create_user(self):
        self.selected_event_label_var.set("User Created")
        self._on_event_dropdown_changed()

    def _build_simulator_card(self):
        card = tk.Frame(
            self.main_container,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        card.pack(fill="x", pady=(0, 20))

        tk.Label(
            card,
            text="SIMULATE EVENT",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w", padx=24, pady=(20, 4))

        tk.Label(
            card,
            text="Select an event to dispatch. IDs are assigned automatically by ChronoReplay.",
            bg=self.CARD_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=24, pady=(0, 16))

        # Event Dropdown
        dropdown_label = tk.Label(
            card,
            text="SELECT EVENT",
            bg=self.CARD_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 9, "bold"),
        )
        dropdown_label.pack(anchor="w", padx=24, pady=(0, 6))

        options = [label for label, _ in self.EVENT_OPTIONS]
        self.event_dropdown = ttk.Combobox(
            card,
            textvariable=self.selected_event_label_var,
            values=options,
            state="readonly",
            style="Chrono.TCombobox",
            font=("Segoe UI", 10),
        )
        self.event_dropdown.pack(fill="x", padx=24, pady=(0, 16))
        self.event_dropdown.bind(
            "<<ComboboxSelected>>", self._on_event_dropdown_changed
        )

        # Dynamic Event Form Container
        self.form_container = tk.Frame(card, bg=self.CARD_COLOR)
        self.form_container.pack(fill="x", padx=24, pady=(0, 16))

        # Status Banner
        bottom_bar = tk.Frame(card, bg=self.CARD_COLOR)
        bottom_bar.pack(fill="x", padx=24, pady=(0, 20))

        self.status_banner = tk.Frame(
            bottom_bar,
            bg=self.INPUT_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        self.status_banner.pack(fill="x", expand=True)

        self.status_icon_label = tk.Label(
            self.status_banner,
            text="●",
            bg=self.INPUT_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 11, "bold"),
        )
        self.status_icon_label.pack(side="left", padx=(10, 6), pady=8)

        self.status_label = tk.Label(
            self.status_banner,
            textvariable=self.status_var,
            bg=self.INPUT_COLOR,
            fg=self.MUTED_COLOR,
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        )
        self.status_label.pack(
            side="left", fill="x", expand=True, padx=(0, 10), pady=8
        )

        # Initial render of the form
        self._render_current_event_form()

    def _on_event_dropdown_changed(self, event=None):
        self._render_current_event_form()

    def _render_current_event_form(self):
        """Render form fields according to selected event type and current user state."""
        for widget in self.form_container.winfo_children():
            widget.destroy()

        self.field_vars = {}
        selected_label = self.selected_event_label_var.get()
        event_type = self.LABEL_TO_TYPE.get(selected_label, "user.created")
        current_user = self.simulator.get_current_user()

        # CASE 1: User Created
        if event_type == "user.created":
            self._render_create_user_form()
            return

        # CASE 2: Event requires a user, but NO user exists yet
        if not current_user:
            self._render_no_user_warning()
            return

        # CASE 3: Event requires a user, and user exists
        self._render_user_bound_event_form(event_type, current_user)

    def _render_create_user_form(self):
        """Form for creating a new user (Name, Email, Age) with automatic ID assignment."""
        form_frame = tk.Frame(self.form_container, bg=self.CARD_COLOR)
        form_frame.pack(fill="x")

        # Name
        self._create_form_row(form_frame, 0, "Name", "name", default="Rahul")
        # Email
        self._create_form_row(
            form_frame, 1, "Email", "email", default="rahul@gmail.com"
        )
        # Age
        self._create_form_row(
            form_frame, 2, "Age", "age", default="25", is_number=True
        )

        btn_row = tk.Frame(form_frame, bg=self.CARD_COLOR)
        btn_row.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))

        ttk.Button(
            btn_row,
            text="CREATE USER",
            style="Accent.TButton",
            command=self._handle_create_user_submit,
        ).pack()

    def _render_no_user_warning(self):
        """Render warning when attempting to record an event without an active user."""
        warn_card = tk.Frame(
            self.form_container,
            bg=self.INPUT_COLOR,
            highlightbackground=self.WARNING_COLOR,
            highlightthickness=1,
        )
        warn_card.pack(fill="x", pady=10)

        inner = tk.Frame(warn_card, bg=self.INPUT_COLOR)
        inner.pack(fill="x", padx=16, pady=14)

        tk.Label(
            inner,
            text="⚠  No user exists.",
            bg=self.INPUT_COLOR,
            fg=self.WARNING_COLOR,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        tk.Label(
            inner,
            text="Create a user first before recording this event.",
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 10))

        tk.Button(
            inner,
            text="Create User",
            bg=self.ACCENT_COLOR,
            fg="#07111f",
            relief="flat",
            bd=0,
            padx=16,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=self._switch_to_create_user,
        ).pack(anchor="w")

    def _render_user_bound_event_form(self, event_type, current_user):
        """Render form fields for events automatically bound to the active user."""
        form_frame = tk.Frame(self.form_container, bg=self.CARD_COLOR)
        form_frame.pack(fill="x")

        # Current User Badge
        user_info_frame = tk.Frame(
            form_frame,
            bg=self.INPUT_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        user_info_frame.grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12)
        )

        tk.Label(
            user_info_frame,
            text=f"Active User Context: {current_user['user_id']} ─ {current_user['name']}",
            bg=self.INPUT_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=12, pady=8)

        row_idx = 1

        if event_type == "balance.added":
            self._create_form_row(
                form_frame,
                row_idx,
                "Amount (₹)",
                "amount",
                default="500.0",
                is_number=True,
            )
            row_idx += 1
            btn_text = "ADD BALANCE"
            btn_cmd = self._handle_add_balance_submit

        elif event_type == "order.created":
            self._create_form_row(
                form_frame,
                row_idx,
                "Order Amount (₹)",
                "amount",
                default="200.0",
                is_number=True,
            )
            row_idx += 1
            btn_text = "CREATE ORDER"
            btn_cmd = self._handle_create_order_submit

        elif event_type == "payment.completed":
            self._create_form_row(
                form_frame,
                row_idx,
                "Amount (₹)",
                "amount",
                default="200.0",
                is_number=True,
            )
            row_idx += 1
            self._create_form_dropdown(
                form_frame,
                row_idx,
                "Payment Method",
                "method",
                ["UPI", "CARD", "NETBANKING", "CASH"],
                default="UPI",
            )
            row_idx += 1
            btn_text = "RECORD PAYMENT"
            btn_cmd = self._handle_complete_payment_submit

        elif event_type == "profile.updated":
            self._create_form_row(
                form_frame,
                row_idx,
                "Name",
                "name",
                default=current_user["name"],
            )
            row_idx += 1
            self._create_form_row(
                form_frame, row_idx, "City", "city", default="Mumbai"
            )
            row_idx += 1
            btn_text = "UPDATE PROFILE"
            btn_cmd = self._handle_update_profile_submit

        elif event_type == "status.changed":
            self._create_form_dropdown(
                form_frame,
                row_idx,
                "Status",
                "status",
                ["active", "suspended", "verified", "inactive"],
                default="active",
            )
            row_idx += 1
            btn_text = "CHANGE STATUS"
            btn_cmd = self._handle_change_status_submit

        elif event_type == "order.updated":
            self._create_form_dropdown(
                form_frame,
                row_idx,
                "Order Status",
                "status",
                ["pending", "paid", "shipped", "completed", "cancelled"],
                default="paid",
            )
            row_idx += 1
            btn_text = "UPDATE ORDER"
            btn_cmd = self._handle_update_order_submit

        elif event_type == "user.deleted":
            tk.Label(
                form_frame,
                text="This will mark the current user as deleted in the event stream.",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 9),
            ).grid(
                row=row_idx, column=0, columnspan=2, sticky="w", pady=(0, 10)
            )
            row_idx += 1
            btn_text = "DELETE USER"
            btn_cmd = self._handle_delete_user_submit

        else:
            btn_text = "DISPATCH EVENT"
            btn_cmd = lambda: None

        btn_row = tk.Frame(form_frame, bg=self.CARD_COLOR)
        btn_row.grid(
            row=row_idx, column=0, columnspan=2, sticky="e", pady=(12, 0)
        )

        ttk.Button(
            btn_row,
            text=btn_text,
            style="Accent.TButton",
            command=btn_cmd,
        ).pack()

    def _create_form_row(
        self, parent, row, label_text, var_key, default="", is_number=False
    ):
        tk.Label(
            parent,
            text=label_text,
            bg=self.CARD_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=6)

        var = tk.StringVar(value=str(default))
        self.field_vars[var_key] = (var, "number" if is_number else "text")

        border = tk.Frame(parent, bg=self.BORDER_COLOR)
        border.grid(row=row, column=1, sticky="ew", pady=6)
        parent.columnconfigure(1, weight=1)

        entry = tk.Entry(
            border,
            textvariable=var,
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            insertbackground=self.TEXT_COLOR,
            relief="flat",
            font=("Segoe UI", 9),
        )
        entry.pack(fill="both", expand=True, padx=1, pady=1, ipady=5)

    def _create_form_dropdown(
        self, parent, row, label_text, var_key, options, default=""
    ):
        tk.Label(
            parent,
            text=label_text,
            bg=self.CARD_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=6)

        var = tk.StringVar(value=default or (options[0] if options else ""))
        self.field_vars[var_key] = (var, "dropdown")

        border = tk.Frame(parent, bg=self.BORDER_COLOR)
        border.grid(row=row, column=1, sticky="ew", pady=6)
        parent.columnconfigure(1, weight=1)

        combo = ttk.Combobox(
            border,
            textvariable=var,
            values=options,
            state="readonly",
            style="Chrono.TCombobox",
            font=("Segoe UI", 9),
        )
        combo.pack(fill="both", expand=True, padx=1, pady=1, ipady=4)

    # ---------------------------------------------------------
    # Form submission handlers
    # ---------------------------------------------------------

    def _handle_create_user_submit(self):
        try:
            name = self.field_vars["name"][0].get().strip()
            email = self.field_vars["email"][0].get().strip()
            age_str = self.field_vars["age"][0].get().strip()

            if not name or not email or not age_str:
                raise ValueError("Name, email, and age are required.")

            age = int(age_str)
            event = self.simulator.create_user(name, email, age)
            user_id = event.data["user_id"]

            self._show_status(
                f"User created successfully — User ID: {user_id}", success=True
            )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_add_balance_submit(self):
        try:
            amount_str = self.field_vars["amount"][0].get().strip()
            amount = float(amount_str)
            event = self.simulator.add_balance(amount)
            self._show_status(
                f"Balance added: ₹{amount:.2f} for user {event.data['user_id']}",
                success=True,
            )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_create_order_submit(self):
        try:
            amount_str = self.field_vars["amount"][0].get().strip()
            amount = float(amount_str)
            event = self.simulator.create_order(amount)
            order_id = event.data["order_id"]
            self._show_status(
                f"Order created successfully — Order ID: {order_id} (₹{amount:.2f})",
                success=True,
            )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_complete_payment_submit(self):
        try:
            amount_str = self.field_vars["amount"][0].get().strip()
            method = self.field_vars["method"][0].get().strip()
            amount = float(amount_str)
            event = self.simulator.complete_payment(amount, method)

            # Check if this caused an invalid state
            diag = self.replay_engine.get_diagnostics_for_event(
                len(self.store.get_all())
            )
            if not diag.get("is_valid", True):
                self._show_status(
                    f"PAYMENT RECORDED WITH INVALID STATE WARNING: {diag.get('reason')}",
                    success=False,
                )
            else:
                self._show_status(
                    f"Payment completed: ₹{amount:.2f} via {method}",
                    success=True,
                )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_update_profile_submit(self):
        try:
            name = self.field_vars["name"][0].get().strip()
            city = self.field_vars["city"][0].get().strip()
            self.simulator.update_profile(name, city)
            self._show_status(
                f"Profile updated: {name}, {city}", success=True
            )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_change_status_submit(self):
        try:
            status = self.field_vars["status"][0].get().strip()
            self.simulator.change_status(status)
            self._show_status(
                f"Status changed to: {status}", success=True
            )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_update_order_submit(self):
        try:
            status = self.field_vars["status"][0].get().strip()
            self.simulator.update_order(status)
            self._show_status(
                f"Order updated to: {status}", success=True
            )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_delete_user_submit(self):
        try:
            self.simulator.delete_user()
            self._show_status("User marked as deleted.", success=True)
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _show_status(self, message, success=True):
        self.status_var.set(message)
        if hasattr(self, "status_label"):
            color = self.SUCCESS_COLOR if success else self.ERROR_COLOR
            icon = "✓" if success else "⚠"
            self.status_label.configure(fg=color)
            self.status_icon_label.configure(text=icon, fg=color)
            self.status_banner.configure(highlightbackground=color)

    def _build_history_preview(self):
        """Preview recent business events at the bottom of the simulator."""
        card = tk.Frame(
            self.main_container,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        card.pack(fill="both", expand=True, pady=(0, 24))

        tk.Label(
            card,
            text="RECENT EVENT STREAM",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w", padx=24, pady=(20, 6))

        # Exclude workspace events
        business_events = [e for e in self.store.get_all() if not e.type.startswith("file.")]

        if not business_events:
            tk.Label(
                card,
                text="No business events recorded in store. Dispatch an event to begin.",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 10),
            ).pack(anchor="w", padx=24, pady=(0, 20))
            return

        preview_table = tk.Frame(card, bg=self.CARD_COLOR)
        preview_table.pack(fill="x", padx=24, pady=(0, 20))

        # Header
        hdr = tk.Frame(preview_table, bg=self.CARD_COLOR)
        hdr.pack(fill="x", pady=(0, 6))
        for col, (title, width) in enumerate(
            [("#", 6), ("USER", 18), ("EVENT", 20), ("DETAILS", 36), ("TIME", 16)]
        ):
            tk.Label(
                hdr,
                text=title,
                width=width,
                anchor="w",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 9, "bold"),
            ).grid(row=0, column=col, padx=4)

        # Show last 6 events
        recent = business_events[-6:]
        start_idx = len(business_events) - len(recent) + 1

        for i, event in enumerate(recent, start=start_idx):
            row = tk.Frame(
                preview_table,
                bg=self.INPUT_COLOR,
                highlightbackground=self.BORDER_COLOR,
                highlightthickness=1,
            )
            row.pack(fill="x", pady=2)

            ts = (
                event.timestamp.split("T")[1].split(".")[0]
                if "T" in event.timestamp
                else event.timestamp
            )

            user_badge = event.data.get("user_id", "System")
            if "name" in event.data and event.type == "user.created":
                user_badge = f"{user_badge} ({event.data['name']})"

            # Details string
            details = []
            for k in ["amount", "order_id", "status", "name"]:
                if k in event.data:
                    val = (
                        f"₹{event.data[k]}"
                        if k == "amount"
                        else str(event.data[k])
                    )
                    details.append(f"{k}: {val}")
            detail_str = " | ".join(details) or str(event.data)

            tk.Label(
                row,
                text=f"#{i}",
                width=6,
                anchor="w",
                bg=self.INPUT_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=8, pady=6)

            tk.Label(
                row,
                text=user_badge,
                width=18,
                anchor="w",
                bg=self.INPUT_COLOR,
                fg=self.ACCENT_COLOR,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=4, pady=6)

            tk.Label(
                row,
                text=event.type,
                width=20,
                anchor="w",
                bg=self.INPUT_COLOR,
                fg=self.TEXT_COLOR,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=4, pady=6)

            tk.Label(
                row,
                text=detail_str,
                width=36,
                anchor="w",
                bg=self.INPUT_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 9),
            ).pack(side="left", padx=4, pady=6)

            tk.Label(
                row,
                text=ts,
                width=16,
                anchor="w",
                bg=self.INPUT_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 8),
            ).pack(side="left", padx=4, pady=6)

    # =========================================================
    # 2. EVENT HISTORY & TIME MACHINE VIEW
    # =========================================================

    def _get_business_events(self):
        """Return all business events (excluding workspace file.* events)."""
        return [e for e in self.store.get_all() if not e.type.startswith("file.")]

    def _get_event_friendly_impact(self, event, state_before=None, state_after=None):
        """Generate a plain-English explanation of what this event changed in the system."""
        etype = event.type
        data = event.data
        uid = data.get("user_id", "System")

        if etype == "user.created":
            name = data.get("name", "User")
            email = data.get("email", "")
            age = data.get("age", "")
            return f"Registered user '{name}' ({email}, age {age}). Initial wallet: ₹0.00."

        elif etype == "balance.added":
            amt = data.get("amount", 0.0)
            bal_before_val = None
            bal_after_val = None
            if state_before and uid in state_before.get("users", {}):
                bal_before_val = state_before["users"][uid].get("balance", 0.0)
            if state_after and uid in state_after.get("users", {}):
                bal_after_val = state_after["users"][uid].get("balance", amt)

            if bal_before_val is not None and bal_after_val is not None:
                if bal_before_val < 0:
                    return f"Topped up ₹{amt:.2f} for {uid}. Balance changed from -₹{abs(bal_before_val):.2f} ➔ ₹{bal_after_val:.2f} (cleared ₹{abs(bal_before_val):.2f} overdraft deficit)."
                return f"Topped up ₹{amt:.2f} for {uid}. Balance changed from ₹{bal_before_val:.2f} ➔ ₹{bal_after_val:.2f}."
            elif bal_after_val is not None:
                return f"Topped up ₹{amt:.2f} into wallet for {uid}. Resulting balance: ₹{bal_after_val:.2f}."
            return f"Topped up ₹{amt:.2f} into wallet for {uid}."

        elif etype == "order.created":
            oid = data.get("order_id", "Order")
            amt = data.get("amount", 0.0)
            return f"Created order {oid} for ₹{amt:.2f} (pending) for {uid}."

        elif etype == "payment.completed":
            amt = data.get("amount", 0.0)
            method = data.get("method", "UPI")
            bal_before_val = None
            bal_after_val = None
            if state_before and uid in state_before.get("users", {}):
                bal_before_val = state_before["users"][uid].get("balance", 0.0)
            if state_after and uid in state_after.get("users", {}):
                bal_after_val = state_after["users"][uid].get("balance", 0.0)

            if bal_before_val is not None and bal_after_val is not None:
                if bal_after_val < 0:
                    return f"Paid ₹{amt:.2f} via {method} for {uid}. Balance changed from ₹{bal_before_val:.2f} ➔ -₹{abs(bal_after_val):.2f} (overdrawn by ₹{abs(bal_after_val):.2f})."
                return f"Paid ₹{amt:.2f} via {method} for {uid}. Balance changed from ₹{bal_before_val:.2f} ➔ ₹{bal_after_val:.2f}."
            return f"Processed payment of ₹{amt:.2f} via {method} for {uid}."

        elif etype == "profile.updated":
            name = data.get("name", "")
            city = data.get("city", "")
            return f"Updated profile for {uid}: Name='{name}', City='{city}'."

        elif etype == "status.changed":
            st = data.get("status", "active")
            return f"Changed account status for {uid} to '{st}'."

        elif etype == "order.updated":
            st = data.get("status", "paid")
            oid = data.get("order_id", "active order")
            return f"Updated order {oid} status to '{st}'."

        elif etype == "user.deleted":
            return f"Marked user {uid} as deleted in the immutable ledger."

        return f"Dispatched {etype} with data: {data}"

    def show_event_history(self):
        self._clear_main_area()

        heading = tk.Label(
            self.main_container,
            text="EVENT HISTORY & TIME MACHINE",
            bg=self.BG_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 22, "bold"),
        )
        heading.pack(anchor="w", pady=(10, 2))

        subtitle = tk.Label(
            self.main_container,
            text="Immutable chronological transaction ledger. Filter by user or launch Time Machine above to step through historical state.",
            bg=self.BG_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 11),
        )
        subtitle.pack(anchor="w", pady=(0, 14))

        # ---------------------------------------------------------
        # Friendly "How this works" Explainer Card
        # ---------------------------------------------------------
        explainer_card = tk.Frame(
            self.main_container,
            bg=self.CARD_COLOR,
            highlightbackground=self.ACCENT_COLOR,
            highlightthickness=1,
        )
        explainer_card.pack(fill="x", pady=(0, 16))

        ex_inner = tk.Frame(explainer_card, bg=self.CARD_COLOR)
        ex_inner.pack(fill="x", padx=20, pady=12)

        tk.Label(
            ex_inner,
            text="💡  HOW EVENT HISTORY & TIME MACHINE WORK",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 4))

        tk.Label(
            ex_inner,
            text="• Ledger: Every action (user creation, wallet top-up, order, payment) is recorded as a permanent event step.\n"
                 "• Time Travel: Click 'LAUNCH TIME MACHINE (STEP-BY-STEP REPLAY)' above to step back in time and inspect live balances & orders.\n"
                 "• Invariant Diagnostics: Automatically checks if any action broke business rules (e.g. negative balances or overspending).",
            bg=self.CARD_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 9),
            justify="left",
        ).pack(anchor="w")

        business_events = self._get_business_events()
        if not business_events:
            card = tk.Frame(
                self.main_container,
                bg=self.CARD_COLOR,
                highlightbackground=self.BORDER_COLOR,
                highlightthickness=1,
            )
            card.pack(fill="both", expand=True, pady=(0, 24))
            tk.Label(
                card,
                text="No business events recorded yet. Go to 'EVENT SIMULATOR' to create users, top-up wallets, or place orders.",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 11),
            ).pack(pady=40)
            return

        all_users = self.simulator.get_all_users()
        active_user = self.history_user_filter_var.get()
        active_date = self.history_date_filter_var.get()

        # ---------------------------------------------------------
        # User & Date Filter Panel
        # ---------------------------------------------------------
        filter_card = tk.Frame(
            self.main_container,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        filter_card.pack(fill="x", pady=(0, 14))

        filter_panel = tk.Frame(filter_card, bg=self.CARD_COLOR)
        filter_panel.pack(fill="x", padx=20, pady=12)

        # Row 1: Filter by User
        user_row = tk.Frame(filter_panel, bg=self.CARD_COLOR)
        user_row.pack(fill="x", pady=(0, 8))

        tk.Label(
            user_row,
            text="👤 1. SELECT USER:",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 10, "bold"),
            width=18,
            anchor="w",
        ).pack(side="left", padx=(0, 8))

        all_user_bg = self.ACCENT_COLOR if active_user == "ALL" else self.BUTTON_COLOR
        all_user_fg = "#07111f" if active_user == "ALL" else self.TEXT_COLOR

        tk.Button(
            user_row,
            text="ALL USERS",
            bg=all_user_bg,
            fg=all_user_fg,
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=lambda: self._set_user_filter("ALL"),
        ).pack(side="left", padx=(0, 6))

        for u in all_users:
            uid = u["user_id"]
            uname = u["name"]
            is_active = active_user == uid
            btn_bg = self.ACCENT_COLOR if is_active else self.BUTTON_COLOR
            btn_fg = "#07111f" if is_active else self.TEXT_COLOR

            tk.Button(
                user_row,
                text=f"{uid} ({uname})",
                bg=btn_bg,
                fg=btn_fg,
                relief="flat",
                bd=0,
                padx=10,
                pady=4,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                command=lambda target=uid: self._set_user_filter(target),
            ).pack(side="left", padx=3)

        # Row 2: Filter by Date (Date-Wise Event History)
        date_row = tk.Frame(filter_panel, bg=self.CARD_COLOR)
        date_row.pack(fill="x", pady=(4, 6))

        tk.Label(
            date_row,
            text="📅 2. SELECT DATE:",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 10, "bold"),
            width=18,
            anchor="w",
        ).pack(side="left", padx=(0, 8))

        # Calculate dates relevant to current user filter
        events_for_user_subset = [
            e for e in business_events
            if active_user == "ALL" or e.data.get("user_id") == active_user
        ]

        # Extract unique dates and calculate counts
        date_counts = {}
        for e in events_for_user_subset:
            d_str = e.timestamp.split("T")[0].split(" ")[0]
            date_counts[d_str] = date_counts.get(d_str, 0) + 1

        all_distinct_dates = sorted(list(date_counts.keys()), reverse=True)

        all_date_bg = self.ACCENT_COLOR if active_date == "ALL" else self.BUTTON_COLOR
        all_date_fg = "#07111f" if active_date == "ALL" else self.TEXT_COLOR

        tk.Button(
            date_row,
            text=f"ALL DATES ({len(events_for_user_subset)})",
            bg=all_date_bg,
            fg=all_date_fg,
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=lambda: self._set_date_filter("ALL"),
        ).pack(side="left", padx=(0, 6))

        for d_val in all_distinct_dates:
            cnt = date_counts[d_val]
            is_active_d = active_date == d_val
            btn_bg = self.ACCENT_COLOR if is_active_d else self.BUTTON_COLOR
            btn_fg = "#07111f" if is_active_d else self.TEXT_COLOR

            tk.Button(
                date_row,
                text=f"📅 {d_val} ({cnt})",
                bg=btn_bg,
                fg=btn_fg,
                relief="flat",
                bd=0,
                padx=10,
                pady=4,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                command=lambda target=d_val: self._set_date_filter(target),
            ).pack(side="left", padx=3)

        # Row 3: Active Filter Summary & Clear Button (if any filter is applied)
        if active_user != "ALL" or active_date != "ALL":
            summary_row = tk.Frame(filter_panel, bg=self.CARD_COLOR)
            summary_row.pack(fill="x", pady=(8, 0))

            filter_text = []
            if active_user != "ALL":
                u_obj = next((u for u in all_users if u["user_id"] == active_user), None)
                u_label = f"{active_user} ({u_obj['name']})" if u_obj else active_user
                filter_text.append(f"User: {u_label}")
            if active_date != "ALL":
                filter_text.append(f"Date: {active_date}")

            tk.Label(
                summary_row,
                text="🔎 Active Filters: " + "  |  ".join(filter_text),
                bg=self.CARD_COLOR,
                fg=self.SUCCESS_COLOR,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=(4, 12))

            tk.Button(
                summary_row,
                text="🔄 RESET ALL FILTERS",
                bg="#334155",
                fg=self.TEXT_COLOR,
                activebackground="#475569",
                activeforeground=self.TEXT_COLOR,
                relief="flat",
                bd=0,
                padx=10,
                pady=3,
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
                command=self._reset_history_filters,
            ).pack(side="left")

        # ---------------------------------------------------------
        # User Storage Summary Box (if filtering specific user)
        # ---------------------------------------------------------
        if active_user != "ALL":
            user_info = next((u for u in all_users if u["user_id"] == active_user), None)
            if user_info:
                engine = self.replay_engine.replay_with_engine()[1]
                state = engine.get_state()
                u_state = state.get("users", {}).get(active_user, {})
                bal = u_state.get("balance", 0.0)
                u_events = [e for e in business_events if e.data.get("user_id") == active_user]
                u_orders = [o for o in state.get("orders", {}).values() if o.get("user_id") == active_user]

                user_summary_box = tk.Frame(
                    self.main_container,
                    bg=self.INPUT_COLOR,
                    highlightbackground=self.BORDER_COLOR,
                    highlightthickness=1,
                )
                user_summary_box.pack(fill="x", pady=(0, 14))

                sum_inner = tk.Frame(user_summary_box, bg=self.INPUT_COLOR)
                sum_inner.pack(fill="x", padx=18, pady=10)

                tk.Label(
                    sum_inner,
                    text=f"📂 USER CONTEXT: {user_info['user_id']} ({user_info['name']})",
                    bg=self.INPUT_COLOR,
                    fg=self.ACCENT_COLOR,
                    font=("Segoe UI", 11, "bold"),
                ).pack(side="left")

                bal_color = self.SUCCESS_COLOR if bal >= 0 else self.ERROR_COLOR
                tk.Label(
                    sum_inner,
                    text=f"Email: {user_info['email']}  |  Total User Events: {len(u_events)}  |  Orders: {len(u_orders)}  |  Wallet Balance: ₹{bal:.2f}",
                    bg=self.INPUT_COLOR,
                    fg=bal_color if bal < 0 else self.TEXT_COLOR,
                    font=("Segoe UI", 10, "bold"),
                ).pack(side="right")

        # Filter events list based on active user AND date filters
        displayed_events_with_index = []
        for idx, e in enumerate(business_events, start=1):
            e_user = e.data.get("user_id")
            e_date = e.timestamp.split("T")[0].split(" ")[0]

            user_match = (active_user == "ALL" or e_user == active_user)
            date_match = (active_date == "ALL" or e_date == active_date)

            if user_match and date_match:
                displayed_events_with_index.append((idx, e))

        # ---------------------------------------------------------
        # Main Event Timeline Card with LAUNCH TIME MACHINE button
        # ---------------------------------------------------------
        card = tk.Frame(
            self.main_container,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        card.pack(fill="both", expand=True, pady=(0, 24))

        top_timeline_bar = tk.Frame(card, bg=self.CARD_COLOR)
        top_timeline_bar.pack(fill="x", padx=20, pady=(18, 10))

        tk.Label(
            top_timeline_bar,
            text="CHRONOLOGICAL EVENT STREAM",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")

        # Main Time Machine Action Button
        total_ev_count = len(business_events)
        tk.Button(
            top_timeline_bar,
            text="⏱  LAUNCH TIME MACHINE (STEP-BY-STEP REPLAY)",
            bg=self.ACCENT_COLOR,
            fg="#07111f",
            activebackground="#7dd3fc",
            activeforeground="#07111f",
            relief="flat",
            bd=0,
            padx=18,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            command=lambda: self.show_time_machine(total_ev_count),
        ).pack(side="right")

        # Header row
        header = tk.Frame(card, bg=self.CARD_COLOR)
        header.pack(fill="x", padx=20, pady=(4, 6))

        for col, (text, width) in enumerate(
            [
                ("STEP", 6),
                ("USER", 16),
                ("EVENT TYPE", 20),
                ("ACTION & IMPACT", 36),
                ("TIME", 14),
                ("ACTIONS", 12),
            ]
        ):
            tk.Label(
                header,
                text=text,
                width=width,
                anchor="w",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 9, "bold"),
            ).grid(row=0, column=col, padx=4, pady=4)

        # Retrieve diagnostics for business events
        diagnostics = self.replay_engine.get_all_diagnostics()
        invalid_map = {
            d["event_index"]: d for d in diagnostics if not d.get("is_valid")
        }

        # Precompute step-by-step state for before/after context
        state_engine = StateEngine()
        step_states = {}
        for idx, ev in enumerate(business_events, start=1):
            s_before = deepcopy(state_engine.get_state())
            state_engine.apply(ev)
            s_after = deepcopy(state_engine.get_state())
            step_states[idx] = (s_before, s_after)

        if not displayed_events_with_index:
            tk.Label(
                card,
                text="No events found for the selected user filter.",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 10),
            ).pack(pady=20)
            return

        for index, event in displayed_events_with_index:
            is_invalid = index in invalid_map
            row_border = self.ERROR_COLOR if is_invalid else self.BORDER_COLOR
            row_bg = "#1f1422" if is_invalid else self.CARD_COLOR

            row = tk.Frame(
                card,
                bg=row_bg,
                highlightbackground=row_border,
                highlightthickness=1,
            )
            row.pack(fill="x", padx=20, pady=3)

            ts = (
                event.timestamp.split("T")[1].split("+")[0]
                if "T" in event.timestamp
                else event.timestamp
            )

            user_display = event.data.get("user_id", "System")
            if "name" in event.data and event.type == "user.created":
                user_display = f"{user_display} ({event.data['name']})"

            # Human-friendly impact summary with before/after state
            s_before, s_after = step_states.get(index, (None, None))
            impact_text = self._get_event_friendly_impact(event, s_before, s_after)

            if is_invalid:
                impact_text = "❌ INVALID: " + impact_text

            tk.Label(
                row,
                text=f"#{index}",
                width=6,
                anchor="w",
                bg=row_bg,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=(8, 0), pady=8)

            tk.Label(
                row,
                text=user_display,
                width=16,
                anchor="w",
                bg=row_bg,
                fg=self.ACCENT_COLOR,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=4, pady=8)

            tk.Label(
                row,
                text=event.type,
                width=20,
                anchor="w",
                bg=row_bg,
                fg=self.ERROR_COLOR if is_invalid else self.TEXT_COLOR,
                font=("Segoe UI", 10, "bold"),
            ).pack(side="left", padx=4, pady=8)

            tk.Label(
                row,
                text=impact_text,
                width=36,
                anchor="w",
                bg=row_bg,
                fg=self.ERROR_COLOR if is_invalid else self.TEXT_COLOR,
                font=("Segoe UI", 9, "bold" if is_invalid else "normal"),
            ).pack(side="left", padx=4, pady=8)

            tk.Label(
                row,
                text=ts,
                width=14,
                anchor="w",
                bg=row_bg,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 9),
            ).pack(side="left", padx=4, pady=8)

            action_box = tk.Frame(row, bg=row_bg)
            action_box.pack(side="right", padx=10, pady=6)

            # View payload data
            tk.Button(
                action_box,
                text="🔍 PAYLOAD",
                bg=self.BUTTON_COLOR,
                fg=self.TEXT_COLOR,
                activebackground=self.BUTTON_ACTIVE,
                activeforeground=self.TEXT_COLOR,
                relief="flat",
                bd=0,
                padx=8,
                pady=5,
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
                command=lambda e=event, n=index: self.view_event(e, n),
            ).pack(side="left")

    def _set_user_filter(self, user_filter):
        self.history_user_filter_var.set(user_filter)
        self.show_event_history()

    def _set_date_filter(self, date_filter):
        self.history_date_filter_var.set(date_filter)
        self.show_event_history()

    def _reset_history_filters(self):
        self.history_user_filter_var.set("ALL")
        self.history_date_filter_var.set("ALL")
        self.show_event_history()

    def view_event(self, event, event_number=None):
        data_text = "\n".join(f"  {k}: {v}" for k, v in event.data.items())
        header = f"Event #{event_number}" if event_number else "Event Metadata"
        messagebox.showinfo(
            header,
            f"Event ID: {event.id}\nType: {event.type}\nVersion: {event.version}\nTimestamp: {event.timestamp}\n\nPayload Data:\n{data_text}",
        )

    # =========================================================
    # TIME MACHINE VIEW
    # =========================================================

    def show_time_machine(self, event_number):
        self._clear_main_area()
        business_events = self._get_business_events()
        if not business_events:
            self.show_event_history()
            return

        total_events = len(business_events)
        event_number = max(1, min(event_number, total_events))
        target_event = business_events[event_number - 1]

        # Calculate state at this step and state before this step
        state_at_step = self.replay_engine.replay_until(event_number)
        state_before = self.replay_engine.replay_until(event_number - 1) if event_number > 1 else None

        heading = tk.Label(
            self.main_container,
            text="TIME MACHINE",
            bg=self.BG_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 22, "bold"),
        )
        heading.pack(anchor="w", pady=(10, 2))

        subtitle = tk.Label(
            self.main_container,
            text="Interactive step-by-step state replayer. Rebuilds the exact state of users, wallets, and orders as they existed at this precise moment in time.",
            bg=self.BG_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 11),
        )
        subtitle.pack(anchor="w", pady=(0, 16))

        # ---------------------------------------------------------
        # 1. Playback & Navigation Controls Card
        # ---------------------------------------------------------
        nav_card = tk.Frame(
            self.main_container,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        nav_card.pack(fill="x", pady=(0, 16))

        top_info = tk.Frame(nav_card, bg=self.CARD_COLOR)
        top_info.pack(fill="x", padx=24, pady=(16, 10))

        user_info = target_event.data.get("user_id", "System")
        tk.Label(
            top_info,
            text=f"REPLAYING STEP #{event_number} OF {total_events}: {target_event.type.upper()}",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")

        # Back to timeline button
        tk.Button(
            top_info,
            text="📋 BACK TO TIMELINE",
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_COLOR,
            activebackground=self.BUTTON_ACTIVE,
            activeforeground=self.TEXT_COLOR,
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=self.show_event_history,
        ).pack(side="right")

        # Step Progress Dots / Tracker
        timeline_bar = tk.Frame(nav_card, bg=self.INPUT_COLOR)
        timeline_bar.pack(fill="x", padx=24, pady=(0, 14), ipady=6)

        window_start = max(1, event_number - 3)
        window_end = min(total_events, event_number + 3)

        timeline_steps = []
        for i in range(window_start, window_end + 1):
            marker = f"● Step #{i}" if i == event_number else f"Step #{i}"
            timeline_steps.append(marker)

        step_display = " ─── ".join(timeline_steps)
        if window_start > 1:
            step_display = "… ─── " + step_display
        if window_end < total_events:
            step_display = step_display + " ─── …"

        tk.Label(
            timeline_bar,
            text=step_display,
            bg=self.INPUT_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=4)

        # Player Control Buttons Row
        controls_frame = tk.Frame(nav_card, bg=self.CARD_COLOR)
        controls_frame.pack(fill="x", padx=24, pady=(0, 18))

        # First step button
        first_btn = tk.Button(
            controls_frame,
            text="⏮ First (#1)",
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_COLOR,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2" if event_number > 1 else "arrow",
            command=lambda: self.show_time_machine(1),
        )
        first_btn.pack(side="left", padx=(0, 6))
        if event_number <= 1:
            first_btn.configure(state="disabled", bg=self.INPUT_COLOR, fg=self.MUTED_COLOR)

        # Previous button
        prev_btn = tk.Button(
            controls_frame,
            text="◀ Previous",
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_COLOR,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2" if event_number > 1 else "arrow",
            command=lambda: self.show_time_machine(max(1, event_number - 1)),
        )
        prev_btn.pack(side="left", padx=(0, 6))
        if event_number <= 1:
            prev_btn.configure(state="disabled", bg=self.INPUT_COLOR, fg=self.MUTED_COLOR)

        # Next button
        next_btn = tk.Button(
            controls_frame,
            text="Next ▶",
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_COLOR,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2" if event_number < total_events else "arrow",
            command=lambda: self.show_time_machine(min(total_events, event_number + 1)),
        )
        next_btn.pack(side="left", padx=(0, 6))
        if event_number >= total_events:
            next_btn.configure(state="disabled", bg=self.INPUT_COLOR, fg=self.MUTED_COLOR)

        # Latest step button
        latest_btn = tk.Button(
            controls_frame,
            text="Latest (Step #{}) ⏭".format(total_events),
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_COLOR,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2" if event_number < total_events else "arrow",
            command=lambda: self.show_time_machine(total_events),
        )
        latest_btn.pack(side="left", padx=(0, 16))
        if event_number >= total_events:
            latest_btn.configure(state="disabled", bg=self.INPUT_COLOR, fg=self.MUTED_COLOR)

        # Quick Jump Dropdown
        jump_frame = tk.Frame(controls_frame, bg=self.CARD_COLOR)
        jump_frame.pack(side="left")

        tk.Label(
            jump_frame,
            text="Jump To:",
            bg=self.CARD_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 6))

        jump_options = [f"Step #{idx}: {ev.type}" for idx, ev in enumerate(business_events, 1)]
        jump_var = tk.StringVar(value=f"Step #{event_number}: {target_event.type}")
        jump_combo = ttk.Combobox(
            jump_frame,
            textvariable=jump_var,
            values=jump_options,
            state="readonly",
            style="Chrono.TCombobox",
            font=("Segoe UI", 8),
            width=24,
        )
        jump_combo.pack(side="left")
        jump_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self.show_time_machine(
                int(jump_var.get().split(":")[0].replace("Step #", "").strip())
            ),
        )

        # Action button on current step
        if event_number < total_events:
            tk.Button(
                controls_frame,
                text=f"⏪ ROLLBACK STORE TO STEP #{event_number}",
                bg=self.ERROR_COLOR,
                fg="#ffffff",
                activebackground="#f87171",
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                padx=14,
                pady=6,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                command=lambda: self._rollback_to_event(event_number),
            ).pack(side="right")
        else:
            tk.Button(
                controls_frame,
                text="⚡ SIMULATE NEW EVENT",
                bg=self.ACCENT_COLOR,
                fg="#07111f",
                relief="flat",
                bd=0,
                padx=14,
                pady=6,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                command=self.show_dashboard,
            ).pack(side="right")

        # ---------------------------------------------------------
        # 2. "⚡ What Changed In This Step" Card
        # ---------------------------------------------------------
        impact_card = tk.Frame(
            self.main_container,
            bg=self.INPUT_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        impact_card.pack(fill="x", pady=(0, 16))

        imp_inner = tk.Frame(impact_card, bg=self.INPUT_COLOR)
        imp_inner.pack(fill="x", padx=20, pady=12)

        tk.Label(
            imp_inner,
            text="⚡  WHAT CHANGED AT THIS STEP",
            bg=self.INPUT_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        friendly_impact = self._get_event_friendly_impact(target_event, state_before, state_at_step)
        tk.Label(
            imp_inner,
            text=f"Event #{event_number} ({target_event.type}): {friendly_impact}",
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 11),
            wraplength=1050,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # ---------------------------------------------------------
        # 3. Invariant Diagnostic Banner (Health Check)
        # ---------------------------------------------------------
        diag = self.replay_engine.get_diagnostics_for_event(event_number)
        if not diag.get("is_valid", True):
            warn_card = tk.Frame(
                self.main_container,
                bg="#260f1b",
                highlightbackground=self.ERROR_COLOR,
                highlightthickness=2,
            )
            warn_card.pack(fill="x", pady=(0, 16))

            w_inner = tk.Frame(warn_card, bg="#260f1b")
            w_inner.pack(fill="x", padx=20, pady=14)

            tk.Label(
                w_inner,
                text="❌  SYSTEM INVARIANT VIOLATION DETECTED",
                bg="#260f1b",
                fg=self.ERROR_COLOR,
                font=("Segoe UI", 13, "bold"),
            ).pack(anchor="w")

            reason_str = diag.get("reason", "Invariant violated.")
            if "deficit" in diag:
                reason_str += f" (Deficit: ₹{diag['deficit']:.2f}, Balance before: ₹{diag['balance_before']:.2f})"

            tk.Label(
                w_inner,
                text=f"This event resulted in an invalid state: {reason_str}\nChronoReplay identified this invariant violation deterministically during state replay.",
                bg="#260f1b",
                fg="#fca5a5",
                font=("Segoe UI", 10),
                justify="left",
            ).pack(anchor="w", pady=(4, 0))
        else:
            ok_card = tk.Frame(
                self.main_container,
                bg=self.CARD_COLOR,
                highlightbackground=self.SUCCESS_COLOR,
                highlightthickness=1,
            )
            ok_card.pack(fill="x", pady=(0, 16))

            ok_inner = tk.Frame(ok_card, bg=self.CARD_COLOR)
            ok_inner.pack(fill="x", padx=20, pady=8)

            tk.Label(
                ok_inner,
                text="✓  SYSTEM STATE INTEGRITY: VALID (All wallet invariants & order consistency rules passed at this step)",
                bg=self.CARD_COLOR,
                fg=self.SUCCESS_COLOR,
                font=("Segoe UI", 10, "bold"),
            ).pack(side="left")

        # ---------------------------------------------------------
        # 4. Visual State Cards Dashboard
        # ---------------------------------------------------------
        users = state_at_step.get("users", {})
        orders = state_at_step.get("orders", {})
        payments = state_at_step.get("payments", [])

        state_dashboard = tk.Frame(self.main_container, bg=self.BG_COLOR)
        state_dashboard.pack(fill="x", pady=(0, 16))

        # Left Column: User Wallets
        left_col = tk.Frame(
            state_dashboard,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(
            left_col,
            text=f"👤 USER WALLETS ({len(users)})",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=16, pady=(14, 10))

        if users:
            for uid, user in users.items():
                u_card = tk.Frame(
                    left_col,
                    bg=self.INPUT_COLOR,
                    highlightbackground=self.BORDER_COLOR,
                    highlightthickness=1,
                )
                u_card.pack(fill="x", padx=14, pady=4)

                u_top = tk.Frame(u_card, bg=self.INPUT_COLOR)
                u_top.pack(fill="x", padx=12, pady=(8, 4))

                tk.Label(
                    u_top,
                    text=f"{user.get('name', 'User')} ({uid})",
                    bg=self.INPUT_COLOR,
                    fg=self.TEXT_COLOR,
                    font=("Segoe UI", 11, "bold"),
                ).pack(side="left")

                bal = user.get("balance", 0.0)
                bal_color = self.SUCCESS_COLOR if bal >= 0 else self.ERROR_COLOR
                tk.Label(
                    u_top,
                    text=f"₹{bal:.2f}",
                    bg=self.INPUT_COLOR,
                    fg=bal_color,
                    font=("Segoe UI", 12, "bold"),
                ).pack(side="right")

                u_bot = tk.Frame(u_card, bg=self.INPUT_COLOR)
                u_bot.pack(fill="x", padx=12, pady=(0, 8))

                status_text = user.get("status", "active").upper()
                tk.Label(
                    u_bot,
                    text=f"Email: {user.get('email', 'N/A')}  •  Status: {status_text}",
                    bg=self.INPUT_COLOR,
                    fg=self.MUTED_COLOR,
                    font=("Segoe UI", 9),
                ).pack(side="left")
        else:
            tk.Label(
                left_col,
                text="No users created as of this step.",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 10),
            ).pack(padx=16, pady=20)

        # Right Column: Orders & Payments
        right_col = tk.Frame(
            state_dashboard,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        right_col.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(
            right_col,
            text=f"📦 ORDERS ({len(orders)}) & PAYMENTS ({len(payments)})",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=16, pady=(14, 10))

        if orders:
            for oid, order in orders.items():
                o_card = tk.Frame(
                    right_col,
                    bg=self.INPUT_COLOR,
                    highlightbackground=self.BORDER_COLOR,
                    highlightthickness=1,
                )
                o_card.pack(fill="x", padx=14, pady=4)

                o_top = tk.Frame(o_card, bg=self.INPUT_COLOR)
                o_top.pack(fill="x", padx=12, pady=(8, 4))

                tk.Label(
                    o_top,
                    text=f"Order {oid} ({order.get('user_id', '')})",
                    bg=self.INPUT_COLOR,
                    fg=self.TEXT_COLOR,
                    font=("Segoe UI", 10, "bold"),
                ).pack(side="left")

                amt = order.get("amount", 0.0)
                st = order.get("status", "pending").upper()
                st_color = self.SUCCESS_COLOR if st == "PAID" or st == "COMPLETED" else self.WARNING_COLOR

                tk.Label(
                    o_top,
                    text=f"₹{amt:.2f}  [{st}]",
                    bg=self.INPUT_COLOR,
                    fg=st_color,
                    font=("Segoe UI", 10, "bold"),
                ).pack(side="right")
        else:
            tk.Label(
                right_col,
                text="No orders recorded as of this step.",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 10),
            ).pack(padx=16, pady=20)

        # ---------------------------------------------------------
        # 5. Raw State Inspection Text Area (Collapsible/Full view)
        # ---------------------------------------------------------
        raw_card = tk.Frame(
            self.main_container,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        raw_card.pack(fill="both", expand=True, pady=(0, 24))

        raw_top = tk.Frame(raw_card, bg=self.CARD_COLOR)
        raw_top.pack(fill="x", padx=20, pady=(14, 6))

        tk.Label(
            raw_top,
            text=f"🔍 COMPLETE RECONSTRUCTED STATE SNAPSHOT (STEP #{event_number})",
            bg=self.CARD_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        state_frame = tk.Frame(raw_card, bg=self.INPUT_COLOR)
        state_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self.replay_state_text = tk.Text(
            state_frame,
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            insertbackground=self.TEXT_COLOR,
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
            height=10,
        )
        self.replay_state_text.pack(fill="both", expand=True, padx=10, pady=8)
        self._display_replay_state(state_at_step, event_number)

    def _display_replay_state(self, state, event_number):
        self.replay_state_text.configure(state="normal")
        self.replay_state_text.delete("1.0", "end")

        users = state.get("users", {})
        orders = state.get("orders", {})
        payments = state.get("payments", [])

        total_balance = sum(u.get("balance", 0) for u in users.values())
        summary = f"STATE SNAPSHOT #{event_number}  |  Users: {len(users)}  |  Orders: {len(orders)}  |  Payments: {len(payments)}  |  Total System Wallet Balance: ₹{total_balance:.2f}\n"
        self.replay_state_text.insert("end", summary + "=" * 68 + "\n\n")

        self.replay_state_text.insert(
            "end", "USERS & WALLETS\n────────────────────────────────────────\n"
        )
        if users:
            for uid, user in users.items():
                self.replay_state_text.insert(
                    "end",
                    f"  • User: {user.get('name', '')} ({uid})\n"
                    f"    Email  : {user.get('email', '')}\n"
                    f"    Status : {user.get('status', 'active')}\n"
                    f"    Balance: ₹{user.get('balance', 0):.2f}\n\n",
                )
        else:
            self.replay_state_text.insert("end", "  No users in state.\n\n")

        self.replay_state_text.insert(
            "end", "ORDERS\n────────────────────────────────────────\n"
        )
        if orders:
            for oid, order in orders.items():
                paid = order.get("paid_amount", 0.0)
                self.replay_state_text.insert(
                    "end",
                    f"  • Order ID: {oid}\n"
                    f"    User   : {order.get('user_id', '')}\n"
                    f"    Amount : ₹{order.get('amount', 0):.2f}\n"
                    f"    Payment: ₹{paid:.2f}\n"
                    f"    Status : {order.get('status', 'pending')}\n\n",
                )
        else:
            self.replay_state_text.insert("end", "  No orders in state.\n\n")

        self.replay_state_text.insert(
            "end", "PAYMENTS\n────────────────────────────────────────\n"
        )
        if payments:
            for p in payments:
                self.replay_state_text.insert(
                    "end",
                    f"  • Payment: ₹{p.get('amount', 0):.2f} via {p.get('method', 'UPI')} (User: {p.get('user_id')})\n",
                )
        else:
            self.replay_state_text.insert("end", "  No payments recorded.\n")

        self.replay_state_text.configure(state="disabled")

    def _rollback_to_event(self, event_number):
        business_events = self._get_business_events()
        if event_number < 1 or event_number > len(business_events):
            return
        target_event = business_events[event_number - 1]
        deleted_count = len(business_events) - event_number

        confirm = messagebox.askyesno(
            "Rollback Event Store",
            f"Are you sure you want to rollback the database to Step #{event_number} ({target_event.type})?\n\n"
            f"This will permanently delete the subsequent {deleted_count} event(s) (Steps #{event_number + 1} to #{len(business_events)}) from the event store.\n\n"
            f"The application state and Event Simulator will be rewound to this exact point in time.",
        )
        if confirm:
            self.store.delete_events_after(target_event.id)
            # Switch active user in simulator if possible
            state = self.replay_engine.replay_until(event_number)
            users = state.get("users", {})
            if users:
                last_user_id = list(users.keys())[-1]
                last_user = users[last_user_id]
                self.simulator.select_user(
                    last_user_id, last_user.get("name"), last_user.get("email")
                )
            messagebox.showinfo(
                "Rollback Completed",
                f"Successfully rewound event store to Step #{event_number}.\n{deleted_count} subsequent event(s) removed.\nLive state is now restored to this exact point in time.",
            )
            self.show_dashboard()

    # =========================================================
    # 3. WORKSPACE & FILE RECOVERY VIEW
    # =========================================================

    def show_workspace(self):
        self._clear_main_area()

        heading = tk.Label(
            self.main_container,
            text="WORKSPACE & FILE RECOVERY",
            bg=self.BG_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 22, "bold"),
        )
        heading.pack(anchor="w", pady=(10, 2))

        subtitle = tk.Label(
            self.main_container,
            text="File time machine with non-destructive restoration. Scan workspace to detect and record changes, inspect version history, and restore physical files.",
            bg=self.BG_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 11),
        )
        subtitle.pack(anchor="w", pady=(0, 18))

        # Top Directory & Action Bar Card
        dir_card = tk.Frame(
            self.main_container,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        dir_card.pack(fill="x", pady=(0, 18))

        tk.Label(
            dir_card,
            text="ACTIVE WORKSPACE DIRECTORY",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        selector_frame = tk.Frame(dir_card, bg=self.CARD_COLOR)
        selector_frame.pack(fill="x", padx=24, pady=(0, 16))

        border = tk.Frame(selector_frame, bg=self.BORDER_COLOR)
        border.pack(side="left", fill="x", expand=True, padx=(0, 10))

        tk.Entry(
            border,
            textvariable=self.workspace_path_var,
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            insertbackground=self.TEXT_COLOR,
            relief="flat",
            font=("Segoe UI", 10),
        ).pack(fill="both", expand=True, padx=1, pady=1, ipady=5)

        tk.Button(
            selector_frame,
            text="SELECT WORKSPACE",
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_COLOR,
            activebackground=self.BUTTON_ACTIVE,
            activeforeground=self.TEXT_COLOR,
            relief="flat",
            bd=0,
            padx=16,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=self._browse_workspace_folder,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            selector_frame,
            text="SCAN WORKSPACE",
            bg=self.ACCENT_COLOR,
            fg="#07111f",
            activebackground="#7dd3fc",
            activeforeground="#07111f",
            relief="flat",
            bd=0,
            padx=18,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=self.scan_workspace,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            selector_frame,
            text="REFRESH",
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_COLOR,
            activebackground=self.BUTTON_ACTIVE,
            activeforeground=self.TEXT_COLOR,
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=self._populate_workspace_files,
        ).pack(side="left")

        # Two-column layout: Left = Files list, Right = Version History
        columns_frame = tk.Frame(self.main_container, bg=self.BG_COLOR)
        columns_frame.pack(fill="both", expand=True, pady=(0, 24))

        # Left Card: Workspace Files
        left_card = tk.Frame(
            columns_frame,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(
            left_card,
            text="WORKSPACE FILES",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=18, pady=(16, 4))

        folder_name = (
            os.path.basename(self.workspace_path_var.get()) or "workspace"
        )
        tk.Label(
            left_card,
            text=f"📁 {folder_name}",
            bg=self.CARD_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=18, pady=(0, 10))

        files_listbox_frame = tk.Frame(left_card, bg=self.INPUT_COLOR)
        files_listbox_frame.pack(
            fill="both", expand=True, padx=18, pady=(0, 18)
        )

        self.files_listbox = tk.Listbox(
            files_listbox_frame,
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            selectbackground=self.BUTTON_ACTIVE,
            relief="flat",
            bd=0,
            font=("Consolas", 10),
        )
        self.files_listbox.pack(fill="both", expand=True, padx=8, pady=8)
        self.files_listbox.bind(
            "<<ListboxSelect>>", self._on_workspace_file_selected
        )

        # Right Card: Version History
        self.right_card = tk.Frame(
            columns_frame,
            bg=self.CARD_COLOR,
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
        )
        self.right_card.pack(
            side="right", fill="both", expand=True, padx=(10, 0)
        )

        self.version_history_title = tk.Label(
            self.right_card,
            text="VERSION HISTORY",
            bg=self.CARD_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 13, "bold"),
        )
        self.version_history_title.pack(anchor="w", padx=18, pady=(16, 4))

        self.version_container = tk.Frame(self.right_card, bg=self.CARD_COLOR)
        self.version_container.pack(
            fill="both", expand=True, padx=18, pady=(0, 18)
        )

        # Populate workspace file list
        self._populate_workspace_files()

    def _browse_workspace_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self.workspace_path_var.get()
        )
        if folder:
            self.workspace_path_var.set(os.path.abspath(folder))
            self.restore_manager = RestoreManager(
                self.workspace_path_var.get(), self.store
            )
            self.workspace_manager = WorkspaceManager(
                self.workspace_path_var.get(), self.store
            )
            self.show_workspace()

    def scan_workspace(self):
        try:
            summary = self.workspace_manager.scan_and_record_changes()
            self._populate_workspace_files()
            msg = (
                f"Scan Complete: {summary['total_scanned']} files scanned.\n"
                f"({summary['created']} Created, {summary['modified']} Modified, "
                f"{summary['unchanged']} Unchanged, {summary['deleted']} Deleted)"
            )
            messagebox.showinfo("Workspace Scan", msg)
            return summary
        except Exception as exc:
            messagebox.showerror("Scan Error", str(exc))

    def _populate_workspace_files(self):
        """Populate the workspace file list with statuses."""
        self.files_listbox.delete(0, "end")

        file_statuses = self.workspace_manager.get_workspace_files_with_status()
        if not file_statuses:
            self.files_listbox.insert(
                "end", "  (No files found. Click SCAN WORKSPACE)"
            )
            return

        for item in file_statuses:
            path = item["file_path"]
            status = item["status"]
            icon = "📄" if item["is_on_disk"] else "🗑"
            self.files_listbox.insert("end", f"  {icon} {path}  [{status}]")

    def _on_workspace_file_selected(self, event=None):
        selection = self.files_listbox.curselection()
        if not selection:
            return

        raw_value = self.files_listbox.get(selection[0])
        clean_path = (
            raw_value.replace("📄", "").replace("🗑", "").split("[")[0].strip()
        )
        self.selected_workspace_file.set(clean_path)

        for widget in self.version_container.winfo_children():
            widget.destroy()

        self.version_history_title.configure(
            text=f"VERSION HISTORY: {clean_path}"
        )

        try:
            history = self.version_history.get_file_history(clean_path)
        except ValueError as exc:
            tk.Label(
                self.version_container,
                text=str(exc),
                bg=self.CARD_COLOR,
                fg=self.ERROR_COLOR,
                font=("Segoe UI", 10),
            ).pack(pady=20)
            return

        if not history:
            tk.Label(
                self.version_container,
                text="No historical versions recorded. Click [SCAN WORKSPACE] to track changes.",
                bg=self.CARD_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 10),
            ).pack(pady=20)
            return

        # Render version history cards
        for version in history:
            row = tk.Frame(
                self.version_container,
                bg=self.INPUT_COLOR,
                highlightbackground=self.BORDER_COLOR,
                highlightthickness=1,
            )
            row.pack(fill="x", pady=3)

            ts = version.timestamp
            if "T" in ts:
                ts = ts.split("T")[1].split("+")[0]

            if version.is_deleted():
                action_text = "DELETED"
                action_color = self.ERROR_COLOR
            elif version.event_type == "file.restored":
                action_text = "RESTORED"
                action_color = self.SUCCESS_COLOR
            elif version.event_type == "file.created":
                action_text = "CREATED"
                action_color = self.ACCENT_COLOR
            else:
                action_text = "MODIFIED"
                action_color = self.WARNING_COLOR

            info_frame = tk.Frame(row, bg=self.INPUT_COLOR)
            info_frame.pack(
                side="left", fill="x", expand=True, padx=10, pady=8
            )

            tk.Label(
                info_frame,
                text=f"VERSION #{version.version}  •  {action_text}",
                bg=self.INPUT_COLOR,
                fg=action_color,
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w")

            tk.Label(
                info_frame,
                text=f"Time: {ts} | Snapshot: {version.snapshot_id or 'Deleted'}",
                bg=self.INPUT_COLOR,
                fg=self.MUTED_COLOR,
                font=("Segoe UI", 8),
            ).pack(anchor="w", pady=(2, 0))

            if version.snapshot_id:
                tk.Button(
                    row,
                    text="RESTORE",
                    bg=self.ACCENT_COLOR,
                    fg="#07111f",
                    relief="flat",
                    bd=0,
                    padx=10,
                    pady=4,
                    font=("Segoe UI", 8, "bold"),
                    cursor="hand2",
                    command=lambda v=version, p=clean_path: self._restore_file_version(
                        p, v
                    ),
                ).pack(side="right", padx=(4, 8), pady=6)

                tk.Button(
                    row,
                    text="VIEW",
                    bg=self.BUTTON_COLOR,
                    fg=self.TEXT_COLOR,
                    relief="flat",
                    bd=0,
                    padx=10,
                    pady=4,
                    font=("Segoe UI", 8, "bold"),
                    cursor="hand2",
                    command=lambda v=version: self._view_file_version(v),
                ).pack(side="right", padx=4, pady=6)

    def _view_file_version(self, version):
        import difflib
        curr = self.version_history.get_content(version.file_path, version.version) or ""
        prev = self.version_history.get_content(version.file_path, version.version - 1) or "" if version.version > 1 else ""
        
        diff = list(difflib.unified_diff(
            prev.splitlines(), curr.splitlines(),
            fromfile=f"v{version.version-1}" if version.version > 1 else "initial",
            tofile=f"v{version.version}",
            lineterm=""
        ))
        change_text = "\n".join(diff) if diff else (curr if curr else "(Empty or no changes)")

        viewer = tk.Toplevel(self.root)
        viewer.title(f"Changes in v{version.version}: {version.file_path}")
        viewer.geometry("560x360")
        viewer.configure(bg=self.BG_COLOR)

        tk.Label(
            viewer,
            text=f"CHANGE IN v{version.version} • {version.file_path}",
            bg=self.BG_COLOR,
            fg=self.ACCENT_COLOR,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 4))

        tk.Label(
            viewer,
            text=f"Event: {version.event_type} | Time: {version.timestamp[:19] if version.timestamp else 'N/A'}",
            bg=self.BG_COLOR,
            fg=self.MUTED_COLOR,
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        text_area = tk.Text(
            viewer,
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            font=("Consolas", 9),
            relief="flat",
            wrap="none",
        )
        text_area.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        text_area.insert("1.0", change_text)
        text_area.configure(state="disabled")

    def _restore_file_version(self, file_path, version):
        confirm = messagebox.askyesno(
            "Confirm File Restore",
            f"Restore {file_path} to Version #{version.version}?\n\n"
            f"Snapshot ID: {version.snapshot_id or 'N/A'}\n"
            "This will physically overwrite the file on disk with historical lines and record a file.restored event.",
        )
        if confirm:
            try:
                if version.snapshot_id:
                    self.restore_manager.restore(version.snapshot_id)
                else:
                    self.restore_manager.restore_version(file_path, version.version)

                # Re-scan workspace so disk state and event stores stay in sync
                self.workspace_manager.scan_and_record_changes()

                restored_content = self.version_history.get_content(file_path, version.version)
                line_count = len(restored_content.splitlines()) if restored_content else 0

                messagebox.showinfo(
                    "File Restored Successfully",
                    f"✓ {file_path} has been restored to Version #{version.version}!\n\n"
                    f"• Restored Lines: {line_count}\n"
                    f"• Target File: {os.path.join(self.restore_manager.workspace_path, file_path)}\n\n"
                    f"The deleted lines are now fully restored on disk.",
                )
                self._populate_workspace_files()
                self._on_workspace_file_selected()
            except Exception as exc:
                messagebox.showerror("Restore Failed", str(exc))

    # Compatibility helper methods
    def refresh_history(self):
        if hasattr(self, "_refresh_history_preview"):
            self._refresh_history_preview()

    def refresh_workspace_files(self):
        self._populate_workspace_files()


def main():
    root = tk.Tk()
    ChronoReplayUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
