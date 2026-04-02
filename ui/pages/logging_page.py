import tkinter as tk
import customtkinter as ctk
from utils.font_loader import F
from utils.localization import L

class LoggingPage(ctk.CTkFrame):
    def __init__(self, parent, manager):
        super().__init__(parent, fg_color="transparent")
        self.manager = manager
        self.setup_ui()

    def setup_ui(self):
        container = ctk.CTkFrame(self, fg_color="#161e29", corner_radius=16, border_width=1, border_color="#1e2c3a")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header row
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill=tk.X, padx=24, pady=(24, 16))

        ctk.CTkLabel(header, text=L("logging.title"),
                     font=F(20, True), text_color="#3b8ed0").pack(side=tk.LEFT)

        clear_btn = ctk.CTkButton(
            header, text=L("logging.clear_history"), width=110, height=32,
            corner_radius=8, fg_color="#1e2c3a", hover_color="#3a1515",
            font=F(11, True), text_color="#8b9bb4",
            command=self._clear_log
        )
        clear_btn.pack(side=tk.RIGHT)

        # Log textbox - Refined padding and font
        self.manager.log_textbox = ctk.CTkTextbox(
            container, font=("Consolas", 12),
            fg_color="#0d1117", text_color="#7ba7cf",
            border_color="#1e2c3a", border_width=1,
            corner_radius=12,
            padx=15, pady=15
        )
        self.manager.log_textbox.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 24))

        # Restore history
        self.manager.log_textbox.configure(state="normal")
        for entry in self.manager.log_history:
            self.manager.log_textbox.insert(tk.END, entry)
        self.manager.log_textbox.see(tk.END)
        self.manager.log_textbox.configure(state="disabled")
        self.manager.log_event(L("logging.log_opened"))

    def _clear_log(self):
        if hasattr(self.manager, 'log_textbox') and self.manager.log_textbox.winfo_exists():
            self.manager.log_history.clear()
            self.manager.log_textbox.configure(state="normal")
            self.manager.log_textbox.delete("1.0", tk.END)
            self.manager.log_textbox.configure(state="disabled")
