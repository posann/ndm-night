import tkinter as tk
import customtkinter as ctk
import os
import threading
import socket
from utils.font_loader import F
from utils.localization import L

# File-type category pills shown in the filter bar
CATEGORIES = ["All", "Compressed", "Video", "Audio", "Image", "Document", "Program"]


class DownloadsPage(ctk.CTkFrame):
    def __init__(self, parent, manager):
        super().__init__(parent, fg_color="transparent")
        self.manager = manager
        self._cat_buttons = {}      # category pill buttons
        self._active_category = "All"
        self.network_status = True  # Default to connected
        self.setup_ui()
        self.start_network_polling()

    # ──────────────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────────────
    def setup_ui(self):
        self.manager.select_all_var = tk.BooleanVar(value=False)

        # ── URL Input Bar ─────────────────────────────────────────────────────
        url_bar = ctk.CTkFrame(self, fg_color="#161e29", corner_radius=12)
        url_bar.pack(fill=tk.X, pady=(16, 12), padx=16)

        ctk.CTkLabel(url_bar, text=L("downloads.url_label"), font=F(13, True),
                     text_color="#4a6080").pack(side=tk.LEFT, padx=(16, 10), pady=12)

        self.manager.mode_var = tk.StringVar(value="Manual")
        ctk.CTkOptionMenu(
            url_bar, values=["Manual", "GDrive"],
            variable=self.manager.mode_var, width=105,
            fg_color="#0d1117", button_color="#1e2c3a",
            button_hover_color="#263545", font=F(12)
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.manager.url_entry = ctk.CTkEntry(
            url_bar, font=F(13, False),
            placeholder_text=L("downloads.url_placeholder"),
            fg_color="#0d1117", border_color="#1e2c3a", border_width=1
        )
        self.manager.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

        ctk.CTkButton(
            url_bar, text=L("downloads.paste"), command=self.manager.paste_url,
            width=80, corner_radius=8, height=36, font=F(12),
            fg_color="#1a2a3a", hover_color="#223344", text_color="#7ba7cf"
        ).pack(side=tk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            url_bar, text=L("downloads.add_download"), command=self.manager.add_download,
            width=130, corner_radius=8, height=36, font=F(13, True),
            fg_color="#1f538d", hover_color="#1a4070", text_color="white"
        ).pack(side=tk.LEFT, padx=(0, 12))

        # ── Filter Bar (search + category pills) ─────────────────────────────
        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.pack(fill=tk.X, padx=16, pady=(0, 8))

        # Network Status Icon (left of search)
        self.net_label = ctk.CTkLabel(
            filter_bar, text="●", 
            font=F(12, True), text_color="#4caf50", width=20)
        self.net_label.pack(side=tk.LEFT, padx=(0, 10))

        # Search entry (left side)
        self.manager.search_var = tk.StringVar(value="")
        search_entry = ctk.CTkEntry(
            filter_bar, textvariable=self.manager.search_var,
            placeholder_text=L("downloads.search_placeholder"),
            width=260, height=36, corner_radius=8, font=F(12, False),
            fg_color="#161e29", border_color="#1e2c3a", border_width=1
        )
        search_entry.pack(side=tk.LEFT)
        search_entry.bind("<KeyRelease>", lambda e: self.manager.filter_downloads())
        self.manager.search_entry = search_entry
        
        # Force placeholder refresh if empty
        if not self.manager.search_var.get():
            search_entry.insert(0, "") # Tricks CTk into showing placeholder

        # Category pills (right side)
        pills_frame = ctk.CTkFrame(filter_bar, fg_color="transparent")
        pills_frame.pack(side=tk.RIGHT)

        for cat in CATEGORIES:
            btn = ctk.CTkButton(
                pills_frame, text=L(f"downloads.category.{cat}"),
                width=100, height=32, corner_radius=16, font=F(12),
                fg_color="#1a2a3a" if cat != "All" else "#1f538d",
                hover_color="#263545",
                text_color="#ffffff" if cat == "All" else "#8b9bb4",
                command=lambda c=cat: self._on_category(c)
            )
            btn.pack(side=tk.LEFT, padx=3)
            self._cat_buttons[cat] = btn

        # ── Download List ─────────────────────────────────────────────────────
        self.manager.downloads_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color="#1e2c3a",
            scrollbar_button_hover_color="#263545"
        )
        self.manager.downloads_frame.pack(fill=tk.BOTH, expand=True, padx=16)

        # ── Stats / Bulk Actions ──────────────────────────────────────────────
        stats_bar = ctk.CTkFrame(self, fg_color="#161e29", corner_radius=10)
        stats_bar.pack(fill=tk.X, padx=16, pady=(8, 14))

        self.manager.select_all_checkbox = ctk.CTkCheckBox(
            stats_bar, text=L("downloads.controls.select_all"),
            variable=self.manager.select_all_var,
            command=self.manager.toggle_select_all,
            font=F(12), text_color="#7ba7cf",
            checkmark_color="white", fg_color="#1f538d", hover_color="#1a4070"
        )
        self.manager.select_all_checkbox.pack(side=tk.LEFT, padx=14, pady=10)

        self.manager.stats_label = ctk.CTkLabel(
            stats_bar, text=L("downloads.stats.ready"), font=F(12), text_color="#4a6080")
        self.manager.stats_label.pack(side=tk.LEFT, padx=6)

        bulk = {
            "width": 44, "height": 34, "corner_radius": 8,
            "text_color": "white", "text_color_disabled": "#2a3a4a",
            "font": ("Segoe UI Emoji", 15)
        }
        self.manager.bulk_btns = {}

        self.manager.bulk_btns['clear_success'] = ctk.CTkButton(
            stats_bar, text="✨", command=self.manager.clear_completed,
            fg_color="#263545", hover_color="#2e4055", **bulk)
        self.manager.bulk_btns['clear_success'].pack(side=tk.RIGHT, padx=(4, 12))

        self.manager.bulk_btns['resume'] = ctk.CTkButton(
            stats_bar, text="▶", command=self.manager.resume_selected,
            fg_color="#1a3d2a", hover_color="#22503a", **bulk)
        self.manager.bulk_btns['resume'].pack(side=tk.RIGHT, padx=4)

        self.manager.bulk_btns['pause'] = ctk.CTkButton(
            stats_bar, text="⏸", command=self.manager.pause_selected,
            fg_color="#3a2d10", hover_color="#4a3a18", **bulk)
        self.manager.bulk_btns['pause'].pack(side=tk.RIGHT, padx=4)

        self.manager.bulk_btns['delete'] = ctk.CTkButton(
            stats_bar, text="🗑", command=self.manager.clear_selected,
            fg_color="#3a1515", hover_color="#4a1e1e", **bulk)
        self.manager.bulk_btns['delete'].pack(side=tk.RIGHT, padx=4)

        # Sync state & restore existing downloads
        self.manager.update_bulk_buttons_state()
        for download_info in self.manager.downloads.values():
            self.manager.create_download_ui(download_info)

    # ──────────────────────────────────────────────────────────────────────────
    # Category filter logic
    # ──────────────────────────────────────────────────────────────────────────
    def _on_category(self, category: str):
        """Highlight the selected pill, update manager filter, and refresh list."""
        self._active_category = category
        self.manager.category_filter = category

        for cat, btn in self._cat_buttons.items():
            if cat == category:
                btn.configure(fg_color="#1f538d", text_color="#ffffff")
            else:
                btn.configure(fg_color="#1a2a3a", text_color="#8b9bb4")

        self.manager.filter_downloads()

    # ──────────────────────────────────────────────────────────────────────────
    # Network Monitoring
    # ──────────────────────────────────────────────────────────────────────────
    def start_network_polling(self):
        """Starts a background thread to check network status periodically"""
        def check():
            while True:
                try:
                    # Use a standard HTTP port (80) which is almost never blocked by firewalls
                    socket.setdefaulttimeout(3)
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(("1.1.1.1", 80))
                    s.close()
                    self.network_status = True
                except:
                    self.network_status = False
                
                # Update UI in main thread
                if self.winfo_exists():
                    self.after(0, self.update_network_ui)
                import time
                time.sleep(5)
        
        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def update_network_ui(self):
        """Updates the network label color and text"""
        if not self.winfo_exists(): return
        
        if self.network_status:
            self.net_label.configure(
                text="●", 
                text_color="#4caf50"
            )
        else:
            self.net_label.configure(
                text="●", 
                text_color="#f44336"
            )
