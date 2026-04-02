import tkinter as tk
import customtkinter as ctk
from utils.helpers import get_resource_path
from utils.font_loader import F
from utils.localization import L

class BrowserPage(ctk.CTkFrame):
    def __init__(self, parent, manager):
        super().__init__(parent, fg_color="transparent")
        self.manager = manager
        self.setup_ui()

    def setup_ui(self):
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # ── Header ────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill=tk.X, pady=(10, 30))

        ctk.CTkLabel(header, text=L("browser.title"),
                     font=F(26, True), text_color="#e8edf2").pack(side=tk.LEFT)

        # Server status badge - Refined & More Compact
        badge = ctk.CTkFrame(header, fg_color="#161e29", corner_radius=12, height=32, border_width=1, border_color="#1e2c3a")
        badge.pack(side=tk.RIGHT)
        badge.pack_propagate(False)

        self.manager.status_dot = ctk.CTkLabel(
            badge, text="●", font=("Consolas", 14), text_color="#4caf50")
        self.manager.status_dot.pack(side=tk.LEFT, padx=(12, 6))

        self.manager.status_text = ctk.CTkLabel(
            badge, text=L("browser.server_active"), font=F(12, True), text_color="#8b9bb4")
        self.manager.status_text.pack(side=tk.LEFT, padx=(0, 12))

        # ── Body (2 columns) ─────────────────────────────────────────────────
        body = ctk.CTkFrame(main, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_columnconfigure((0, 1), weight=1)

        # Left: Guide steps
        left = ctk.CTkFrame(body, fg_color="#161e29", corner_radius=16,
                            border_width=1, border_color="#1e2c3a")
        left.grid(row=0, column=0, padx=(0, 12), sticky="nsew")

        ctk.CTkLabel(left, text=L("browser.setup_guide"), font=F(18, True),
                     text_color="#3b8ed0").pack(pady=(24, 16), padx=24, anchor="w")

        # Dynamically load steps from localization
        steps = L("browser.steps", default=[])
        if isinstance(steps, list):
            for i, step in enumerate(steps):
                title = step.get("title", "")
                desc = step.get("desc", "")
                
                row = ctk.CTkFrame(left, fg_color="transparent")
                row.pack(fill=tk.X, padx=20, pady=10)
                ctk.CTkLabel(row, text=title, font=F(13, True),
                             text_color="#3b8ed0", anchor="w").pack(fill=tk.X)
                ctk.CTkLabel(row, text=desc, font=F(12), text_color="#6b7a8d",
                             anchor="w", wraplength=340, justify="left").pack(fill=tk.X)
                if i < len(steps) - 1:
                    ctk.CTkFrame(left, height=1, fg_color="#1e2c3a").pack(fill=tk.X, padx=28, pady=5)

        # Right: Installation card
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        ctk.CTkLabel(right, text=L("browser.install_now"), font=F(17, True)).pack(pady=(4, 10), anchor="w")

        self.manager.drag_card = ctk.CTkFrame(
            right, height=220, fg_color="#161e29",
            border_width=2, border_color="#3b8ed0", corner_radius=16)
        self.manager.drag_card.pack(fill=tk.X, pady=4)
        self.manager.drag_card.pack_propagate(False)

        inner = ctk.CTkFrame(self.manager.drag_card, fg_color="transparent")
        inner.pack(expand=True)

        icon = ctk.CTkLabel(inner, text="📥", font=("Segoe UI Emoji", 56))
        icon.pack(pady=(0, 8))
        ctk.CTkLabel(inner, text=L("browser.drag_drop"),
                     font=F(17, True), text_color="#3b8ed0").pack()
        ctk.CTkLabel(inner, text=L("browser.drag_desc"),
                     font=F(12), text_color="#6b7a8d").pack()

        # Manual copy path row
        copy_row = ctk.CTkFrame(right, fg_color="#161e29", corner_radius=10)
        copy_row.pack(fill=tk.X, pady=18)

        ctk.CTkLabel(copy_row, text=L("browser.load_unpacked"),
                     font=F(12, True), text_color="#555f6e").pack(side=tk.LEFT, padx=14, pady=14)

        def copy_path():
            ext_path = get_resource_path("extension")
            self.manager.root.clipboard_clear()
            self.manager.root.clipboard_append(ext_path)
            copy_btn.configure(text=L("browser.copied"), fg_color="#4caf50")
            self.manager.root.after(2000, lambda: copy_btn.configure(text=L("browser.copy_path"), fg_color="#1a2a3a"))
            self.manager.log_event(f"Extension path copied: {ext_path}")

        copy_btn = ctk.CTkButton(copy_row, text=L("browser.copy_path"), width=100, height=30,
                                 fg_color="#1a2a3a", hover_color="#223344",
                                 font=F(12), command=copy_path)
        copy_btn.pack(side=tk.RIGHT, padx=14)

        # ── Drag logic ────────────────────────────────────────────────────────
        self.manager.drag_start_pos = None

        def on_press(e):
            self.manager.drag_start_pos = (e.x_root, e.y_root)
            self.manager.drag_card.configure(border_color="#4caf50")

        def on_move(e):
            if self.manager.drag_start_pos:
                dx = abs(e.x_root - self.manager.drag_start_pos[0])
                dy = abs(e.y_root - self.manager.drag_start_pos[1])
                if dx > 5 or dy > 5:
                    self.manager.start_shell_drag()
                    self.manager.drag_start_pos = None

        def on_enter(e):
            self.manager.drag_card.configure(border_color="#00bfff", fg_color="#1a2a3a")
            self.manager.root.configure(cursor="fleur")

        def on_leave(e):
            self.manager.drag_card.configure(border_color="#3b8ed0", fg_color="#161e29")
            self.manager.root.configure(cursor="")

        for w in [self.manager.drag_card, inner, icon]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_press)
            w.bind("<B1-Motion>", on_move)
            w.bind("<ButtonRelease-1>",
                   lambda e: self.manager.drag_card.configure(border_color="#3b8ed0"))
