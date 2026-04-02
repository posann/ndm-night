import tkinter as tk
import customtkinter as ctk
from utils.font_loader import F
from utils.helpers import get_resource_path
from utils.localization import L
from PIL import Image

class AboutPage(ctk.CTkFrame):
    def __init__(self, parent, manager):
        super().__init__(parent, fg_color="#111920") # Match main content color
        self.manager = manager
        self.setup_ui()

    def setup_ui(self):
        # Center Container
        container = ctk.CTkFrame(self, fg_color="#161e29", corner_radius=16, border_width=1, border_color="#1e2c3a")
        container.place(relx=0.5, rely=0.45, anchor="center", relwidth=0.7, relheight=0.7)
        
        # Elegant Header
        ctk.CTkLabel(container, text=L("about.header"), font=("Segoe UI Emoji", 56)).pack(pady=(50, 15))
        ctk.CTkLabel(container, text=L("app.title"), font=F(28, True), text_color="#e8edf2").pack()
        ctk.CTkLabel(container, text=L("app.version"), font=F(14), text_color="#555f6e").pack()
        
        # Divider
        ctk.CTkFrame(container, height=1, width=400, fg_color="#1e2c3a").pack(pady=40)
        
        # Description
        desc_text = L("about.description")
        ctk.CTkLabel(container, text=desc_text, font=F(15), text_color="#8b9bb4", justify="center").pack()
        
        # Footer / Developer Credit
        footer = ctk.CTkFrame(container, fg_color="transparent")
        footer.pack(side=tk.BOTTOM, pady=40)
        
        ctk.CTkLabel(footer, text=L("about.crafted_by"), font=F(13), text_color="#555f6e").pack(side=tk.LEFT, padx=6)
        ctk.CTkLabel(footer, text="posann", font=F(15, True), text_color="#3b8ed0").pack(side=tk.LEFT)
