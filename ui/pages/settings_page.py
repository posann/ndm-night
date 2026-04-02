import tkinter as tk
import customtkinter as ctk
from utils.font_loader import F
from utils.localization import L, init_localization, get_current_lang
from utils.database import set_setting, get_setting

class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, manager):
        super().__init__(parent, fg_color="transparent")
        self.manager = manager
        self.setup_ui()

    def setup_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill=tk.X, padx=24, pady=(24, 16))
        
        ctk.CTkLabel(header, text=L("settings.title"), 
                     font=F(22, True), text_color="#3b8ed0").pack(side=tk.LEFT)

        # Main Container
        container = ctk.CTkFrame(self, fg_color="#161e29", corner_radius=16, border_width=1, border_color="#1e2c3a")
        container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 24))
        
        # Section: General Settings
        self.create_section_header(container, L("settings.general"))
        
        # Row: Language
        lang_row = ctk.CTkFrame(container, fg_color="transparent")
        lang_row.pack(fill=tk.X, padx=24, pady=12)
        
        ctk.CTkLabel(lang_row, text=L("settings.language"), font=F(14, True), text_color="#e8edf2").pack(side=tk.LEFT)
        
        # Languages: English, Indonesian
        self.lang_var = tk.StringVar(value="English" if get_current_lang() == "en" else "Bahasa Indonesia")
        lang_menu = ctk.CTkOptionMenu(
            lang_row, 
            values=["English", "Bahasa Indonesia"],
            variable=self.lang_var,
            command=self.change_language,
            fg_color="#1e2c3a", button_color="#1e2c3a", 
            button_hover_color="#263545", font=F(13)
        )
        lang_menu.pack(side=tk.RIGHT)
        
        ctk.CTkLabel(container, text=L("settings.language_desc"), font=F(12), text_color="#555f6e").pack(padx=24, pady=(0, 12), anchor="w")

        # Divider
        ctk.CTkFrame(container, height=1, fg_color="#1e2c3a").pack(fill=tk.X, padx=24, pady=20)

        # Section: Appearance (Coming Soon / Placeholder)
        self.create_section_header(container, L("settings.appearance"))
        
        # Row: Theme
        theme_row = ctk.CTkFrame(container, fg_color="transparent")
        theme_row.pack(fill=tk.X, padx=24, pady=12)
        ctk.CTkLabel(theme_row, text=L("settings.theme"), font=F(14, True), text_color="#e8edf2").pack(side=tk.LEFT)
        
        theme_menu = ctk.CTkOptionMenu(
            theme_row, 
            values=["Dark", "Light"],
            state="disabled", # Future feature
            fg_color="#1e2c3a", button_color="#1e2c3a", 
            font=F(13)
        )
        theme_menu.pack(side=tk.RIGHT)

    def create_section_header(self, parent, title):
        ctk.CTkLabel(parent, text=title, font=F(12, True), text_color="#3b4a5a").pack(padx=24, pady=(20, 8), anchor="w")

    def change_language(self, choice):
        new_lang = "en" if choice == "English" else "id"
        if new_lang != get_current_lang():
            # Save to DB
            set_setting("language", new_lang)
            
            # Re-init localization
            init_localization(new_lang)
            
            # Refresh all UI components (including this page) via main_window
            if hasattr(self.manager, 'refresh_ui'):
                self.manager.refresh_ui()
