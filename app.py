import customtkinter as ctk
from ui.main_window import DownloadManager
from utils.localization import init_localization
from utils.database import init_db, get_setting

if __name__ == "__main__":
    # Initialize database and load saved settings
    init_db()
    saved_lang = get_setting("language", "en")
    init_localization(saved_lang)
    
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    root.state('zoomed')  # Starts the window in maximized mode
    app = DownloadManager(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()