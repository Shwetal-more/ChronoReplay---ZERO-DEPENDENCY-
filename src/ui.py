"""
ChronoReplay graphical user interface.

Architecture:
- Event Simulator: Generate, validate, and append structured business events.
  Automatic ID generation for user_id and order_id without manual inputs.
- Event History & Time Machine: Chronological business event stream with user separation
  and storage filtering, centralized Time Machine playback, invariant diagnostics,
  and state reconstruction. Excludes file workspace events.
- Workspace & File Recovery: Dedicated directory browser, scanner, version history,
  diff inspection, and non-destructive point-in-time file restoration.

Only Python standard-library modules are used.
"""

import os
import difflib
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from copy import deepcopy

from src.event import Event
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

    def __init__(self, root, database_path=None):
        self.root = root
        self.root.title("ChronoReplay — Event Debugging & Workspace Recovery")
        self.root.geometry("1200x800")
        self.root.minsize(960, 640)
        self.root.configure(bg=self.BG_COLOR)

        self.selected_event_label_var = tk.StringVar(value="User Created")
        self.status_var = tk.StringVar(value="Ready")
        self.workspace_path_var = tk.StringVar(value=os.path.abspath("."))
        self.selected_workspace_file = tk.StringVar()

        # User & Date filters in Event History
        self.history_user_filter_var = tk.StringVar(value="ALL")
        self.history_date_filter_var = tk.StringVar(value="ALL")

        # Initialize event engine & stores
        self.main_db_path = database_path or os.path.join(
            os.path.expanduser("~"),
            ".chronoreplay",
            "chronoreplay.db"
            )
        os.makedirs(os.path.dirname(self.main_db_path), exist_ok=True)
        self.store = EventStore(self.main_db_path)
        self.version_history = VersionHistory(self.store)
        self.replay_engine = ReplayEngine(self.store)
        self.simulator = EventSimulator(self.store)

        # Initialize workspace engine
        self._sync_workspace_path(self.workspace_path_var.get())

        # Dynamic form field variables
        self.field_vars = {}

        self._configure_styles()
        self._build_header()
        self._build_navigation()
        self._build_scrollable_main()

        self.show_dashboard()

    def _sync_workspace_path(self, target_path=None):
        """Synchronize active workspace directory for file tracking."""
        if target_path is None:
            target_path = self.workspace_path_var.get()
        abs_path = os.path.abspath(str(target_path).strip())
        self.workspace_path = abs_path
        self.workspace_path_var.set(abs_path)

        self.restore_manager = RestoreManager(abs_path, self.store)
        self.workspace_manager = WorkspaceManager(abs_path, self.store)

    # =========================================================
    # UI COMPONENT HELPERS (REDUCING REPETITION & BOILERPLATE)
    # =========================================================

    def make_label(
        self, parent, text="", fg=None, bg=None, font=None, bold=False, size=10, **kwargs
    ):
        """Standardized label factory with theme defaults."""
        fg = fg or self.TEXT_COLOR
        if bg is None:
            try:
                bg = parent.cget("bg")
            except Exception:
                bg = self.BG_COLOR
        font = font or ("Segoe UI", size, "bold" if bold else "normal")
        return tk.Label(parent, text=text, fg=fg, bg=bg, font=font, **kwargs)

    def make_button(
        self,
        parent,
        text="",
        command=None,
        bg=None,
        fg=None,
        active_bg=None,
        active_fg=None,
        font=None,
        bold=True,
        size=9,
        padx=12,
        pady=5,
        cursor="hand2",
        **kwargs,
    ):
        """Standardized button factory with dark-theme defaults."""
        bg = bg or self.BUTTON_COLOR
        fg = fg or self.TEXT_COLOR
        active_bg = active_bg or self.BUTTON_ACTIVE
        active_fg = active_fg or fg
        font = font or ("Segoe UI", size, "bold" if bold else "normal")

        opts = {
            "text": text,
            "command": command,
            "bg": bg,
            "fg": fg,
            "activebackground": active_bg,
            "activeforeground": active_fg,
            "font": font,
            "padx": padx,
            "pady": pady,
            "relief": "flat",
            "bd": 0,
            "cursor": cursor,
        }
        opts.update(kwargs)
        return tk.Button(parent, **opts)

    def make_accent_button(
        self, parent, text="", command=None, font=None, bold=True, size=9, padx=14, pady=6, **kwargs
    ):
        """Standardized prominent accent-colored action button."""
        return self.make_button(
            parent,
            text=text,
            command=command,
            bg=self.ACCENT_COLOR,
            fg="#07111f",
            active_bg="#7dd3fc",
            active_fg="#07111f",
            font=font,
            bold=bold,
            size=size,
            padx=padx,
            pady=pady,
            **kwargs,
        )

    def make_card(
        self, parent, bg=None, highlightbackground=None, highlightthickness=1, **kwargs
    ):
        """Standardized container card with consistent border and dark background."""
        return tk.Frame(
            parent,
            bg=bg or self.CARD_COLOR,
            highlightbackground=highlightbackground or self.BORDER_COLOR,
            highlightthickness=highlightthickness,
            **kwargs,
        )

    def make_entry(self, parent, textvariable=None, bg=None, fg=None, font=None, **kwargs):
        """Standardized styled text entry."""
        opts = {
            "bg": bg or self.INPUT_COLOR,
            "fg": fg or self.TEXT_COLOR,
            "insertbackground": fg or self.TEXT_COLOR,
            "relief": "flat",
            "font": font or ("Segoe UI", 10),
        }
        if textvariable is not None:
            opts["textvariable"] = textvariable
        opts.update(kwargs)
        return tk.Entry(parent, **opts)

    def make_dropdown(
        self,
        parent,
        values=None,
        textvariable=None,
        default=None,
        command=None,
        width=None,
        font=None,
        style="Chrono.TCombobox",
        **kwargs,
    ):
        """High-reliability dark-themed dropdown selector."""
        values = values or []
        if textvariable is None:
            textvariable = tk.StringVar(value=default or (values[0] if values else ""))
        elif default and not textvariable.get():
            textvariable.set(default)

        combo_opts = {
            "values": values,
            "textvariable": textvariable,
            "state": "readonly",
            "style": style,
            "font": font or ("Segoe UI", 9),
        }
        if width is not None:
            combo_opts["width"] = width
        combo_opts.update(kwargs)

        combo = ttk.Combobox(parent, **combo_opts)

        # Open popdown on entry click
        combo.bind("<Button-1>", lambda e: combo.event_generate("<Down>"))

        if command:
            combo.bind(
                "<<ComboboxSelected>>",
                lambda e: self.root.after_idle(lambda: command(textvariable.get())),
            )

        return combo

    # =========================================================
    # STYLES & THEMING
    # =========================================================

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Global listbox palette for Combobox popdowns
        for pat in ("*TCombobox*Listbox.", "*ComboboxPopdown*Listbox.", "*Listbox."):
            self.root.option_add(f"{pat}background", self.INPUT_COLOR)
            self.root.option_add(f"{pat}foreground", self.TEXT_COLOR)
            self.root.option_add(f"{pat}selectBackground", self.BUTTON_ACTIVE)
            self.root.option_add(f"{pat}selectForeground", self.ACCENT_COLOR)

        # Button styles
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
            background=[("active", self.BUTTON_ACTIVE), ("pressed", self.CARD_COLOR)],
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
            background=[("active", "#7dd3fc"), ("pressed", "#0284c7")],
            foreground=[("active", "#07111f")],
        )

        # Combobox dark style
        style.configure(
            "Chrono.TCombobox",
            fieldbackground=self.INPUT_COLOR,
            background=self.BUTTON_COLOR,
            foreground=self.TEXT_COLOR,
            darkcolor=self.BORDER_COLOR,
            lightcolor=self.BORDER_COLOR,
            arrowcolor=self.ACCENT_COLOR,
            bordercolor=self.BORDER_COLOR,
            borderwidth=1,
            padding=(8, 6),
            font=("Segoe UI", 9),
        )
        style.map(
            "Chrono.TCombobox",
            fieldbackground=[("readonly", self.INPUT_COLOR), ("active", self.INPUT_COLOR)],
            background=[("active", self.BUTTON_ACTIVE), ("readonly", self.BUTTON_COLOR)],
            foreground=[("readonly", self.TEXT_COLOR), ("disabled", self.MUTED_COLOR)],
            arrowcolor=[("active", "#7dd3fc"), ("disabled", self.MUTED_COLOR)],
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

        self.make_label(
            header, text="⏱  CHRONOREPLAY", bg=self.PANEL_COLOR, size=20, bold=True
        ).pack(side="left", padx=26)

        self.make_label(
            header,
            text="LOCAL EVENT-SOURCED DEBUGGING PLATFORM",
            bg=self.PANEL_COLOR,
            fg=self.MUTED_COLOR,
            size=9,
            bold=True,
        ).pack(side="left")

        status_frame = tk.Frame(header, bg=self.PANEL_COLOR)
        status_frame.pack(side="right", padx=26)

        self.make_label(
            status_frame, text="●", bg=self.PANEL_COLOR, fg=self.SUCCESS_COLOR, size=13
        ).pack(side="left", padx=(0, 6))

        self.make_label(
            status_frame, text="SYSTEM READY", bg=self.PANEL_COLOR, size=10, bold=True
        ).pack(side="left")

    def _build_navigation(self):
        navigation = tk.Frame(self.root, bg=self.BG_COLOR, height=60)
        navigation.pack(fill="x", padx=20, pady=(10, 0))
        navigation.pack_propagate(False)

        for text, cmd in [
            ("EVENT SIMULATOR", self.show_dashboard),
            ("EVENT HISTORY & TIME MACHINE", self.show_event_history),
            ("WORKSPACE & FILE RECOVERY", self.show_workspace),
        ]:
            ttk.Button(navigation, text=text, style="Chrono.TButton", command=cmd).pack(
                side="left", padx=4
            )

    # =========================================================
    # SCROLLABLE MAIN CONTAINER
    # =========================================================

    def _build_scrollable_main(self):
        outer = tk.Frame(self.root, bg=self.BG_COLOR)
        outer.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = tk.Canvas(outer, bg=self.BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            outer, orient="vertical", command=self.canvas.yview, style="Chrono.Vertical.TScrollbar"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.main_container = tk.Frame(self.canvas, bg=self.BG_COLOR)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.main_container, anchor="nw"
        )

        self.main_container.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind(
            "<Configure>", lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width)
        )

        def _scroll(delta):
            self.canvas.yview_scroll(int(delta), "units")

        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: not isinstance(e.widget, (tk.Text, tk.Listbox)) and _scroll(-1 * (e.delta / 120)),
        )
        self.canvas.bind_all(
            "<Button-4>",
            lambda e: not isinstance(e.widget, (tk.Text, tk.Listbox)) and _scroll(-3),
        )
        self.canvas.bind_all(
            "<Button-5>",
            lambda e: not isinstance(e.widget, (tk.Text, tk.Listbox)) and _scroll(3),
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

        self.make_label(self.main_container, text="EVENT SIMULATOR", size=22, bold=True).pack(
            anchor="w", pady=(10, 2)
        )
        self.make_label(
            self.main_container,
            text="Simulate business transactions with automatic internal ID generation. ChronoReplay assigns user IDs and order IDs automatically.",
            fg=self.MUTED_COLOR,
            size=11,
        ).pack(anchor="w", pady=(0, 18))

        self._build_active_user_banner()
        self._build_simulator_card()
        self._build_history_preview()

    def _build_active_user_banner(self):
        """Display current active user details, user switcher, and wallet balance."""
        current_user = self.simulator.get_current_user()
        active_users = self.simulator.get_active_users()

        banner_frame = self.make_card(self.main_container)
        banner_frame.pack(fill="x", pady=(0, 16))

        if current_user:
            engine = self.replay_engine.replay_with_engine()[1]
            state = engine.get_state()
            balance = state.get("users", {}).get(current_user["user_id"], {}).get("balance", 0.0)

            left_box = tk.Frame(banner_frame, bg=self.CARD_COLOR)
            left_box.pack(side="left", padx=20, pady=14)

            self.make_label(
                left_box, text="👤 CURRENT ACTIVE USER", fg=self.ACCENT_COLOR, size=9, bold=True
            ).pack(anchor="w")

            user_label = f"{current_user['user_id']}  ─  {current_user['name']} ({current_user['email']})"
            self.make_label(left_box, text=user_label, size=13, bold=True).pack(
                anchor="w", pady=(2, 4)
            )

            if len(active_users) > 1:
                switcher_box = tk.Frame(left_box, bg=self.CARD_COLOR)
                switcher_box.pack(anchor="w", pady=(2, 0))

                self.make_label(
                    switcher_box, text="Switch User Context:", fg=self.MUTED_COLOR, size=8, bold=True
                ).pack(side="left", padx=(0, 6))

                user_options = [f"{u['user_id']} : {u['name']}" for u in active_users]
                self.user_switch_var = tk.StringVar(
                    value=f"{current_user['user_id']} : {current_user['name']}"
                )

                self.make_dropdown(
                    switcher_box,
                    values=user_options,
                    textvariable=self.user_switch_var,
                    command=lambda val: self._on_user_switched(),
                    font=("Segoe UI", 8),
                    width=28,
                ).pack(side="left")

            right_box = tk.Frame(banner_frame, bg=self.CARD_COLOR)
            right_box.pack(side="right", padx=20, pady=14)

            self.make_label(
                right_box, text="WALLET BALANCE", fg=self.MUTED_COLOR, size=9, bold=True
            ).pack(anchor="e")

            bal_color = self.SUCCESS_COLOR if balance >= 0 else self.ERROR_COLOR
            self.make_label(
                right_box, text=f"₹{balance:.2f}", fg=bal_color, size=14, bold=True
            ).pack(anchor="e")

        else:
            no_user_box = tk.Frame(banner_frame, bg=self.CARD_COLOR)
            no_user_box.pack(fill="x", padx=20, pady=14)

            self.make_label(
                no_user_box, text="⚠  NO USER EXISTS", fg=self.WARNING_COLOR, size=11, bold=True
            ).pack(side="left")
            self.make_label(
                no_user_box,
                text="— Create a user first before recording orders or payment events.",
                fg=self.MUTED_COLOR,
                size=10,
            ).pack(side="left", padx=8)

            self.make_accent_button(
                no_user_box,
                text="CREATE USER",
                command=self._switch_to_create_user,
                padx=12,
                pady=4,
            ).pack(side="right")

    def _on_user_switched(self, event=None):
        val = getattr(self, "user_switch_var", None)
        if val:
            user_id = val.get().split(":")[0].strip()
            self.simulator.switch_user(user_id)
            self._show_status(f"Switched active user context to {user_id}", success=True)
            self.show_dashboard()

    def _switch_to_create_user(self):
        self.selected_event_label_var.set("User Created")
        self._render_current_event_form()

    def _build_simulator_card(self):
        card = self.make_card(self.main_container)
        card.pack(fill="x", pady=(0, 20))

        self.make_label(card, text="SIMULATE EVENT", fg=self.ACCENT_COLOR, size=15, bold=True).pack(
            anchor="w", padx=24, pady=(20, 4)
        )
        self.make_label(
            card,
            text="Select an event to dispatch. IDs are assigned automatically by ChronoReplay.",
            fg=self.MUTED_COLOR,
            size=10,
        ).pack(anchor="w", padx=24, pady=(0, 16))

        self.make_label(card, text="SELECT EVENT", fg=self.MUTED_COLOR, size=9, bold=True).pack(
            anchor="w", padx=24, pady=(0, 6)
        )

        options = [label for label, _ in self.EVENT_OPTIONS]
        self.event_dropdown = self.make_dropdown(
            card,
            values=options,
            textvariable=self.selected_event_label_var,
            command=lambda val: self._render_current_event_form(),
            font=("Segoe UI", 10),
        )
        self.event_dropdown.pack(fill="x", padx=24, pady=(0, 16))

        self.form_container = tk.Frame(card, bg=self.CARD_COLOR)
        self.form_container.pack(fill="x", padx=24, pady=(0, 16))

        bottom_bar = tk.Frame(card, bg=self.CARD_COLOR)
        bottom_bar.pack(fill="x", padx=24, pady=(0, 20))

        self.status_banner = self.make_card(bottom_bar, bg=self.INPUT_COLOR)
        self.status_banner.pack(fill="x", expand=True)

        self.status_icon_label = self.make_label(
            self.status_banner, text="●", bg=self.INPUT_COLOR, fg=self.MUTED_COLOR, size=11, bold=True
        )
        self.status_icon_label.pack(side="left", padx=(10, 6), pady=8)

        self.status_label = self.make_label(
            self.status_banner,
            textvariable=self.status_var,
            bg=self.INPUT_COLOR,
            fg=self.MUTED_COLOR,
            anchor="w",
            size=9,
            bold=True,
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=8)

        self._render_current_event_form()

    def _render_current_event_form(self):
        """Render dynamic fields for selected event type."""
        for widget in self.form_container.winfo_children():
            widget.destroy()

        self.field_vars = {}
        selected_label = self.selected_event_label_var.get()
        event_type = self.LABEL_TO_TYPE.get(selected_label, "user.created")
        current_user = self.simulator.get_current_user()

        if event_type == "user.created":
            self._render_create_user_form()
        elif not current_user:
            self._render_no_user_warning()
        else:
            self._render_user_bound_event_form(event_type, current_user)

    def _render_create_user_form(self):
        """Form for creating new user."""
        form_frame = tk.Frame(self.form_container, bg=self.CARD_COLOR)
        form_frame.pack(fill="x")

        self._create_form_row(form_frame, 0, "Name", "name", default="Rahul")
        self._create_form_row(form_frame, 1, "Email", "email", default="rahul@gmail.com")
        self._create_form_row(form_frame, 2, "Age", "age", default="25", is_number=True)

        btn_row = tk.Frame(form_frame, bg=self.CARD_COLOR)
        btn_row.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))

        ttk.Button(
            btn_row,
            text="CREATE USER",
            style="Accent.TButton",
            command=self._handle_create_user_submit,
        ).pack()

    def _render_no_user_warning(self):
        """Warning when no user exists."""
        warn_card = self.make_card(
            self.form_container, bg=self.INPUT_COLOR, highlightbackground=self.WARNING_COLOR
        )
        warn_card.pack(fill="x", pady=10)

        inner = tk.Frame(warn_card, bg=self.INPUT_COLOR)
        inner.pack(fill="x", padx=16, pady=14)

        self.make_label(
            inner, text="⚠  No user exists.", bg=self.INPUT_COLOR, fg=self.WARNING_COLOR, size=12, bold=True
        ).pack(anchor="w")
        self.make_label(
            inner,
            text="Create a user first before recording this event.",
            bg=self.INPUT_COLOR,
            size=10,
        ).pack(anchor="w", pady=(2, 10))

        self.make_accent_button(
            inner, text="Create User", command=self._switch_to_create_user, padx=16, pady=6
        ).pack(anchor="w")

    def _render_user_bound_event_form(self, event_type, current_user):
        """Render event form dynamically with active user context."""
        form_frame = tk.Frame(self.form_container, bg=self.CARD_COLOR)
        form_frame.pack(fill="x")

        user_info_frame = self.make_card(form_frame, bg=self.INPUT_COLOR)
        user_info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self.make_label(
            user_info_frame,
            text=f"Active User Context: {current_user['user_id']} ─ {current_user['name']}",
            bg=self.INPUT_COLOR,
            fg=self.ACCENT_COLOR,
            size=10,
            bold=True,
        ).pack(side="left", padx=12, pady=8)

        # Form configuration map: event_type -> (fields, btn_text, submit_cmd)
        form_configs = {
            "balance.added": (
                [("row", "Amount (₹)", "amount", "500.0", True)],
                "ADD BALANCE",
                self._handle_add_balance_submit,
            ),
            "order.created": (
                [("row", "Order Amount (₹)", "amount", "200.0", True)],
                "CREATE ORDER",
                self._handle_create_order_submit,
            ),
            "payment.completed": (
                [
                    ("row", "Amount (₹)", "amount", "200.0", True),
                    ("dropdown", "Payment Method", "method", ["UPI", "CARD", "NETBANKING", "CASH"], "UPI"),
                ],
                "RECORD PAYMENT",
                self._handle_complete_payment_submit,
            ),
            "profile.updated": (
                [
                    ("row", "Name", "name", current_user["name"], False),
                    ("row", "City", "city", "Mumbai", False),
                ],
                "UPDATE PROFILE",
                self._handle_update_profile_submit,
            ),
            "status.changed": (
                [("dropdown", "Status", "status", ["active", "suspended", "verified", "inactive"], "active")],
                "CHANGE STATUS",
                self._handle_change_status_submit,
            ),
            "order.updated": (
                [
                    (
                        "dropdown",
                        "Order Status",
                        "status",
                        ["pending", "paid", "shipped", "completed", "cancelled"],
                        "paid",
                    )
                ],
                "UPDATE ORDER",
                self._handle_update_order_submit,
            ),
            "user.deleted": (
                [
                    (
                        "dropdown",
                        "Select User to Delete",
                        "user_id",
                        [
                            f"{u['user_id']} : {u['name']} (Balance: ₹{u.get('balance', 0.0):.2f})"
                            for u in self.simulator.get_active_users()
                        ] or [f"{current_user['user_id']} : {current_user['name']}"],
                        f"{current_user['user_id']} : {current_user['name']} (Balance: ₹{current_user.get('balance', 0.0):.2f})",
                    )
                ],
                "DELETE SELECTED USER",
                self._handle_delete_user_submit,
            ),
        }

        if event_type == "payment.completed":
            user_orders = self.simulator.get_user_orders(current_user["user_id"])
            user_balance = self.simulator.get_user_balance(current_user["user_id"])
            if not user_orders:
                no_order_card = self.make_card(
                    form_frame, bg=self.INPUT_COLOR, highlightbackground=self.WARNING_COLOR
                )
                no_order_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))

                inner = tk.Frame(no_order_card, bg=self.INPUT_COLOR)
                inner.pack(fill="x", padx=16, pady=12)

                self.make_label(
                    inner,
                    text="⚠  NO ORDER FOUND FOR USER",
                    bg=self.INPUT_COLOR,
                    fg=self.WARNING_COLOR,
                    size=10,
                    bold=True,
                ).pack(anchor="w")
                self.make_label(
                    inner,
                    text="Payments cannot be completed without an order. Please create an order first.",
                    bg=self.INPUT_COLOR,
                    size=9,
                ).pack(anchor="w", pady=(2, 8))

                self.make_accent_button(
                    inner,
                    text="CREATE ORDER",
                    command=lambda: (
                        self.selected_event_label_var.set("Order Created"),
                        self._render_current_event_form(),
                    ),
                    padx=14,
                    pady=4,
                ).pack(anchor="w")
                return

            if user_balance <= 0:
                no_bal_card = self.make_card(
                    form_frame, bg=self.INPUT_COLOR, highlightbackground=self.WARNING_COLOR
                )
                no_bal_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))

                inner = tk.Frame(no_bal_card, bg=self.INPUT_COLOR)
                inner.pack(fill="x", padx=16, pady=12)

                self.make_label(
                    inner,
                    text=f"⚠  NO BALANCE AVAILABLE (Current: ₹{user_balance:.2f})",
                    bg=self.INPUT_COLOR,
                    fg=self.WARNING_COLOR,
                    size=10,
                    bold=True,
                ).pack(anchor="w")
                self.make_label(
                    inner,
                    text="Payments cannot be completed without available balance. Please add balance first.",
                    bg=self.INPUT_COLOR,
                    size=9,
                ).pack(anchor="w", pady=(2, 8))

                self.make_accent_button(
                    inner,
                    text="ADD BALANCE (₹500)",
                    command=lambda: (
                        self.selected_event_label_var.set("Balance Added"),
                        self._render_current_event_form(),
                    ),
                    padx=14,
                    pady=4,
                ).pack(anchor="w")
                return

            pending_orders = [o for o in user_orders if o.get("status") in ("pending", "created")]
            order_opts = []
            for o in user_orders:
                remaining = max(0.0, o["amount"] - o.get("paid_amount", 0.0))
                order_opts.append(f"{o['order_id']} : ₹{o['amount']:.2f} (Status: {o['status'].upper()}, Due: ₹{remaining:.2f})")

            default_order = order_opts[0]
            default_amount = "200.0"
            if pending_orders:
                p_ord = pending_orders[0]
                p_rem = max(0.0, p_ord["amount"] - p_ord.get("paid_amount", 0.0))
                default_order = next((opt for opt in order_opts if opt.startswith(p_ord["order_id"])), order_opts[0])
                default_amount = f"{p_rem:.2f}" if p_rem > 0 else f"{p_ord['amount']:.2f}"

            form_configs["payment.completed"] = (
                [
                    ("dropdown", "Select Order to Pay", "order_id", order_opts, default_order),
                    ("row", "Amount (₹)", "amount", default_amount, True),
                    ("dropdown", "Payment Method", "method", ["UPI", "CARD", "NETBANKING", "CASH"], "UPI"),
                ],
                "RECORD PAYMENT",
                self._handle_complete_payment_submit,
            )

        fields, btn_text, btn_cmd = form_configs.get(event_type, ([], "DISPATCH EVENT", lambda: None))

        row_idx = 1
        for field in fields:
            if field[0] == "row":
                _, label_text, var_key, default_val, is_num = field
                self._create_form_row(form_frame, row_idx, label_text, var_key, default_val, is_num)
            elif field[0] == "dropdown":
                _, label_text, var_key, opts, default_val = field
                self._create_form_dropdown(form_frame, row_idx, label_text, var_key, opts, default_val)
            row_idx += 1

        if event_type == "user.deleted":
            self.make_label(
                form_frame,
                text="This will mark the current user as deleted in the event stream.",
                fg=self.MUTED_COLOR,
                size=9,
            ).grid(row=row_idx, column=0, columnspan=2, sticky="w", pady=(0, 10))
            row_idx += 1

        btn_row = tk.Frame(form_frame, bg=self.CARD_COLOR)
        btn_row.grid(row=row_idx, column=0, columnspan=2, sticky="e", pady=(12, 0))

        ttk.Button(btn_row, text=btn_text, style="Accent.TButton", command=btn_cmd).pack()

    def _create_form_row(self, parent, row, label_text, var_key, default="", is_number=False):
        self.make_label(parent, text=label_text, size=9, bold=True).grid(
            row=row, column=0, sticky="w", padx=(0, 14), pady=6
        )
        var = tk.StringVar(value=str(default))
        self.field_vars[var_key] = (var, "number" if is_number else "text")

        border = tk.Frame(parent, bg=self.BORDER_COLOR)
        border.grid(row=row, column=1, sticky="ew", pady=6)
        parent.columnconfigure(1, weight=1)

        self.make_entry(border, textvariable=var, font=("Segoe UI", 9)).pack(
            fill="both", expand=True, padx=1, pady=1, ipady=5
        )

    def _create_form_dropdown(self, parent, row, label_text, var_key, options, default=""):
        self.make_label(parent, text=label_text, size=9, bold=True).grid(
            row=row, column=0, sticky="w", padx=(0, 14), pady=6
        )
        var = tk.StringVar(value=default or (options[0] if options else ""))
        self.field_vars[var_key] = (var, "dropdown")

        combo = self.make_dropdown(parent, values=options, textvariable=var, font=("Segoe UI", 9))
        combo.grid(row=row, column=1, sticky="ew", pady=6)
        parent.columnconfigure(1, weight=1)

    # ---------------------------------------------------------
    # Form submission handlers
    # ---------------------------------------------------------

    def _get_event_local_date(self, event):
        """Extract standardized YYYY-MM-DD local date string from event timestamp."""
        ts = getattr(event, "timestamp", "")
        if not ts:
            return ""
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is not None:
                return dt.astimezone().strftime("%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ts.split("T")[0].split(" ")[0]

    def _get_event_local_time(self, event):
        """Extract standardized HH:MM:SS local time string from event timestamp."""
        ts = getattr(event, "timestamp", "")
        if not ts:
            return ""
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is not None:
                return dt.astimezone().strftime("%H:%M:%S")
            return dt.strftime("%H:%M:%S")
        except Exception:
            if "T" in ts:
                return ts.split("T")[1].split(".")[0].split("+")[0]
            return ts

    def _handle_create_user_submit(self):
        try:
            name = self.field_vars["name"][0].get().strip()
            email = self.field_vars["email"][0].get().strip()
            age_str = self.field_vars["age"][0].get().strip()
            if not name or not email or not age_str:
                raise ValueError("Name, email, and age are required.")
            event = self.simulator.create_user(name, email, int(age_str))
            self.history_user_filter_var.set("ALL")
            self.history_date_filter_var.set("ALL")
            self._show_status(f"User created successfully — User ID: {event.data['user_id']}", success=True)
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_add_balance_submit(self):
        try:
            amount = float(self.field_vars["amount"][0].get().strip())
            event = self.simulator.add_balance(amount)
            self.history_date_filter_var.set("ALL")
            self._show_status(
                f"Balance added: ₹{amount:.2f} for user {event.data['user_id']}", success=True
            )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_create_order_submit(self):
        try:
            amount = float(self.field_vars["amount"][0].get().strip())
            event = self.simulator.create_order(amount)
            self.history_date_filter_var.set("ALL")
            self._show_status(
                f"Order created successfully — Order ID: {event.data['order_id']} (₹{amount:.2f})",
                success=True,
            )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_complete_payment_submit(self):
        try:
            amount = float(self.field_vars["amount"][0].get().strip())
            method = self.field_vars["method"][0].get().strip()
            order_id = None
            if "order_id" in self.field_vars:
                raw_order = self.field_vars["order_id"][0].get().strip()
                if ":" in raw_order:
                    order_id = raw_order.split(":")[0].strip()
                elif raw_order:
                    order_id = raw_order

            self.simulator.complete_payment(amount, method, order_id=order_id)
            self.history_date_filter_var.set("ALL")

            diag = self.replay_engine.get_diagnostics_for_event(len(self.store.get_all()))
            if not diag.get("is_valid", True):
                self._show_status(
                    f"PAYMENT RECORDED WITH INVALID STATE WARNING: {diag.get('reason')}", success=False
                )
            else:
                self._show_status(
                    f"Payment completed: ₹{amount:.2f} for {order_id or 'Order'} via {method}", success=True
                )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_update_profile_submit(self):
        try:
            name = self.field_vars["name"][0].get().strip()
            city = self.field_vars["city"][0].get().strip()
            self.simulator.update_profile(name, city)
            self._show_status(f"Profile updated: {name}, {city}", success=True)
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_change_status_submit(self):
        try:
            status = self.field_vars["status"][0].get().strip()
            self.simulator.change_status(status)
            self._show_status(f"Status changed to: {status}", success=True)
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_update_order_submit(self):
        try:
            status = self.field_vars["status"][0].get().strip()
            self.simulator.update_order(status)
            self._show_status(f"Order updated to: {status}", success=True)
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_delete_user_submit(self):
        try:
            target_uid = None
            if "user_id" in self.field_vars:
                raw_user = self.field_vars["user_id"][0].get().strip()
                if ":" in raw_user:
                    target_uid = raw_user.split(":")[0].strip()
                elif raw_user:
                    target_uid = raw_user

            event = self.simulator.delete_user(user_id=target_uid)
            self.show_dashboard()
            self._show_status(f"Selected user '{event.data['user_id']}' marked as deleted. Other users remain unaffected.", success=True)
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _show_status(self, message, success=True):
        if hasattr(self, "status_var"):
            try:
                self.status_var.set(message)
            except Exception:
                pass
        if hasattr(self, "status_label"):
            try:
                color = self.SUCCESS_COLOR if success else self.ERROR_COLOR
                self.status_label.configure(fg=color)
                if hasattr(self, "status_icon_label"):
                    self.status_icon_label.configure(text="✓" if success else "⚠", fg=color)
                if hasattr(self, "status_banner"):
                    self.status_banner.configure(highlightbackground=color)
            except Exception:
                pass

    def _build_history_preview(self):
        """Preview recent business events at the bottom of the simulator."""
        card = self.make_card(self.main_container)
        card.pack(fill="both", expand=True, pady=(0, 24))

        self.make_label(card, text="RECENT EVENT STREAM", fg=self.ACCENT_COLOR, size=15, bold=True).pack(
            anchor="w", padx=24, pady=(20, 6)
        )

        business_events = self._get_business_events()
        if not business_events:
            self.make_label(
                card,
                text="No business events recorded in store. Dispatch an event to begin.",
                fg=self.MUTED_COLOR,
                size=10,
            ).pack(anchor="w", padx=24, pady=(0, 20))
            return

        preview_table = tk.Frame(card, bg=self.CARD_COLOR)
        preview_table.pack(fill="x", padx=24, pady=(0, 20))

        hdr = tk.Frame(preview_table, bg=self.CARD_COLOR)
        hdr.pack(fill="x", pady=(0, 6))
        for col, (title, width) in enumerate(
            [("#", 6), ("USER", 18), ("EVENT", 20), ("DETAILS", 36), ("TIME", 16)]
        ):
            self.make_label(
                hdr, text=title, width=width, anchor="w", fg=self.MUTED_COLOR, size=9, bold=True
            ).grid(row=0, column=col, padx=4)

        recent = business_events[-6:]
        start_idx = len(business_events) - len(recent) + 1

        for i, event in enumerate(recent, start=start_idx):
            row = self.make_card(preview_table, bg=self.INPUT_COLOR)
            row.pack(fill="x", pady=2)

            ts = self._get_event_local_time(event)
            user_badge = event.data.get("user_id", "System")
            if "name" in event.data and event.type == "user.created":
                user_badge = f"{user_badge} ({event.data['name']})"

            details = [
                f"{k}: ₹{event.data[k]}" if k == "amount" else f"{k}: {event.data[k]}"
                for k in ["amount", "order_id", "status", "name"]
                if k in event.data
            ]
            detail_str = " | ".join(details) or str(event.data)

            for text, width, fg, bold in [
                (f"#{i}", 6, self.MUTED_COLOR, True),
                (user_badge, 18, self.ACCENT_COLOR, True),
                (event.type, 20, self.TEXT_COLOR, True),
                (detail_str, 36, self.MUTED_COLOR, False),
                (ts, 16, self.MUTED_COLOR, False),
            ]:
                self.make_label(
                    row,
                    text=text,
                    width=width,
                    anchor="w",
                    bg=self.INPUT_COLOR,
                    fg=fg,
                    size=8 if width == 16 else 9,
                    bold=bold,
                ).pack(side="left", padx=(8 if width == 6 else 4), pady=6)

    # =========================================================
    # 2. EVENT HISTORY & TIME MACHINE VIEW
    # =========================================================

    def _get_business_events(self):
        """Return all business events (excluding workspace file.* events)."""
        return [e for e in self.store.get_all() if not e.type.startswith("file.")]

    def _get_event_friendly_impact(self, event, state_before=None, state_after=None):
        """Generate human-readable impact explanation for an event."""
        etype = event.type
        data = event.data
        uid = data.get("user_id", "System")

        if etype == "user.created":
            return f"Registered user '{data.get('name', 'User')}' ({data.get('email', '')}, age {data.get('age', '')}). Initial wallet: ₹0.00."

        if etype == "balance.added":
            amt = data.get("amount", 0.0)
            bal_before = state_before.get("users", {}).get(uid, {}).get("balance") if state_before else None
            bal_after = state_after.get("users", {}).get(uid, {}).get("balance") if state_after else None

            if bal_before is not None and bal_after is not None:
                if bal_before < 0:
                    return f"Topped up ₹{amt:.2f} for {uid}. Balance changed from -₹{abs(bal_before):.2f} ➔ ₹{bal_after:.2f} (cleared ₹{abs(bal_before):.2f} overdraft deficit)."
                return f"Topped up ₹{amt:.2f} for {uid}. Balance changed from ₹{bal_before:.2f} ➔ ₹{bal_after:.2f}."
            elif bal_after is not None:
                return f"Topped up ₹{amt:.2f} into wallet for {uid}. Resulting balance: ₹{bal_after:.2f}."
            return f"Topped up ₹{amt:.2f} into wallet for {uid}."

        if etype == "order.created":
            return f"Created order {data.get('order_id', 'Order')} for ₹{data.get('amount', 0.0):.2f} (pending) for {uid}."

        if etype == "payment.completed":
            amt = data.get("amount", 0.0)
            method = data.get("method", "UPI")
            bal_before = state_before.get("users", {}).get(uid, {}).get("balance") if state_before else None
            bal_after = state_after.get("users", {}).get(uid, {}).get("balance") if state_after else None

            if bal_before is not None and bal_after is not None:
                if bal_after < 0:
                    return f"Paid ₹{amt:.2f} via {method} for {uid}. Balance changed from ₹{bal_before:.2f} ➔ -₹{abs(bal_after):.2f} (overdrawn by ₹{abs(bal_after):.2f})."
                return f"Paid ₹{amt:.2f} via {method} for {uid}. Balance changed from ₹{bal_before:.2f} ➔ ₹{bal_after:.2f}."
            return f"Processed payment of ₹{amt:.2f} via {method} for {uid}."

        if etype == "profile.updated":
            return f"Updated profile for {uid}: Name='{data.get('name', '')}', City='{data.get('city', '')}'."
        if etype == "status.changed":
            return f"Changed account status for {uid} to '{data.get('status', 'active')}'."
        if etype == "order.updated":
            return f"Updated order {data.get('order_id', 'active order')} status to '{data.get('status', 'paid')}'."
        if etype == "state.restored":
            return f"Restored historical application state from Step #{data.get('source_event_number', '?')}."
        if etype == "user.deleted":
            return f"Marked user {uid} as deleted in the immutable ledger."

        return f"Dispatched {etype} with data: {data}"

    def show_event_history(self):
        self._clear_main_area()

        self.make_label(
            self.main_container, text="EVENT HISTORY & TIME MACHINE", size=22, bold=True
        ).pack(anchor="w", pady=(10, 2))
        self.make_label(
            self.main_container,
            text="Immutable chronological transaction ledger. Filter by user or launch Time Machine above to step through historical state.",
            fg=self.MUTED_COLOR,
            size=11,
        ).pack(anchor="w", pady=(0, 14))

        # How it works card
        explainer_card = self.make_card(self.main_container, highlightbackground=self.ACCENT_COLOR)
        explainer_card.pack(fill="x", pady=(0, 16))

        ex_inner = tk.Frame(explainer_card, bg=self.CARD_COLOR)
        ex_inner.pack(fill="x", padx=20, pady=12)

        self.make_label(
            ex_inner,
            text="💡  HOW EVENT HISTORY & TIME MACHINE WORK",
            fg=self.ACCENT_COLOR,
            size=11,
            bold=True,
        ).pack(anchor="w", pady=(0, 4))
        self.make_label(
            ex_inner,
            text="• Ledger: Every action (user creation, wallet top-up, order, payment) is recorded as a permanent event step.\n"
            "• Time Travel: Click 'LAUNCH TIME MACHINE (STEP-BY-STEP REPLAY)' above to step back in time and inspect live balances & orders.\n"
            "• Invariant Diagnostics: Automatically checks if any action broke business rules (e.g. negative balances or overspending).",
            size=9,
            justify="left",
        ).pack(anchor="w")

        business_events = self._get_business_events()
        if not business_events:
            card = self.make_card(self.main_container)
            card.pack(fill="both", expand=True, pady=(0, 24))
            self.make_label(
                card,
                text="No business events recorded yet. Go to 'EVENT SIMULATOR' to create users, top-up wallets, or place orders.",
                fg=self.MUTED_COLOR,
                size=11,
            ).pack(pady=40)
            return

        all_users = self.simulator.get_all_users()
        active_users = self.simulator.get_active_users()
        ex_users = self.simulator.get_ex_users()
        ex_uids = {u["user_id"] for u in ex_users}
        active_user = self.history_user_filter_var.get()
        active_date = self.history_date_filter_var.get()

        # Filter card
        filter_card = self.make_card(self.main_container)
        filter_card.pack(fill="x", pady=(0, 14))

        filter_panel = tk.Frame(filter_card, bg=self.CARD_COLOR)
        filter_panel.pack(fill="x", padx=20, pady=12)

        # Row 1: Select user filter
        user_row = tk.Frame(filter_panel, bg=self.CARD_COLOR)
        user_row.pack(fill="x", pady=(0, 8))

        self.make_label(
            user_row, text="👤 1. SELECT USER:", fg=self.ACCENT_COLOR, size=10, bold=True, width=18, anchor="w"
        ).pack(side="left", padx=(0, 8))

        user_btn_specs = [("ALL USERS", "ALL")] + [(f"{u['user_id']} ({u['name']})", u["user_id"]) for u in active_users]
        if ex_users:
            ex_event_count = len([e for e in business_events if e.data.get("user_id") in ex_uids])
            user_btn_specs.append((f"📁 OTHER (Ex-Users: {len(ex_users)} | {ex_event_count} Evt)", "EX_USERS"))

        for label, val in user_btn_specs:
            is_act = active_user == val
            self.make_button(
                user_row,
                text=label,
                bg=self.ACCENT_COLOR if is_act else self.BUTTON_COLOR,
                fg="#07111f" if is_act else self.TEXT_COLOR,
                padx=10,
                pady=4,
                command=lambda t=val: self._set_user_filter(t),
            ).pack(side="left", padx=3)

        # Row 2: Select date filter
        date_row = tk.Frame(filter_panel, bg=self.CARD_COLOR)
        date_row.pack(fill="x", pady=(4, 6))

        self.make_label(
            date_row, text="📅 2. SELECT DATE:", fg=self.ACCENT_COLOR, size=10, bold=True, width=18, anchor="w"
        ).pack(side="left", padx=(0, 8))

        events_for_user = [
            e for e in business_events
            if active_user == "ALL"
            or (active_user == "EX_USERS" and e.data.get("user_id") in ex_uids)
            or e.data.get("user_id") == active_user
        ]
        date_counts = {}
        for e in events_for_user:
            d_str = self._get_event_local_date(e)
            date_counts[d_str] = date_counts.get(d_str, 0) + 1

        if active_date != "ALL" and active_date not in date_counts:
            active_date = "ALL"
            self.history_date_filter_var.set("ALL")

        date_btn_specs = [(f"ALL DATES ({len(events_for_user)})", "ALL")] + [
            (f"📅 {d} ({date_counts[d]})", d) for d in sorted(date_counts.keys(), reverse=True)
        ]
        for label, val in date_btn_specs:
            is_act = active_date == val
            self.make_button(
                date_row,
                text=label,
                bg=self.ACCENT_COLOR if is_act else self.BUTTON_COLOR,
                fg="#07111f" if is_act else self.TEXT_COLOR,
                padx=10,
                pady=4,
                command=lambda t=val: self._set_date_filter(t),
            ).pack(side="left", padx=3)

        # Row 3: Active Filters & Reset Button
        if active_user != "ALL" or active_date != "ALL":
            summary_row = tk.Frame(filter_panel, bg=self.CARD_COLOR)
            summary_row.pack(fill="x", pady=(8, 0))

            f_texts = []
            if active_user != "ALL":
                u_obj = next((u for u in all_users if u["user_id"] == active_user), None)
                f_texts.append(f"User: {active_user} ({u_obj['name']})" if u_obj else f"User: {active_user}")
            if active_date != "ALL":
                f_texts.append(f"Date: {active_date}")

            self.make_label(
                summary_row,
                text="🔎 Active Filters: " + "  |  ".join(f_texts),
                fg=self.SUCCESS_COLOR,
                size=9,
                bold=True,
            ).pack(side="left", padx=(4, 12))

            self.make_button(
                summary_row,
                text="🔄 RESET ALL FILTERS",
                bg="#334155",
                active_bg="#475569",
                padx=10,
                pady=3,
                size=8,
                command=self._reset_history_filters,
            ).pack(side="left")

        # User Storage Summary Box
        if active_user != "ALL":
            user_info = next((u for u in all_users if u["user_id"] == active_user), None)
            if user_info:
                state = self.replay_engine.replay_with_engine()[1].get_state()
                bal = state.get("users", {}).get(active_user, {}).get("balance", 0.0)
                u_events = [e for e in business_events if e.data.get("user_id") == active_user]
                u_orders = [o for o in state.get("orders", {}).values() if o.get("user_id") == active_user]

                user_summary_box = self.make_card(self.main_container, bg=self.INPUT_COLOR)
                user_summary_box.pack(fill="x", pady=(0, 14))

                sum_inner = tk.Frame(user_summary_box, bg=self.INPUT_COLOR)
                sum_inner.pack(fill="x", padx=18, pady=10)

                self.make_label(
                    sum_inner,
                    text=f"📂 USER CONTEXT: {user_info['user_id']} ({user_info['name']})",
                    bg=self.INPUT_COLOR,
                    fg=self.ACCENT_COLOR,
                    size=11,
                    bold=True,
                ).pack(side="left")

                bal_color = self.SUCCESS_COLOR if bal >= 0 else self.ERROR_COLOR
                self.make_label(
                    sum_inner,
                    text=f"Email: {user_info['email']}  |  Total User Events: {len(u_events)}  |  Orders: {len(u_orders)}  |  Wallet Balance: ₹{bal:.2f}",
                    bg=self.INPUT_COLOR,
                    fg=bal_color if bal < 0 else self.TEXT_COLOR,
                    size=10,
                    bold=True,
                ).pack(side="right")

        # Main Timeline Card
        card = self.make_card(self.main_container)
        card.pack(fill="both", expand=True, pady=(0, 24))

        top_timeline_bar = tk.Frame(card, bg=self.CARD_COLOR)
        top_timeline_bar.pack(fill="x", padx=20, pady=(18, 10))

        self.make_label(
            top_timeline_bar, text="CHRONOLOGICAL EVENT STREAM", fg=self.ACCENT_COLOR, size=14, bold=True
        ).pack(side="left")

        user_tm_label = f"FOR {active_user}" if active_user != "ALL" else "ALL USERS"
        self.make_accent_button(
            top_timeline_bar,
            text=f"⏱  LAUNCH TIME MACHINE ({user_tm_label})",
            padx=18,
            pady=8,
            size=10,
            command=lambda: self.show_time_machine(user_id=active_user),
        ).pack(side="right")

        # Header columns
        header = tk.Frame(card, bg=self.CARD_COLOR)
        header.pack(fill="x", padx=20, pady=(4, 6))

        for col, (text, width) in enumerate(
            [
                ("STEP", 6),
                ("USER", 16),
                ("EVENT TYPE", 18),
                ("ACTION & IMPACT", 34),
                ("TIME", 12),
                ("ACTIONS", 22),
            ]
        ):
            self.make_label(
                header, text=text, width=width, anchor="w", fg=self.MUTED_COLOR, size=9, bold=True
            ).grid(row=0, column=col, padx=4, pady=4)

        invalid_map = {d["event_index"]: d for d in self.replay_engine.get_all_diagnostics() if not d.get("is_valid")}

        state_engine = StateEngine()
        step_states = {}
        for idx, ev in enumerate(business_events, start=1):
            s_before = deepcopy(state_engine.get_state())
            state_engine.apply(ev)
            s_after = deepcopy(state_engine.get_state())
            step_states[idx] = (s_before, s_after)

        displayed_events = [
            (idx, e)
            for idx, e in enumerate(business_events, start=1)
            if (
                active_user == "ALL"
                or (active_user == "EX_USERS" and e.data.get("user_id") in ex_uids)
                or e.data.get("user_id") == active_user
            )
            and (active_date == "ALL" or self._get_event_local_date(e) == active_date)
        ]

        if not displayed_events:
            self.make_label(
                card, text="No events found for the selected filter.", fg=self.MUTED_COLOR, size=10
            ).pack(pady=20)
            return

        for index, event in displayed_events:
            is_invalid = index in invalid_map
            row_border = self.ERROR_COLOR if is_invalid else self.BORDER_COLOR
            row_bg = "#1f1422" if is_invalid else self.CARD_COLOR

            row = self.make_card(card, bg=row_bg, highlightbackground=row_border)
            row.pack(fill="x", padx=20, pady=3)

            ts = self._get_event_local_time(event)
            raw_uid = event.data.get("user_id", "System")
            is_ex = raw_uid in ex_uids
            ex_obj = next((u for u in ex_users if u["user_id"] == raw_uid), None)

            if is_ex:
                user_display = f"Ex-User: {ex_obj['name'] if ex_obj else raw_uid} ({raw_uid})"
            elif "name" in event.data and event.type == "user.created":
                user_display = f"{raw_uid} ({event.data['name']})"
            else:
                user_display = raw_uid

            s_before, s_after = step_states.get(index, (None, None))
            impact_text = self._get_event_friendly_impact(event, s_before, s_after)
            if is_invalid:
                impact_text = "❌ INVALID: " + impact_text

            for text, width, fg, bold in [
                (f"#{index}", 6, self.MUTED_COLOR, True),
                (user_display, 16, self.ACCENT_COLOR, True),
                (event.type, 18, self.ERROR_COLOR if is_invalid else self.TEXT_COLOR, True),
                (impact_text, 34, self.ERROR_COLOR if is_invalid else self.TEXT_COLOR, is_invalid),
                (ts, 12, self.MUTED_COLOR, False),
            ]:
                self.make_label(
                    row,
                    text=text,
                    width=width,
                    anchor="w",
                    bg=row_bg,
                    fg=fg,
                    size=10 if width == 18 else 9,
                    bold=bold,
                ).pack(side="left", padx=(8 if width == 6 else 4), pady=8)

            action_box = tk.Frame(row, bg=row_bg)
            action_box.pack(side="right", padx=10, pady=6)

            self.make_accent_button(
                action_box,
                text="⏱ REPLAY",
                padx=8,
                pady=4,
                size=8,
                command=lambda e=event: self.show_time_machine(target_event_id=e.id, user_id=active_user),
            ).pack(side="left", padx=(0, 6))

            self.make_button(
                action_box,
                text="🔍 PAYLOAD",
                padx=8,
                pady=4,
                size=8,
                command=lambda e=event, n=index: self.view_event(e, n),
            ).pack(side="left")

    def _set_user_filter(self, user_filter):
        self.history_user_filter_var.set(user_filter)
        self.history_date_filter_var.set("ALL")
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
    # TIME MACHINE VIEW (STEP-BY-STEP REPLAY)
    # =========================================================

    def show_time_machine(self, event_number=None, user_id=None, target_event_id=None):
        self._clear_main_area()
        all_business_events = self._get_business_events()
        if not all_business_events:
            self.show_event_history()
            return

        all_users = self.simulator.get_all_users()
        active_users = self.simulator.get_active_users()
        ex_users = self.simulator.get_ex_users()
        ex_uids = {u["user_id"] for u in ex_users}
        valid_uids = [u["user_id"] for u in all_users]

        user_id = user_id or self.history_user_filter_var.get()
        if user_id not in ["ALL", "EX_USERS"] + valid_uids:
            user_id = "ALL"

        if user_id == "EX_USERS":
            scoped_events = [e for e in all_business_events if e.data.get("user_id") in ex_uids] or all_business_events
        elif user_id != "ALL":
            scoped_events = [e for e in all_business_events if e.data.get("user_id") == user_id] or all_business_events
        else:
            scoped_events = all_business_events

        total_scoped_events = len(scoped_events)

        if target_event_id:
            matched_idx = next((i for i, e in enumerate(scoped_events, 1) if e.id == target_event_id), None)
            if matched_idx is not None:
                step_index, target_event = matched_idx, scoped_events[matched_idx - 1]
            else:
                all_idx = next((i for i, e in enumerate(all_business_events, 1) if e.id == target_event_id), None)
                if all_idx is not None:
                    user_id = "ALL"
                    scoped_events = all_business_events
                    total_scoped_events = len(scoped_events)
                    step_index, target_event = all_idx, scoped_events[all_idx - 1]
                else:
                    step_index, target_event = total_scoped_events, scoped_events[-1]
        elif event_number is not None:
            step_index = max(1, min(event_number, total_scoped_events))
            target_event = scoped_events[step_index - 1]
        else:
            step_index = total_scoped_events
            target_event = scoped_events[-1]

        state_at_step = self.replay_engine.replay_until_event_id(target_event.id)
        state_before = self.replay_engine.replay_before_event_id(target_event.id)
        abs_index = next((i for i, e in enumerate(all_business_events, 1) if e.id == target_event.id), step_index)

        self.make_label(self.main_container, text="TIME MACHINE", size=22, bold=True).pack(
            anchor="w", pady=(10, 2)
        )
        self.make_label(
            self.main_container,
            text="Interactive step-by-step state replayer. Rebuilds the exact state of users, wallets, and orders as they existed at this precise moment in time.",
            fg=self.MUTED_COLOR,
            size=11,
        ).pack(anchor="w", pady=(0, 14))

        # Scope selector
        user_selector_card = self.make_card(self.main_container)
        user_selector_card.pack(fill="x", pady=(0, 14))

        user_sel_inner = tk.Frame(user_selector_card, bg=self.CARD_COLOR)
        user_sel_inner.pack(fill="x", padx=20, pady=10)

        self.make_label(
            user_sel_inner, text="👤 SELECT TIMELINE USER:", fg=self.ACCENT_COLOR, size=10, bold=True, width=22, anchor="w"
        ).pack(side="left", padx=(0, 8))

        tm_scope_specs = [(f"ALL USERS ({len(all_business_events)})", "ALL")] + [
            (
                f"{u['user_id']} ({u['name']}) [{len([e for e in all_business_events if e.data.get('user_id') == u['user_id']])}]",
                u["user_id"],
            )
            for u in active_users
        ]
        if ex_users:
            ex_event_count = len([e for e in all_business_events if e.data.get("user_id") in ex_uids])
            tm_scope_specs.append((f"📁 OTHER (Ex-Users: {len(ex_users)} | {ex_event_count} Evt)", "EX_USERS"))

        for label, val in tm_scope_specs:
            is_act = user_id == val
            self.make_button(
                user_sel_inner,
                text=label,
                bg=self.ACCENT_COLOR if is_act else self.BUTTON_COLOR,
                fg="#07111f" if is_act else self.TEXT_COLOR,
                padx=10,
                pady=4,
                command=lambda t=val: self.show_time_machine(user_id=t),
            ).pack(side="left", padx=3)

        # Controls & Playback Card
        nav_card = self.make_card(self.main_container)
        nav_card.pack(fill="x", pady=(0, 16))

        top_info = tk.Frame(nav_card, bg=self.CARD_COLOR)
        top_info.pack(fill="x", padx=24, pady=(16, 10))

        u_name_str = ""
        if user_id == "EX_USERS":
            replay_heading = f"📁 EX-USERS / OTHER ─ STEP #{step_index} OF {total_scoped_events} : {target_event.type.upper()}"
        elif user_id != "ALL":
            u_obj = next((u for u in all_users if u["user_id"] == user_id), None)
            u_name_str = f" ({u_obj['name']})" if u_obj else ""
            replay_heading = f"👤 USER {user_id}{u_name_str} ─ STEP #{step_index} OF {total_scoped_events} : {target_event.type.upper()}"
        else:
            replay_heading = f"🌐 GLOBAL STEP #{step_index} OF {total_scoped_events} : {target_event.type.upper()}"

        self.make_label(top_info, text=replay_heading, fg=self.ACCENT_COLOR, size=13, bold=True).pack(side="left")
        self.make_button(top_info, text="📋 BACK TO TIMELINE", padx=12, pady=4, command=self.show_event_history).pack(side="right")

        # Step Progress Dots
        timeline_bar = tk.Frame(nav_card, bg=self.INPUT_COLOR)
        timeline_bar.pack(fill="x", padx=24, pady=(0, 14), ipady=6)

        window_start = max(1, step_index - 3)
        window_end = min(total_scoped_events, step_index + 3)
        timeline_steps = [
            f"● Step #{i} ({scoped_events[i-1].type.split('.')[-1]})"
            if i == step_index
            else f"Step #{i} ({scoped_events[i-1].type.split('.')[-1]})"
            for i in range(window_start, window_end + 1)
        ]
        step_display = ("… ─── " if window_start > 1 else "") + " ─── ".join(timeline_steps) + (" ─── …" if window_end < total_scoped_events else "")
        self.make_label(timeline_bar, text=step_display, bg=self.INPUT_COLOR, fg=self.ACCENT_COLOR, size=10, bold=True).pack(pady=4)

        # Player buttons
        controls_frame = tk.Frame(nav_card, bg=self.CARD_COLOR)
        controls_frame.pack(fill="x", padx=24, pady=(0, 18))

        nav_buttons = [
            ("⏮ First (#1)", 1, step_index > 1),
            ("◀ Previous", max(1, step_index - 1), step_index > 1),
            ("Next ▶", min(total_scoped_events, step_index + 1), step_index < total_scoped_events),
            (f"Latest (#{total_scoped_events}) ⏭", total_scoped_events, step_index < total_scoped_events),
        ]
        for btn_text, target_step, enabled in nav_buttons:
            b = self.make_button(
                controls_frame,
                text=btn_text,
                padx=12,
                pady=6,
                cursor="hand2" if enabled else "arrow",
                command=lambda s=target_step: self.show_time_machine(s, user_id=user_id),
            )
            b.pack(side="left", padx=(0, 16 if "Latest" in btn_text else 6))
            if not enabled:
                b.configure(state="disabled", bg=self.INPUT_COLOR, fg=self.MUTED_COLOR)

        # Jump dropdown
        jump_frame = tk.Frame(controls_frame, bg=self.CARD_COLOR)
        jump_frame.pack(side="left")
        self.make_label(jump_frame, text="Jump To:", fg=self.MUTED_COLOR, size=9, bold=True).pack(side="left", padx=(0, 6))

        jump_options = [f"Step #{idx}: {ev.type}" for idx, ev in enumerate(scoped_events, 1)]
        jump_var = tk.StringVar(value=f"Step #{step_index}: {target_event.type}")
        self.make_dropdown(
            jump_frame,
            values=jump_options,
            textvariable=jump_var,
            command=lambda val: self.show_time_machine(
                int(val.split(":")[0].replace("Step #", "").strip()), user_id=user_id
            ),
            font=("Segoe UI", 9),
            width=24,
        ).pack(side="left")

        # Action Buttons
        if step_index < total_scoped_events:
            action_btn_box = tk.Frame(controls_frame, bg=self.CARD_COLOR)
            action_btn_box.pack(side="right")

            self.make_accent_button(
                action_btn_box,
                text=f"⏪ REWIND TO STEP #{step_index}",
                padx=12,
                pady=6,
                command=lambda: self._rewind_to_event(target_event.id, user_id),
            ).pack(side="left", padx=(0, 6))

            self.make_button(
                action_btn_box,
                text="🔄 RESTORE (APPEND-ONLY)",
                bg="#0284c7",
                fg="#ffffff",
                active_bg="#38bdf8",
                active_fg="#07111f",
                padx=12,
                pady=6,
                command=lambda: self._restore_state_from_event(target_event.id, abs_index),
            ).pack(side="left")
        else:
            self.make_accent_button(
                controls_frame, text="⚡ SIMULATE NEW EVENT", padx=14, pady=6, command=self.show_dashboard
            ).pack(side="right")

        # What Changed card
        impact_card = self.make_card(self.main_container, bg=self.INPUT_COLOR)
        impact_card.pack(fill="x", pady=(0, 16))

        imp_inner = tk.Frame(impact_card, bg=self.INPUT_COLOR)
        imp_inner.pack(fill="x", padx=20, pady=12)

        self.make_label(
            imp_inner, text="⚡  WHAT CHANGED AT THIS STEP", bg=self.INPUT_COLOR, fg=self.ACCENT_COLOR, size=10, bold=True
        ).pack(anchor="w")

        friendly_impact = self._get_event_friendly_impact(target_event, state_before, state_at_step)
        self.make_label(
            imp_inner,
            text=f"Event #{abs_index} ({target_event.type}): {friendly_impact}",
            bg=self.INPUT_COLOR,
            size=11,
            wraplength=1050,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # Diagnostics card
        diag = self.replay_engine.get_diagnostics_for_event_id(target_event.id)
        if not diag.get("is_valid", True):
            warn_card = self.make_card(
                self.main_container, bg="#260f1b", highlightbackground=self.ERROR_COLOR, highlightthickness=2
            )
            warn_card.pack(fill="x", pady=(0, 16))

            w_inner = tk.Frame(warn_card, bg="#260f1b")
            w_inner.pack(fill="x", padx=20, pady=14)

            self.make_label(
                w_inner, text="❌  SYSTEM INVARIANT VIOLATION DETECTED", bg="#260f1b", fg=self.ERROR_COLOR, size=13, bold=True
            ).pack(anchor="w")

            reason_str = diag.get("reason", "Invariant violated.")
            if "deficit" in diag:
                reason_str += f" (Deficit: ₹{diag['deficit']:.2f}, Balance before: ₹{diag['balance_before']:.2f})"

            self.make_label(
                w_inner,
                text=f"This event resulted in an invalid state: {reason_str}\nChronoReplay identified this invariant violation deterministically during state replay.",
                bg="#260f1b",
                fg="#fca5a5",
                size=10,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))
        else:
            ok_card = self.make_card(self.main_container, highlightbackground=self.SUCCESS_COLOR)
            ok_card.pack(fill="x", pady=(0, 16))

            ok_inner = tk.Frame(ok_card, bg=self.CARD_COLOR)
            ok_inner.pack(fill="x", padx=20, pady=8)

            self.make_label(
                ok_inner,
                text="✓  SYSTEM STATE INTEGRITY: VALID (All wallet invariants & order consistency rules passed at this step)",
                fg=self.SUCCESS_COLOR,
                size=10,
                bold=True,
            ).pack(side="left")

        # Visual Dashboard Cards
        users = state_at_step.get("users", {})
        orders = state_at_step.get("orders", {})
        payments = state_at_step.get("payments", [])

        display_orders = {oid: o for oid, o in orders.items() if o.get("user_id") == user_id} if user_id != "ALL" else orders
        display_payments = [p for p in payments if p.get("user_id") == user_id] if user_id != "ALL" else payments

        state_dashboard = tk.Frame(self.main_container, bg=self.BG_COLOR)
        state_dashboard.pack(fill="x", pady=(0, 16))

        # Left Column: User Wallets
        left_col = self.make_card(state_dashboard)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        wallets_title = f"👤 USER WALLETS ({len(users)})" if user_id == "ALL" else f"👤 USER WALLET: {user_id}"
        self.make_label(left_col, text=wallets_title, fg=self.ACCENT_COLOR, size=12, bold=True).pack(
            anchor="w", padx=16, pady=(14, 10)
        )

        if users:
            sorted_uids = list(users.keys())
            if user_id != "ALL" and user_id in users:
                sorted_uids.remove(user_id)
                sorted_uids.insert(0, user_id)

            for uid in sorted_uids:
                user = users[uid]
                is_del = user.get("status") == "deleted" or user.get("deleted")
                is_scoped = user_id != "ALL" and uid == user_id
                card_bg = "#1a131b" if is_del else ("#132338" if is_scoped else self.INPUT_COLOR)
                border_col = "#f59e0b" if is_del else (self.ACCENT_COLOR if is_scoped else self.BORDER_COLOR)
                u_card = self.make_card(left_col, bg=card_bg, highlightbackground=border_col)
                u_card.pack(fill="x", padx=14, pady=4)

                u_top = tk.Frame(u_card, bg=card_bg)
                u_top.pack(fill="x", padx=12, pady=(8, 4))

                scope_badge = " [SELECTED] " if is_scoped else ""
                name_prefix = "Ex-User: " if is_del else ""
                name_color = "#fca5a5" if is_del else (self.ACCENT_COLOR if is_scoped else self.TEXT_COLOR)
                self.make_label(
                    u_top,
                    text=f"{name_prefix}{user.get('name', 'User')} ({uid}){scope_badge}",
                    bg=card_bg,
                    fg=name_color,
                    size=11,
                    bold=True,
                ).pack(side="left")

                bal = user.get("balance", 0.0)
                self.make_label(
                    u_top,
                    text=f"₹{bal:.2f}",
                    bg=card_bg,
                    fg=self.MUTED_COLOR if is_del else (self.SUCCESS_COLOR if bal >= 0 else self.ERROR_COLOR),
                    size=13,
                    bold=True,
                ).pack(side="right")

                u_bot = tk.Frame(u_card, bg=card_bg)
                u_bot.pack(fill="x", padx=12, pady=(0, 8))
                status_txt = "DELETED (EX-USER)" if is_del else user.get("status", "active").upper()
                self.make_label(
                    u_bot,
                    text=f"Email: {user.get('email', 'N/A')}  •  Status: {status_txt}",
                    bg=card_bg,
                    fg="#f59e0b" if is_del else self.MUTED_COLOR,
                    size=9,
                ).pack(side="left")
        else:
            self.make_label(left_col, text="No users created as of this step.", fg=self.MUTED_COLOR, size=10).pack(padx=16, pady=20)

        # Right Column: Orders & Payments
        right_col = self.make_card(state_dashboard)
        right_col.pack(side="left", fill="both", expand=True, padx=(8, 0))

        orders_title = (
            f"📦 ORDERS ({len(display_orders)}) & PAYMENTS ({len(display_payments)})"
            if user_id == "ALL"
            else f"📦 {user_id} ORDERS ({len(display_orders)}) & PAYMENTS ({len(display_payments)})"
        )
        self.make_label(right_col, text=orders_title, fg=self.ACCENT_COLOR, size=12, bold=True).pack(
            anchor="w", padx=16, pady=(14, 10)
        )

        if display_orders:
            for oid, order in display_orders.items():
                o_card = self.make_card(right_col, bg=self.INPUT_COLOR)
                o_card.pack(fill="x", padx=14, pady=4)

                o_top = tk.Frame(o_card, bg=self.INPUT_COLOR)
                o_top.pack(fill="x", padx=12, pady=(8, 4))

                self.make_label(o_top, text=f"Order {oid} ({order.get('user_id', '')})", bg=self.INPUT_COLOR, size=10, bold=True).pack(side="left")

                amt = order.get("amount", 0.0)
                st = order.get("status", "pending").upper()
                st_color = self.SUCCESS_COLOR if st in ["PAID", "COMPLETED"] else self.WARNING_COLOR
                self.make_label(o_top, text=f"₹{amt:.2f}  [{st}]", bg=self.INPUT_COLOR, fg=st_color, size=10, bold=True).pack(side="right")
        else:
            self.make_label(right_col, text="No orders recorded as of this step.", fg=self.MUTED_COLOR, size=10).pack(padx=16, pady=20)

        # Raw State Inspection Text Area
        raw_card = self.make_card(self.main_container)
        raw_card.pack(fill="both", expand=True, pady=(0, 24))

        raw_top = tk.Frame(raw_card, bg=self.CARD_COLOR)
        raw_top.pack(fill="x", padx=20, pady=(14, 6))

        user_focus_str = f" ─ FOCUSED USER: {user_id}" if user_id != "ALL" else ""
        self.make_label(
            raw_top,
            text=f"🔍 COMPLETE RECONSTRUCTED STATE SNAPSHOT (STEP #{abs_index}){user_focus_str}",
            fg=self.MUTED_COLOR,
            size=10,
            bold=True,
        ).pack(side="left")

        state_frame = tk.Frame(raw_card, bg=self.INPUT_COLOR)
        state_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        scroll = tk.Scrollbar(state_frame, bg=self.INPUT_COLOR)
        scroll.pack(side="right", fill="y")

        self.replay_state_text = tk.Text(
            state_frame,
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            insertbackground=self.TEXT_COLOR,
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
            height=14,
            yscrollcommand=scroll.set,
        )
        self.replay_state_text.pack(fill="both", expand=True, padx=(10, 0), pady=8)
        scroll.config(command=self.replay_state_text.yview)

        self._display_replay_state(state_at_step, abs_index, selected_user_id=user_id)

    def _display_replay_state(self, state, event_number, selected_user_id="ALL"):
        self.replay_state_text.configure(state="normal")
        self.replay_state_text.delete("1.0", "end")

        users = state.get("users", {})
        orders = state.get("orders", {})
        payments = state.get("payments", [])

        total_balance = sum(u.get("balance", 0) for u in users.values())
        scope_info = f"  |  Focused User: {selected_user_id}" if selected_user_id != "ALL" else ""
        summary = (
            f"STATE SNAPSHOT #{event_number}  |  Users: {len(users)}  |  Orders: {len(orders)}  |  "
            f"Payments: {len(payments)}  |  Total System Wallet Balance: ₹{total_balance:.2f}{scope_info}\n"
            + "=" * 76
            + "\n\n"
        )
        self.replay_state_text.insert("end", summary)

        # Focused User Highlight
        if selected_user_id != "ALL" and selected_user_id in users:
            sel_u = users[selected_user_id]
            sel_bal = sel_u.get("balance", 0.0)
            sel_orders = [o for o in orders.values() if o.get("user_id") == selected_user_id]
            sel_pmts = [p for p in payments if p.get("user_id") == selected_user_id]
            self.replay_state_text.insert(
                "end",
                f"🎯 FOCUSED USER SNAPSHOT: {sel_u.get('name', 'User')} ({selected_user_id})\n"
                f"────────────────────────────────────────────────────────────────────────────\n"
                f"  • Name   : {sel_u.get('name', '')}\n"
                f"  • Email  : {sel_u.get('email', '')}\n"
                f"  • Status : {sel_u.get('status', 'active').upper()}\n"
                f"  • Balance: ₹{sel_bal:.2f}\n"
                f"  • Orders : {len(sel_orders)} order(s)\n"
                f"  • Payments: {len(sel_pmts)} transaction(s)\n\n",
            )

        self.replay_state_text.insert(
            "end", "USERS & WALLETS\n────────────────────────────────────────────────────────────────────────────\n"
        )
        if users:
            sorted_uids = list(users.keys())
            if selected_user_id != "ALL" and selected_user_id in users:
                sorted_uids.remove(selected_user_id)
                sorted_uids.insert(0, selected_user_id)

            for uid in sorted_uids:
                u = users[uid]
                tag = "  [★ SELECTED USER]" if (selected_user_id != "ALL" and uid == selected_user_id) else ""
                self.replay_state_text.insert(
                    "end",
                    f"  • User: {u.get('name', '')} ({uid}){tag}\n"
                    f"    Email  : {u.get('email', '')}\n"
                    f"    Status : {u.get('status', 'active')}\n"
                    f"    Balance: ₹{u.get('balance', 0):.2f}\n\n",
                )
        else:
            self.replay_state_text.insert("end", "  No users in state.\n\n")

        self.replay_state_text.insert(
            "end", "ORDERS\n────────────────────────────────────────────────────────────────────────────\n"
        )
        if orders:
            sorted_orders = list(orders.items())
            if selected_user_id != "ALL":
                user_ords = [o for o in sorted_orders if o[1].get("user_id") == selected_user_id]
                other_ords = [o for o in sorted_orders if o[1].get("user_id") != selected_user_id]
                sorted_orders = user_ords + other_ords

            for oid, order in sorted_orders:
                is_u = selected_user_id != "ALL" and order.get("user_id") == selected_user_id
                tag = "  [★ SELECTED USER ORDER]" if is_u else ""
                self.replay_state_text.insert(
                    "end",
                    f"  • Order ID: {oid}{tag}\n"
                    f"    User   : {order.get('user_id', '')}\n"
                    f"    Amount : ₹{order.get('amount', 0):.2f}\n"
                    f"    Payment: ₹{order.get('paid_amount', 0.0):.2f}\n"
                    f"    Status : {order.get('status', 'pending')}\n\n",
                )
        else:
            self.replay_state_text.insert("end", "  No orders in state.\n\n")

        self.replay_state_text.insert(
            "end", "PAYMENTS\n────────────────────────────────────────────────────────────────────────────\n"
        )
        if payments:
            sorted_payments = list(payments)
            if selected_user_id != "ALL":
                user_pmts = [p for p in sorted_payments if p.get("user_id") == selected_user_id]
                other_pmts = [p for p in sorted_payments if p.get("user_id") != selected_user_id]
                sorted_payments = user_pmts + other_pmts

            for p in sorted_payments:
                is_u = selected_user_id != "ALL" and p.get("user_id") == selected_user_id
                tag = "  [★ SELECTED USER]" if is_u else ""
                ord_info = f" (Order: {p.get('order_id')})" if p.get("order_id") else ""
                self.replay_state_text.insert(
                    "end",
                    f"  • Payment: ₹{p.get('amount', 0):.2f} via {p.get('method', 'UPI')} (User: {p.get('user_id')}){ord_info} [{p.get('status', 'success').upper()}]{tag}\n",
                )
        else:
            self.replay_state_text.insert("end", "  No payments recorded.\n")

        self.replay_state_text.configure(state="disabled")

    def _rewind_to_event(self, target_event_id, user_id=None):
        target_event = self.store.get(target_event_id)
        if not target_event:
            return

        confirm = messagebox.askyesno(
            "Time Machine — Rewind",
            f"Are you sure you want to rewind the application state to event '{target_event.type}'?\n\n"
            f"The application state will be reconstructed exactly as it was at this point in time.\n\n"
            f"No events will be deleted. All subsequent events will remain safely stored in the Event Store.",
        )
        if confirm:
            state = self.replay_engine.replay_until_event_id(target_event.id)
            users = state.get("users", {})
            if users:
                target_uid = user_id if (user_id and user_id in users) else list(users.keys())[-1]
                u = users[target_uid]
                self.simulator.select_user(target_uid, u.get("name"), u.get("email"))

            messagebox.showinfo(
                "Time Machine — Rewind",
                f"Application state rewound to event '{target_event.type}'.\n\n"
                f"All events remain safely stored in the Event Store.\n"
                f"State reconstruction and simulator context updated.",
            )
            self.show_time_machine(target_event_id=target_event.id, user_id=user_id)

    def _restore_state_from_event(self, target_event_id, abs_step_number=None):
        target_event = self.store.get(target_event_id)
        if not target_event:
            return

        confirm = messagebox.askyesno(
            "Time Machine — Restore State",
            f"Are you sure you want to restore the application state from event '{target_event.type}'?\n\n"
            f"This will bring this historical state forward as the active state by appending an immutable 'state.restored' event to the Event Store.\n\n"
            f"No events will be deleted. All previous events remain safely stored in the Event Store.",
        )
        if confirm:
            all_store_events = self.store.get_all()
            exact_store_index = next(
                (i for i, e in enumerate(all_store_events, 1) if e.id == target_event.id),
                abs_step_number or 1,
            )

            target_uid = target_event.data.get("user_id", "System")
            restored_event = Event.create(
                event_type="state.restored",
                data={
                    "source_event_number": exact_store_index,
                    "source_event_id": target_event.id,
                    "source_event_type": target_event.type,
                    "user_id": target_uid,
                },
            )
            self.store.append(restored_event)

            state = self.replay_engine.replay_all()
            users = state.get("users", {})
            if target_uid in users:
                u = users[target_uid]
                self.simulator.select_user(target_uid, u.get("name"), u.get("email"))
                self.history_user_filter_var.set(target_uid)
            elif users:
                last_user_id = list(users.keys())[-1]
                last_user = users[last_user_id]
                self.simulator.select_user(last_user_id, last_user.get("name"), last_user.get("email"))
                self.history_user_filter_var.set(last_user_id)

            self.history_date_filter_var.set("ALL")

            messagebox.showinfo(
                "State Restored (Append-Only)",
                f"Successfully restored state from event '{target_event.type}'.\n\n"
                f"A new 'state.restored' event has been appended to the ledger.\n"
                f"The complete event history remains 100% immutable and intact.",
            )
            self.show_event_history()

    def _delete_events_permanently(self, target_event_id, user_id=None):
        target_event = self.store.get(target_event_id)
        if not target_event:
            return

        confirm = messagebox.askyesno(
            "Delete Events",
            f"This action will permanently remove all subsequent events after '{target_event.type}' from the Event Store.\n"
            f"This cannot be undone.\n\n"
            f"Are you sure you want to permanently delete all subsequent events?",
        )
        if confirm:
            deleted_count = self.store.delete_events_after(target_event.id)
            state = self.replay_engine.replay_until_event_id(target_event.id)
            users = state.get("users", {})
            if users:
                last_user_id = list(users.keys())[-1]
                last_user = users[last_user_id]
                self.simulator.select_user(last_user_id, last_user.get("name"), last_user.get("email"))
            messagebox.showinfo(
                "Events Deleted",
                f"Permanently removed {deleted_count} event(s) from the event store.",
            )
            self.show_dashboard()

    # =========================================================
    # 3. WORKSPACE & FILE RECOVERY VIEW
    # =========================================================

    def show_workspace(self):
        self._clear_main_area()

        self.make_label(
            self.main_container, text="WORKSPACE & FILE RECOVERY", size=22, bold=True
        ).pack(anchor="w", pady=(10, 2))
        self.make_label(
            self.main_container,
            text="File time machine with non-destructive restoration. Scan workspace to detect and record changes, inspect version history, and restore physical files.",
            fg=self.MUTED_COLOR,
            size=11,
        ).pack(anchor="w", pady=(0, 18))

        # Active workspace bar
        dir_card = self.make_card(self.main_container)
        dir_card.pack(fill="x", pady=(0, 18))

        self.make_label(
            dir_card, text="ACTIVE WORKSPACE DIRECTORY", fg=self.ACCENT_COLOR, size=14, bold=True
        ).pack(anchor="w", padx=24, pady=(18, 4))

        selector_frame = tk.Frame(dir_card, bg=self.CARD_COLOR)
        selector_frame.pack(fill="x", padx=24, pady=(0, 16))

        border = tk.Frame(selector_frame, bg=self.BORDER_COLOR)
        border.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.make_entry(border, textvariable=self.workspace_path_var).pack(
            fill="both", expand=True, padx=1, pady=1, ipady=5
        )

        self.make_button(
            selector_frame, text="SELECT WORKSPACE", padx=16, pady=6, command=self._browse_workspace_folder
        ).pack(side="left", padx=(0, 8))

        self.make_accent_button(
            selector_frame, text="SCAN WORKSPACE", padx=18, pady=6, command=self.scan_workspace
        ).pack(side="left", padx=(0, 8))

        self.make_button(
            selector_frame, text="REFRESH", padx=14, pady=6, command=self._populate_workspace_files
        ).pack(side="left")

        # Two-column layout
        columns_frame = tk.Frame(self.main_container, bg=self.BG_COLOR)
        columns_frame.pack(fill="both", expand=True, pady=(0, 24))

        left_card = self.make_card(columns_frame)
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.make_label(left_card, text="WORKSPACE FILES", fg=self.ACCENT_COLOR, size=13, bold=True).pack(
            anchor="w", padx=18, pady=(16, 4)
        )

        folder_name = os.path.basename(self.workspace_path_var.get()) or "workspace"
        self.make_label(left_card, text=f"📁 {folder_name}", size=11, bold=True).pack(
            anchor="w", padx=18, pady=(0, 10)
        )

        files_listbox_frame = tk.Frame(left_card, bg=self.INPUT_COLOR)
        files_listbox_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))

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
        self.files_listbox.bind("<<ListboxSelect>>", self._on_workspace_file_selected)

        self.right_card = self.make_card(columns_frame)
        self.right_card.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self.version_history_title = self.make_label(
            self.right_card, text="VERSION HISTORY", fg=self.ACCENT_COLOR, size=13, bold=True
        )
        self.version_history_title.pack(anchor="w", padx=18, pady=(16, 4))

        self.version_container = tk.Frame(self.right_card, bg=self.CARD_COLOR)
        self.version_container.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self._populate_workspace_files()
        self._start_workspace_auto_watcher()

    def _start_workspace_auto_watcher(self):
        """Periodically check for filesystem changes in the workspace."""
        if hasattr(self, "_watcher_job") and self._watcher_job:
            try:
                self.root.after_cancel(self._watcher_job)
            except Exception:
                pass

        def _auto_sync_tick():
            try:
                if hasattr(self, "files_listbox") and self.files_listbox.winfo_exists():
                    summary = self.workspace_manager.scan_and_record_changes()
                    if summary.get("created", 0) > 0 or summary.get("modified", 0) > 0 or summary.get("deleted", 0) > 0:
                        self._populate_workspace_files()
                        if self.selected_workspace_file.get():
                            self._on_workspace_file_selected()
            except Exception:
                pass
            finally:
                self._watcher_job = self.root.after(1500, _auto_sync_tick)

        self._watcher_job = self.root.after(1500, _auto_sync_tick)

    def _browse_workspace_folder(self):
        folder = filedialog.askdirectory(initialdir=self.workspace_path_var.get())
        if folder:
            self._sync_workspace_path(folder)
            self.show_workspace()

    def scan_workspace(self):
        try:
            self._sync_workspace_path(self.workspace_path_var.get())
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
        """Populate workspace files list with status indicators."""
        self.files_listbox.delete(0, "end")

        current_path = os.path.abspath(str(self.workspace_path_var.get()).strip())
        if current_path != self.workspace_manager.workspace_path:
            self._sync_workspace_path(current_path)

        file_statuses = self.workspace_manager.get_workspace_files_with_status()
        if not file_statuses:
            self.files_listbox.insert("end", "  (No files found. Click SCAN WORKSPACE)")
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
        clean_path = raw_value.replace("📄", "").replace("🗑", "").split("[")[0].strip()
        self.selected_workspace_file.set(clean_path)

        for widget in self.version_container.winfo_children():
            widget.destroy()

        self.version_history_title.configure(text=f"VERSION HISTORY: {clean_path}")

        try:
            history = self.version_history.get_file_history(clean_path, self.workspace_path)
        except ValueError as exc:
            self.make_label(self.version_container, text=str(exc), fg=self.ERROR_COLOR, size=10).pack(pady=20)
            return

        if not history:
            self.make_label(
                self.version_container,
                text="No historical versions recorded. Click [SCAN WORKSPACE] to track changes.",
                fg=self.MUTED_COLOR,
                size=10,
            ).pack(pady=20)
            return

        for version in history:
            row = self.make_card(self.version_container, bg=self.INPUT_COLOR)
            row.pack(fill="x", pady=3)

            ts = version.timestamp.split("T")[1].split("+")[0] if "T" in version.timestamp else version.timestamp

            if version.is_deleted():
                action_text, action_color = "DELETED", self.ERROR_COLOR
            elif version.event_type == "file.restored":
                action_text, action_color = "RESTORED", self.SUCCESS_COLOR
            elif version.event_type == "file.created":
                action_text, action_color = "CREATED", self.ACCENT_COLOR
            else:
                action_text, action_color = "MODIFIED", self.WARNING_COLOR

            info_frame = tk.Frame(row, bg=self.INPUT_COLOR)
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            self.make_label(
                info_frame,
                text=f"VERSION #{version.version}  •  {action_text}",
                bg=self.INPUT_COLOR,
                fg=action_color,
                size=9,
                bold=True,
            ).pack(anchor="w")

            self.make_label(
                info_frame,
                text=f"Time: {ts} | Snapshot: {version.snapshot_id or 'Deleted'}",
                bg=self.INPUT_COLOR,
                fg=self.MUTED_COLOR,
                size=8,
            ).pack(anchor="w", pady=(2, 0))

            if version.snapshot_id:
                self.make_accent_button(
                    row,
                    text="RESTORE",
                    padx=10,
                    pady=4,
                    size=8,
                    command=lambda v=version, p=clean_path: self._restore_file_version(p, v),
                ).pack(side="right", padx=(4, 8), pady=6)

                self.make_button(
                    row,
                    text="VIEW",
                    padx=10,
                    pady=4,
                    size=8,
                    command=lambda v=version: self._view_file_version(v),
                ).pack(side="right", padx=4, pady=6)

    def _view_file_version(self, version):
        curr = self.version_history.get_content(version.file_path, version.version) or ""
        prev = self.version_history.get_content(version.file_path, version.version - 1) or "" if version.version > 1 else ""

        diff = list(
            difflib.unified_diff(
                prev.splitlines(),
                curr.splitlines(),
                fromfile=f"v{version.version-1}" if version.version > 1 else "initial",
                tofile=f"v{version.version}",
                lineterm="",
            )
        )
        change_text = "\n".join(diff) if diff else (curr if curr else "(Empty or no changes)")

        viewer = tk.Toplevel(self.root)
        viewer.title(f"Changes in v{version.version}: {version.file_path}")
        viewer.geometry("560x360")
        viewer.configure(bg=self.BG_COLOR)

        self.make_label(
            viewer,
            text=f"CHANGE IN v{version.version} • {version.file_path}",
            bg=self.BG_COLOR,
            fg=self.ACCENT_COLOR,
            size=11,
            bold=True,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        self.make_label(
            viewer,
            text=f"Event: {version.event_type} | Time: {version.timestamp[:19] if version.timestamp else 'N/A'}",
            bg=self.BG_COLOR,
            fg=self.MUTED_COLOR,
            size=8,
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
        confirm = messagebox.askyesnocancel(
            "Confirm File Restore",
            f"Restore {file_path} to Version #{version.version}?\n\n"
            f"Snapshot ID: {version.snapshot_id or 'N/A'}\n"
            "• Yes = overwrite the current file with the historical version\n"
            "• No = keep the current file and restore only missing historical lines\n"
            "• Cancel = do nothing",
        )
        if confirm is None:
            return

        merge_with_current = not confirm
        selected_line_indexes = None
        if merge_with_current:
            try:
                current_content = self.version_history.get_content(file_path, self.version_history.get_version_index(file_path, version.version) if hasattr(self.version_history, "get_version_index") else version.version) or ""
                historical_content = self.version_history.get_content(file_path, version.version) or ""
                if historical_content:
                    lines = historical_content.splitlines()
                    if len(lines) > 1:
                        selector = tk.Toplevel(self.root)
                        selector.title(f"Select lines to restore from {file_path}")
                        selector.geometry("420x320")
                        selector.configure(bg=self.BG_COLOR)

                        self.make_label(
                            selector,
                            text=f"Choose lines from Version #{version.version} to restore",
                            bg=self.BG_COLOR,
                            fg=self.ACCENT_COLOR,
                            size=10,
                            bold=True,
                        ).pack(anchor="w", padx=12, pady=(10, 4))

                        listbox = tk.Listbox(
                            selector,
                            bg=self.INPUT_COLOR,
                            fg=self.TEXT_COLOR,
                            selectbackground=self.BUTTON_ACTIVE,
                            relief="flat",
                            bd=0,
                            font=("Consolas", 9),
                            selectmode="extended",
                        )
                        listbox.pack(fill="both", expand=True, padx=12, pady=(0, 8))

                        for idx, line in enumerate(lines, start=1):
                            if not line.strip():
                                listbox.insert("end", f"{idx}: <blank>")
                            else:
                                listbox.insert("end", f"{idx}: {line}")

                        selection_result = {"value": None}

                        def _apply_selection():
                            selection = listbox.curselection()
                            selection_result["value"] = [int(item) - 1 for item in selection]
                            selector.destroy()

                        def _cancel_selection():
                            selection_result["value"] = []
                            selector.destroy()

                        btn_row = tk.Frame(selector, bg=self.BG_COLOR)
                        btn_row.pack(fill="x", padx=12, pady=(0, 12))
                        self.make_button(btn_row, text="RESTORE SELECTED", padx=12, pady=5, command=_apply_selection).pack(side="right")
                        self.make_button(btn_row, text="AUTO MISSING LINES", padx=12, pady=5, command=_cancel_selection).pack(side="right", padx=(0, 8))

                        selector.transient(self.root)
                        selector.grab_set()
                        self.root.wait_window(selector)
                        selected_line_indexes = selection_result["value"]
                        if selected_line_indexes is None:
                            selected_line_indexes = []
            except Exception:
                selected_line_indexes = None

        try:
            if version.snapshot_id:
                self.restore_manager.restore(
                    version.snapshot_id,
                    merge_with_current=merge_with_current,
                    previous_line_count=None,
                    selected_line_indexes=selected_line_indexes,
                )
            else:
                self.restore_manager.restore_version(
                    file_path,
                    version.version,
                    merge_with_current=merge_with_current,
                    previous_line_count=None,
                    selected_line_indexes=selected_line_indexes,
                )

            self.workspace_manager.scan_and_record_changes()

            restored_content = self.version_history.get_content(file_path, version.version)
            line_count = len(restored_content.splitlines()) if restored_content else 0

            action_text = "fully replaced the current file" if not merge_with_current else "kept the current file and restored only the missing or selected historical lines"
            messagebox.showinfo(
                "File Restored Successfully",
                f"✓ {file_path} has been restored to Version #{version.version}!\n\n"
                f"• Restored Lines: {line_count}\n"
                f"• Target File: {os.path.join(self.restore_manager.workspace_path, file_path)}\n\n"
                f"The file {action_text} on disk.",
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
