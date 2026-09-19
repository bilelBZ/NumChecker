"""Standalone Windows Desktop GUI for WhatsApp & Telegram Number Checker.

Built with CustomTkinter for high-DPI modern dark UI.
"""
import asyncio
import csv
import os
import sys
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from PIL import Image

# Import core validation engine
from src.auth_whatsapp import (
    authenticate_whatsapp_interactive,
    get_whatsapp_session_dir,
    is_whatsapp_linked,
    unlink_whatsapp_session,
)
from src.models import (
    TelegramResult,
    ValidationRecord,
    WhatsAppResult,
    compute_lead_quality,
)
from src.utils.input_parser import (
    InputPhoneRecord,
    normalize_input_records,
    parse_csv_records,
)
from src.utils.rate_limiter import AsyncRateLimiter
from src.validators.phone import PhoneValidator
from src.validators.telegram import TelegramValidator
from src.validators.whatsapp import WhatsAppValidator

# Appearance settings
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class NumberCheckerApp(ctk.CTk):
    """Main Desktop Application Window."""

    def __init__(self):
        super().__init__()

        self.title("WhatsApp & Telegram Number Checker (CRM Lead Validator)")
        self.geometry("1180x800")
        self.minsize(980, 700)

        # Set window icon
        icon_path = os.path.join(os.path.dirname(__file__), "logo.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # State variables
        self.is_running = False
        self.is_linking_wa = False
        self.should_stop = False
        self.loaded_records: List[InputPhoneRecord] = []
        self.validation_results: List[ValidationRecord] = []
        self.selected_file_path = ""

        # Check initial WhatsApp connection
        wa_already_linked = is_whatsapp_linked()

        # Credentials / Settings
        self.settings = {
            "whatsapp_token": os.getenv("WHATSAPP_API_TOKEN", ""),
            "whatsapp_phone_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
            "telegram_api_id": os.getenv("TELEGRAM_API_ID", ""),
            "telegram_api_hash": os.getenv("TELEGRAM_API_HASH", ""),
            "telegram_session": os.getenv("TELEGRAM_SESSION_STRING", ""),
            "simulation_mode": not wa_already_linked,
        }

        self._init_layout()

    def _init_layout(self):
        """Construct modern UI components."""
        # Top Header
        self.header_frame = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#11161d")
        self.header_frame.pack(fill="x", side="top")

        # Logo thumbnail in header
        logo_path = os.path.join(os.path.dirname(__file__), "logo.jpg")
        if os.path.exists(logo_path):
            try:
                pil_img = Image.open(logo_path)
                self.logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(42, 42))
                self.logo_label = ctk.CTkLabel(self.header_frame, image=self.logo_img, text="")
                self.logo_label.pack(side="left", padx=(20, 10), pady=12)
            except Exception:
                pass

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="WhatsApp & Telegram Number Checker",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff"
        )
        self.title_label.pack(side="left", pady=12)

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="  |  B2B CRM Lead Intelligence & Contact Validator",
            font=ctk.CTkFont(size=13),
            text_color="#8b949e"
        )
        self.subtitle_label.pack(side="left", pady=16)

        # Settings button in header right
        self.btn_settings = ctk.CTkButton(
            self.header_frame,
            text="⚙️ Settings",
            width=100,
            fg_color="#21262d",
            hover_color="#30363d",
            command=self._open_settings
        )
        self.btn_settings.pack(side="right", padx=20, pady=16)

        # Main horizontal container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=15)

        # Left Sidebar (Inputs & Controls) - scrollable frame for flexible window sizing
        self.left_panel = ctk.CTkScrollableFrame(self.main_container, width=340, corner_radius=12)
        self.left_panel.pack(side="left", fill="y", padx=(0, 15), pady=0)

        # Right Content Area (Metrics & Results Table)
        self.right_panel = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color="#161b22")
        self.right_panel.pack(side="right", fill="both", expand=True)

        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        """Construct input tabs and controls."""
        self.tabview = ctk.CTkTabview(self.left_panel, corner_radius=10)
        self.tabview.pack(fill="x", padx=8, pady=(5, 0))

        self.tab_csv = self.tabview.add("📁 Upload CSV")
        self.tab_manual = self.tabview.add("✍️ Paste Numbers")

        # CSV Upload Tab
        self.btn_browse = ctk.CTkButton(
            self.tab_csv,
            text="Choose CSV / File...",
            command=self._browse_file,
            fg_color="#238636",
            hover_color="#2ea043"
        )
        self.btn_browse.pack(fill="x", padx=10, pady=(15, 10))

        self.lbl_file_name = ctk.CTkLabel(
            self.tab_csv,
            text="No file selected\n(Supports Apollo, HubSpot, raw CSV)",
            font=ctk.CTkFont(size=12),
            text_color="#8b949e",
            wraplength=270
        )
        self.lbl_file_name.pack(pady=5)

        # Manual Paste Tab
        self.txt_manual = ctk.CTkTextbox(self.tab_manual, height=110)
        self.txt_manual.pack(fill="both", expand=True, padx=5, pady=5)
        self.txt_manual.insert("1.0", "+14155552671\n+33612345678\n+447911123456")

        # Platform Selection
        self.lbl_opts = ctk.CTkLabel(
            self.left_panel,
            text="Platforms to Validate",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_opts.pack(anchor="w", padx=12, pady=(12, 4))

        self.var_wa = ctk.BooleanVar(value=True)
        self.chk_wa = ctk.CTkCheckBox(
            self.left_panel,
            text="WhatsApp (Regular / Business)",
            variable=self.var_wa,
            text_color="#25D366"
        )
        self.chk_wa.pack(anchor="w", padx=12, pady=3)

        self.var_tg = ctk.BooleanVar(value=True)
        self.chk_tg = ctk.CTkCheckBox(
            self.left_panel,
            text="Telegram (Username & Premium)",
            variable=self.var_tg,
            text_color="#2AABEE"
        )
        self.chk_tg.pack(anchor="w", padx=12, pady=3)

        # WhatsApp Web Interactive Connection Box
        self.wa_box = ctk.CTkFrame(self.left_panel, fg_color="#11161d", corner_radius=8)
        self.wa_box.pack(fill="x", padx=10, pady=(10, 6))

        self.lbl_wa_box_title = ctk.CTkLabel(
            self.wa_box,
            text="WhatsApp Web Engine (100% Free)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#25D366"
        )
        self.lbl_wa_box_title.pack(anchor="w", padx=10, pady=(8, 2))

        # Status row with unlink button
        self.wa_status_frame = ctk.CTkFrame(self.wa_box, fg_color="transparent")
        self.wa_status_frame.pack(fill="x", padx=10, pady=(2, 6))

        linked = is_whatsapp_linked()
        status_text = "🟢 Linked & Ready" if linked else "⚪ Not Linked"
        status_color = "#2ea043" if linked else "#8b949e"

        self.lbl_wa_status = ctk.CTkLabel(
            self.wa_status_frame,
            text=status_text,
            font=ctk.CTkFont(size=12),
            text_color=status_color
        )
        self.lbl_wa_status.pack(side="left")

        self.btn_unlink_wa = ctk.CTkButton(
            self.wa_status_frame,
            text="Unlink",
            width=50,
            height=22,
            font=ctk.CTkFont(size=10),
            fg_color="#21262d",
            hover_color="#da3633",
            command=self._unlink_whatsapp
        )
        if linked:
            self.btn_unlink_wa.pack(side="right")

        self.btn_link_wa = ctk.CTkButton(
            self.wa_box,
            text="🔗 Link WhatsApp (Scan QR)",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#238636",
            hover_color="#2ea043",
            command=self._link_whatsapp
        )
        self.btn_link_wa.pack(fill="x", padx=10, pady=(2, 8))

        # Mode Selection Box (Live Mode vs Simulation)
        self.mode_box = ctk.CTkFrame(self.left_panel, fg_color="#11161d", corner_radius=8)
        self.mode_box.pack(fill="x", padx=10, pady=(4, 6))

        self.var_live_mode = ctk.BooleanVar(value=not self.settings["simulation_mode"])
        self.switch_live_mode = ctk.CTkSwitch(
            self.mode_box,
            text="🟢 Live Verification Mode",
            variable=self.var_live_mode,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_mode_toggled
        )
        self.switch_live_mode.pack(anchor="w", padx=10, pady=(8, 2))

        self.lbl_mode_desc = ctk.CTkLabel(
            self.mode_box,
            text="Direct live queries to WhatsApp & Telegram" if self.var_live_mode.get() else "Offline demo mode (no network calls)",
            font=ctk.CTkFont(size=10),
            text_color="#2ea043" if self.var_live_mode.get() else "#8b949e",
            wraplength=270
        )
        self.lbl_mode_desc.pack(anchor="w", padx=10, pady=(0, 8))

        # Country code fallback
        self.lbl_country = ctk.CTkLabel(
            self.left_panel,
            text="Default Country (Fallback)",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_country.pack(anchor="w", padx=12, pady=(8, 2))

        self.cbo_country = ctk.CTkComboBox(
            self.left_panel,
            values=["US (+1)", "TN (+216)", "FR (+33)", "GB (+44)", "DE (+49)", "ES (+34)", "IN (+91)", "BR (+55)", "AE (+971)"]
        )
        self.cbo_country.set("US (+1)")
        self.cbo_country.pack(fill="x", padx=12, pady=2)

        # Concurrency slider
        self.lbl_concurrency = ctk.CTkLabel(
            self.left_panel,
            text="Parallel Workers: 5",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_concurrency.pack(anchor="w", padx=12, pady=(8, 2))

        self.slider_concurrency = ctk.CTkSlider(
            self.left_panel,
            from_=1,
            to=10,
            number_of_steps=9,
            command=self._on_slider_change
        )
        self.slider_concurrency.set(5)
        self.slider_concurrency.pack(fill="x", padx=12, pady=2)

        # Action Buttons
        self.btn_start = ctk.CTkButton(
            self.left_panel,
            text="▶ Start Validation",
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f6feb",
            hover_color="#388bfd",
            command=self._start_validation
        )
        self.btn_start.pack(fill="x", padx=12, pady=(15, 6))

        self.btn_stop = ctk.CTkButton(
            self.left_panel,
            text="⏹ Stop",
            height=30,
            fg_color="#da3633",
            hover_color="#f85149",
            state="disabled",
            command=self._stop_validation
        )
        self.btn_stop.pack(fill="x", padx=12, pady=(0, 12))

    def _build_right_panel(self):
        """Construct real-time metric cards, progress bar, and results table."""
        # Top KPI Metric Cards
        self.cards_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.cards_frame.pack(fill="x", padx=15, pady=(15, 10))

        self.card_total = self._create_kpi_card(self.cards_frame, "Total Leads", "0", "#c9d1d9")
        self.card_wa = self._create_kpi_card(self.cards_frame, "WhatsApp Active", "0", "#2ea043")
        self.card_tg = self._create_kpi_card(self.cards_frame, "Telegram Active", "0", "#58a6ff")
        self.card_score = self._create_kpi_card(self.cards_frame, "Avg Lead Score", "--", "#d29922")

        # Progress bar
        self.progress_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=5)

        self.lbl_progress = ctk.CTkLabel(
            self.progress_frame,
            text="Ready to validate leads.",
            font=ctk.CTkFont(size=12),
            text_color="#8b949e"
        )
        self.lbl_progress.pack(anchor="w", pady=(0, 4))

        self.progressbar = ctk.CTkProgressBar(self.progress_frame)
        self.progressbar.pack(fill="x")
        self.progressbar.set(0)

        # Table frame (Treeview with custom dark style)
        self.table_frame = ctk.CTkFrame(self.right_panel, fg_color="#0d1117", corner_radius=8)
        self.table_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # Configure style for Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#0d1117",
            foreground="#c9d1d9",
            fieldbackground="#0d1117",
            rowheight=28,
            font=("Segoe UI", 10),
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background="#161b22",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0
        )
        style.map("Treeview", background=[("selected", "#1f6feb")])

        columns = ("phone", "carrier", "whatsapp", "telegram", "score", "channel", "timezone", "business_hours")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("phone", text="Phone (E.164)")
        self.tree.heading("carrier", text="Carrier / Type")
        self.tree.heading("whatsapp", text="WhatsApp")
        self.tree.heading("telegram", text="Telegram")
        self.tree.heading("score", text="Score")
        self.tree.heading("channel", text="Best Channel")
        self.tree.heading("timezone", text="Timezone")
        self.tree.heading("business_hours", text="Safe to Contact?")

        self.tree.column("phone", width=130, anchor="w")
        self.tree.column("carrier", width=110, anchor="w")
        self.tree.column("whatsapp", width=95, anchor="center")
        self.tree.column("telegram", width=95, anchor="center")
        self.tree.column("score", width=65, anchor="center")
        self.tree.column("channel", width=105, anchor="center")
        self.tree.column("timezone", width=130, anchor="w")
        self.tree.column("business_hours", width=110, anchor="center")

        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Legend / Explanation below table
        self.lbl_legend = ctk.CTkLabel(
            self.right_panel,
            text="ℹ️ Safe to Contact: Evaluates lead local timezone (Mon–Fri, 9:00 AM – 6:00 PM). Weekends & off-hours are flagged '🌙 No' for compliance.",
            font=ctk.CTkFont(size=11),
            text_color="#8b949e"
        )
        self.lbl_legend.pack(anchor="w", padx=18, pady=(2, 2))

        # Bottom Action Bar
        self.bottom_bar = ctk.CTkFrame(self.right_panel, height=45, fg_color="transparent")
        self.bottom_bar.pack(fill="x", padx=15, pady=(4, 10))

        self.btn_export = ctk.CTkButton(
            self.bottom_bar,
            text="💾 Export Enriched CSV",
            fg_color="#238636",
            hover_color="#2ea043",
            command=self._export_csv,
            state="disabled"
        )
        self.btn_export.pack(side="left")

        self.btn_clear = ctk.CTkButton(
            self.bottom_bar,
            text="Clear",
            width=80,
            fg_color="#21262d",
            hover_color="#30363d",
            command=self._clear_results
        )
        self.btn_clear.pack(side="right")

    def _create_kpi_card(self, parent, title: str, initial_value: str, color: str):
        """Build a reusable KPI metric card."""
        card = ctk.CTkFrame(parent, fg_color="#0d1117", corner_radius=8, height=65)
        card.pack(side="left", fill="x", expand=True, padx=4)

        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11), text_color="#8b949e")
        lbl_title.pack(anchor="w", padx=10, pady=(6, 0))

        lbl_val = ctk.CTkLabel(card, text=initial_value, font=ctk.CTkFont(size=18, weight="bold"), text_color=color)
        lbl_val.pack(anchor="w", padx=10, pady=(0, 6))

        return lbl_val

    def _on_slider_change(self, val):
        self.lbl_concurrency.configure(text=f"Parallel Workers: {int(val)}")

    def _on_mode_toggled(self):
        """Handle toggle between Live Mode and Offline Simulation Mode."""
        is_live = self.var_live_mode.get()
        self.settings["simulation_mode"] = not is_live
        if is_live:
            self.lbl_mode_desc.configure(
                text="Direct live queries to WhatsApp & Telegram",
                text_color="#2ea043"
            )
        else:
            self.lbl_mode_desc.configure(
                text="Offline demo mode (no network calls)",
                text_color="#8b949e"
            )

    def _link_whatsapp(self):
        """Launch interactive visible Chrome/Edge to scan WhatsApp Web QR code."""
        if self.is_running:
            messagebox.showwarning("Busy", "Cannot link WhatsApp while validation is actively running.")
            return

        if self.is_linking_wa:
            return

        self.is_linking_wa = True
        self.btn_link_wa.configure(state="disabled", text="⏳ Opening Browser...")
        self.lbl_wa_status.configure(text="🟡 Launching browser...", text_color="#d29922")

        def worker():
            def cb(msg: str):
                self.after(0, lambda m=msg: self.lbl_wa_status.configure(text=f"🟡 {m[:30]}..."))

            try:
                success = asyncio.run(authenticate_whatsapp_interactive(status_callback=cb))
            except Exception as e:
                success = False
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Connection Error", f"WhatsApp Linking Error:\n{err_msg}"))

            self.after(0, self._on_whatsapp_link_finished, success)

        threading.Thread(target=worker, daemon=True).start()

    def _on_whatsapp_link_finished(self, success: bool):
        """Handle completion of WhatsApp Web QR code linking."""
        self.is_linking_wa = False
        self.btn_link_wa.configure(state="normal", text="🔗 Link WhatsApp (Scan QR)")

        if is_whatsapp_linked():
            self.lbl_wa_status.configure(text="🟢 Linked & Ready", text_color="#2ea043")
            self.btn_unlink_wa.pack(side="right")
            self.var_live_mode.set(True)
            self.settings["simulation_mode"] = False
            self._on_mode_toggled()
            messagebox.showinfo(
                "WhatsApp Linked!",
                "🎉 WhatsApp Web authenticated successfully!\n\n"
                "Your account is linked and ready. The app will now perform real-time, live WhatsApp checks with 100% accuracy."
            )
        else:
            self.lbl_wa_status.configure(text="⚪ Not Linked", text_color="#8b949e")

    def _unlink_whatsapp(self):
        """Clear saved WhatsApp session files."""
        if messagebox.askyesno("Unlink WhatsApp", "Are you sure you want to unlink and log out of WhatsApp Web?"):
            unlink_whatsapp_session()
            self.lbl_wa_status.configure(text="⚪ Not Linked", text_color="#8b949e")
            self.btn_unlink_wa.pack_forget()
            messagebox.showinfo("Unlinked", "WhatsApp Web session has been removed.")

    def _browse_file(self):
        """Open file dialog to pick CSV."""
        filepath = filedialog.askopenfilename(
            title="Select Lead CSV File",
            filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            self.selected_file_path = filepath
            filename = os.path.basename(filepath)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    records = parse_csv_records(f.read())
                self.loaded_records = records
                self.lbl_file_name.configure(
                    text=f"Loaded: {filename}\n({len(records)} leads detected)",
                    text_color="#58a6ff"
                )
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to parse CSV: {e}")

    def _start_validation(self):
        """Prepare inputs and launch async background worker."""
        # Gather inputs based on active tab
        current_tab = self.tabview.get()
        if current_tab == "📁 Upload CSV":
            if not self.loaded_records:
                messagebox.showwarning("Input Required", "Please browse and select a CSV file first.")
                return
            entries = self.loaded_records
        else:
            raw_text = self.txt_manual.get("1.0", "end").strip()
            if not raw_text:
                messagebox.showwarning("Input Required", "Please paste phone numbers to validate.")
                return
            entries = normalize_input_records([], raw_text)

        platforms = []
        if self.var_wa.get():
            platforms.append("whatsapp")
        if self.var_tg.get():
            platforms.append("telegram")

        if not platforms:
            messagebox.showwarning("Platform Required", "Please select at least one platform (WhatsApp or Telegram).")
            return

        # Check Live Mode vs WhatsApp connection
        is_live = self.var_live_mode.get()
        self.settings["simulation_mode"] = not is_live

        if is_live and "whatsapp" in platforms and not is_whatsapp_linked() and not self.settings["whatsapp_token"]:
            res = messagebox.askyesno(
                "WhatsApp QR Scan Required",
                "You are running in Live Mode, but WhatsApp Web is not linked yet!\n\n"
                "To verify real phone numbers on WhatsApp for free, you must link your account:\n\n"
                "• Click 'Yes' to launch the QR scanner now.\n"
                "• Click 'No' to switch to Offline Demo Mode."
            )
            if res:
                self._link_whatsapp()
            else:
                self.var_live_mode.set(False)
                self.settings["simulation_mode"] = True
                self._on_mode_toggled()
            return

        # UI state
        self.is_running = True
        self.should_stop = False
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_export.configure(state="disabled")
        self._clear_results()

        default_country = self.cbo_country.get()[:2]
        concurrency = int(self.slider_concurrency.get())

        # Start thread
        thread = threading.Thread(
            target=self._run_validation_thread,
            args=(entries, platforms, default_country, concurrency),
            daemon=True
        )
        thread.start()

    def _run_validation_thread(self, entries: List[InputPhoneRecord], platforms: List[str], default_country: str, concurrency: int):
        """Background thread executing async validation loop."""
        asyncio.run(self._async_worker(entries, platforms, default_country, concurrency))

    async def _async_worker(self, entries: List[InputPhoneRecord], platforms: List[str], default_country: str, concurrency: int):
        phone_validator = PhoneValidator(default_region=default_country)
        wa_validator = WhatsAppValidator(
            api_token=self.settings["whatsapp_token"],
            phone_number_id=self.settings["whatsapp_phone_id"],
            simulation_mode=self.settings["simulation_mode"]
        ) if "whatsapp" in platforms else None

        tg_validator = TelegramValidator(
            api_id=int(self.settings["telegram_api_id"]) if self.settings["telegram_api_id"] else None,
            api_hash=self.settings["telegram_api_hash"],
            session_string=self.settings["telegram_session"],
            simulation_mode=self.settings["simulation_mode"]
        ) if "telegram" in platforms else None

        semaphore = asyncio.Semaphore(concurrency)
        total = len(entries)
        completed = 0
        wa_active_count = 0
        tg_active_count = 0
        total_score = 0

        async def process_item(entry: InputPhoneRecord):
            nonlocal completed, wa_active_count, tg_active_count, total_score

            if self.should_stop:
                return

            sanitized = phone_validator.sanitize_and_validate(entry.raw_number)
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            if not sanitized.valid_format or not sanitized.e164:
                score, channel, risk = compute_lead_quality(False, "Invalid", None, None)
                record = ValidationRecord(
                    input=entry.raw_number,
                    validFormat=False,
                    timezone=sanitized.timezone,
                    leadQualityScore=score,
                    recommendedChannel=channel,
                    riskLevel=risk,
                    customFields=entry.custom_fields,
                    verifiedAt=now_iso,
                    error=sanitized.error or "Invalid format"
                )
            else:
                wa_res = None
                tg_res = None
                async with semaphore:
                    tasks = []
                    if wa_validator:
                        tasks.append(("wa", wa_validator.verify_number(sanitized.e164)))
                    if tg_validator:
                        tasks.append(("tg", tg_validator.verify_number(sanitized.e164)))
                    if tasks:
                        task_keys = [t[0] for t in tasks]
                        outcomes = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
                        for k, o in zip(task_keys, outcomes):
                            if not isinstance(o, Exception):
                                if k == "wa":
                                    wa_res = o
                                elif k == "tg":
                                    tg_res = o

                score, channel, risk = compute_lead_quality(
                    valid_format=True,
                    number_type=sanitized.number_type,
                    wa_result=wa_res,
                    tg_result=tg_res
                )

                record = ValidationRecord(
                    input=entry.raw_number,
                    e164=sanitized.e164,
                    country=sanitized.country,
                    validFormat=True,
                    carrier=sanitized.carrier,
                    whatsapp=wa_res,
                    telegram=tg_res,
                    timezone=sanitized.timezone,
                    localTime=sanitized.local_time,
                    isBusinessHours=sanitized.is_business_hours,
                    leadQualityScore=score,
                    recommendedChannel=channel,
                    riskLevel=risk,
                    customFields=entry.custom_fields,
                    verifiedAt=now_iso
                )

                if wa_res and wa_res.isRegistered:
                    wa_active_count += 1
                if tg_res and tg_res.isRegistered:
                    tg_active_count += 1
                total_score += score

            completed += 1
            self.validation_results.append(record)

            # Update UI safely
            self.after(0, self._update_progress, completed, total, wa_active_count, tg_active_count, total_score, record)

        # Batch execution
        tasks = [process_item(e) for e in entries]
        await asyncio.gather(*tasks)

        if wa_validator:
            await wa_validator.close()
        if tg_validator:
            await tg_validator.close()

        self.after(0, self._on_validation_finish)

    def _update_progress(self, completed, total, wa_active, tg_active, total_score, latest_record: ValidationRecord):
        """Update live UI metrics and table."""
        pct = completed / max(1, total)
        self.progressbar.set(pct)
        mode_str = "Simulation" if self.settings["simulation_mode"] else "Live"
        self.lbl_progress.configure(text=f"Validating leads ({mode_str}): {completed} / {total} ({int(pct * 100)}%)")

        self.card_total.configure(text=str(completed))
        self.card_wa.configure(text=str(wa_active))
        self.card_tg.configure(text=str(tg_active))
        avg = int(total_score / max(1, completed))
        self.card_score.configure(text=f"{avg} / 100")

        # Format row values
        phone_display = latest_record.e164 or latest_record.input
        carrier_display = latest_record.carrier or "Invalid"

        wa_text = "❌ Not on WA"
        if latest_record.whatsapp:
            if latest_record.whatsapp.isRegistered:
                wa_text = "✅ Business" if latest_record.whatsapp.accountType == "business" else "✅ Active"
            elif latest_record.whatsapp.error:
                err = latest_record.whatsapp.error.lower()
                if "not linked" in err:
                    wa_text = "⚠️ Scan QR"
                elif "simulated" in err:
                    wa_text = "🧪 Demo No"
                elif "not registered" in err or "unregistered" in err:
                    wa_text = "❌ Not on WA"
                else:
                    wa_text = "❌ Inactive"
            else:
                wa_text = "❌ Not on WA"

        tg_text = "❌ Not on TG"
        if latest_record.telegram:
            if latest_record.telegram.isRegistered:
                tg_text = "⭐ Premium" if latest_record.telegram.isPremium else "✅ Active"
            elif latest_record.telegram.error:
                err = latest_record.telegram.error.lower()
                if "not configured" in err:
                    tg_text = "⚠️ Needs Key"
                elif "simulated" in err:
                    tg_text = "🧪 Demo No"
                else:
                    tg_text = "❌ Not on TG"
            else:
                tg_text = "❌ Not on TG"

        # Explicit business hours description
        if latest_record.isBusinessHours:
            biz_hours_text = "☀️ Yes (Open)"
        else:
            now_utc = datetime.now(timezone.utc)
            if now_utc.weekday() in (5, 6):
                biz_hours_text = "🌙 Weekend (Closed)"
            elif latest_record.localTime:
                biz_hours_text = f"🌙 Night ({latest_record.localTime})"
            else:
                biz_hours_text = "🌙 Off-Hours"

        self.tree.insert(
            "",
            "end",
            values=(
                phone_display,
                carrier_display,
                wa_text,
                tg_text,
                f"{latest_record.leadQualityScore}",
                latest_record.recommendedChannel,
                latest_record.timezone or "--",
                biz_hours_text
            )
        )
        # Scroll to bottom
        self.tree.yview_moveto(1.0)

    def _on_validation_finish(self):
        """Reset buttons after completion."""
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_export.configure(state="normal")
        self.lbl_progress.configure(text=f"Completed! {len(self.validation_results)} leads verified successfully.")
        messagebox.showinfo("Validation Finished", f"Processed {len(self.validation_results)} leads successfully!\nClick 'Export Enriched CSV' to save results.")

    def _stop_validation(self):
        """Trigger worker cancellation."""
        self.should_stop = True
        self.lbl_progress.configure(text="Stopping validation...")

    def _clear_results(self):
        """Reset tables and cards."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.validation_results.clear()
        self.card_total.configure(text="0")
        self.card_wa.configure(text="0")
        self.card_tg.configure(text="0")
        self.card_score.configure(text="--")
        self.progressbar.set(0)
        self.lbl_progress.configure(text="Ready to validate leads.")

    def _export_csv(self):
        """Save results to CSV preserving all original input columns."""
        if not self.validation_results:
            return

        save_path = filedialog.asksaveasfilename(
            title="Export Enriched Lead CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not save_path:
            return

        try:
            # Flatten records into dicts
            data_dicts = [r.to_dataset_dict() for r in self.validation_results]
            if not data_dicts:
                return

            # Collect all unique fieldnames
            all_keys = []
            for d in data_dicts:
                for k in d.keys():
                    if k not in all_keys:
                        all_keys.append(k)

            with open(save_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=all_keys)
                writer.writeheader()
                for row in data_dicts:
                    # Flatten any dicts like whatsapp / telegram into readable strings for CSV
                    clean_row = {}
                    for k, v in row.items():
                        if isinstance(v, dict):
                            clean_row[k] = str(v)
                        else:
                            clean_row[k] = v
                    writer.writerow(clean_row)

            messagebox.showinfo("Export Successful", f"Saved {len(data_dicts)} enriched leads to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save CSV file: {e}")

    def _open_settings(self):
        """Open settings dialog to configure API keys or simulation mode."""
        win = ctk.CTkToplevel(self)
        win.title("API & Platform Settings")
        win.geometry("520x420")
        win.grab_set()

        lbl_sim = ctk.CTkLabel(win, text="Free / Simulation Mode", font=ctk.CTkFont(weight="bold"))
        lbl_sim.pack(anchor="w", padx=25, pady=(20, 5))

        var_sim = ctk.BooleanVar(value=self.settings["simulation_mode"])
        chk_sim = ctk.CTkSwitch(
            win,
            text="Enable 100% Free / Dry-Run Mode (No API keys needed)",
            variable=var_sim
        )
        chk_sim.pack(anchor="w", padx=25, pady=5)

        lbl_wa = ctk.CTkLabel(win, text="WhatsApp Cloud API (Optional)", font=ctk.CTkFont(weight="bold"))
        lbl_wa.pack(anchor="w", padx=25, pady=(15, 5))

        txt_wa_token = ctk.CTkEntry(win, placeholder_text="WhatsApp Access Token (Optional)")
        txt_wa_token.pack(fill="x", padx=25, pady=3)
        txt_wa_token.insert(0, self.settings["whatsapp_token"])

        txt_wa_id = ctk.CTkEntry(win, placeholder_text="WhatsApp Phone Number ID (Optional)")
        txt_wa_id.pack(fill="x", padx=25, pady=3)
        txt_wa_id.insert(0, self.settings["whatsapp_phone_id"])

        lbl_tg = ctk.CTkLabel(win, text="Telegram MTProto API (my.telegram.org)", font=ctk.CTkFont(weight="bold"))
        lbl_tg.pack(anchor="w", padx=25, pady=(15, 5))

        txt_tg_id = ctk.CTkEntry(win, placeholder_text="Telegram API ID (Optional)")
        txt_tg_id.pack(fill="x", padx=25, pady=3)
        txt_tg_id.insert(0, self.settings["telegram_api_id"])

        txt_tg_hash = ctk.CTkEntry(win, placeholder_text="Telegram API Hash (Optional)", show="*")
        txt_tg_hash.pack(fill="x", padx=25, pady=3)
        txt_tg_hash.insert(0, self.settings["telegram_api_hash"])

        def save_and_close():
            self.settings["simulation_mode"] = var_sim.get()
            self.var_live_mode.set(not var_sim.get())
            self._on_mode_toggled()
            self.settings["whatsapp_token"] = txt_wa_token.get().strip()
            self.settings["whatsapp_phone_id"] = txt_wa_id.get().strip()
            self.settings["telegram_api_id"] = txt_tg_id.get().strip()
            self.settings["telegram_api_hash"] = txt_tg_hash.get().strip()
            win.destroy()

        btn_save = ctk.CTkButton(win, text="Save Settings", command=save_and_close, fg_color="#238636")
        btn_save.pack(pady=20)


if __name__ == "__main__":
    app = NumberCheckerApp()
    app.mainloop()
