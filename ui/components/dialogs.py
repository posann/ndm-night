import tkinter as tk
import customtkinter as ctk
import os
import sys
from tkinter import messagebox
from utils.font_loader import F
from utils.helpers import format_size, get_unique_path, get_resource_path, center_window
from utils.localization import L
from utils.database import save_download

def show_download_info_popup(manager, url, filename, content_length, supports_range=False):
    """Confirm download details before starting"""
    manager.update_stats() 
    
    popup = ctk.CTkToplevel(manager.root)
    popup.title(L("dialogs.info_title"))
    popup.attributes("-topmost", True)  # Ensure it pops up over browser
    
    # Center position
    center_window(popup, manager.root, 500, 320)
    popup.grab_set()
    popup.resizable(False, False)
    
    ctk.CTkLabel(popup, text=L("dialogs.file_info"), font=F(18, True), text_color="#3b8ed0").place(x=20, y=10)
    
    ctk.CTkLabel(popup, text=L("dialogs.file_name"), font=F(12, True)).place(x=20, y=60)
    url_entry = ctk.CTkEntry(popup, font=F(12, False), width=370)
    url_entry.insert(0, url)
    url_entry.configure(state='readonly')
    url_entry.place(x=100, y=60)

    ctk.CTkLabel(popup, text=L("dialogs.file_name"), font=F(12, True)).place(x=20, y=100)
    name_entry = ctk.CTkEntry(popup, font=F(12, False), width=370)
    name_entry.insert(0, filename)
    name_entry.place(x=100, y=100)

    size_str = format_size(content_length) if content_length > 0 else "Unknown / Dynamic"
    ctk.CTkLabel(popup, text=L("dialogs.file_size"), font=F(12, True)).place(x=20, y=140)
    ctk.CTkLabel(popup, text=size_str, font=F(12)).place(x=100, y=140)
    
    file_ext = os.path.splitext(filename)[1] or "Unknown"
    ctk.CTkLabel(popup, text=L("dialogs.extension"), font=F(12, True)).place(x=20, y=180)
    ctk.CTkLabel(popup, text=file_ext, font=F(12)).place(x=100, y=180)

    def on_download():
        new_filename = name_entry.get().strip() or filename
        popup.destroy()
        downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads", "NDM")
        if not os.path.exists(downloads_folder): os.makedirs(downloads_folder)
        save_path = os.path.join(downloads_folder, new_filename)
        existing_paths = [d.get('save_path') for d in manager.downloads.values()]
        save_path = get_unique_path(save_path, existing_paths)
        manager.start_download(url, save_path, os.path.basename(save_path), content_length, supports_range=supports_range)

    def on_cancel():
        manager.stats_label.configure(text="Ready")
        popup.destroy()

    ctk.CTkButton(popup, text=L("dialogs.download"), command=on_download, fg_color="#1f538d", corner_radius=8, width=150, font=F(12, True)).place(x=100, y=240)
    ctk.CTkButton(popup, text=L("dialogs.cancel"), command=on_cancel, fg_color="#3a1515", corner_radius=8, width=150, font=F(12, True)).place(x=270, y=240)

def show_download_details(manager, download_id):
    """View full details and update URL if needed"""
    if download_id not in manager.downloads: return
    info = manager.downloads[download_id]
    
    popup = ctk.CTkToplevel(manager.root)
    popup.title(L("dialogs.details_title"))
    popup.attributes("-topmost", True)
    center_window(popup, manager.root, 600, 420)
    popup.resizable(False, False)
    
    ctk.CTkLabel(popup, text="📁 " + info['filename'], font=F(15, True), wraplength=550).pack(pady=(20, 15))
    info_frame = ctk.CTkFrame(popup, fg_color="transparent")
    info_frame.pack(fill=tk.BOTH, padx=20, pady=5)

    ctk.CTkLabel(info_frame, text=L("dialogs.storage_location", path=info.get('save_path', '-')), font=F(12), anchor="w").pack(fill=tk.X, pady=3)
    ctk.CTkLabel(info_frame, text=L("dialogs.total_size", size=format_size(info.get('total_size', 0))), font=F(12), anchor="w").pack(fill=tk.X, pady=3)
    st_val = L(f"status.{info.get('status', 'error').lower()}", default=info.get('status', 'Unknown'))
    ctk.CTkLabel(info_frame, text=L("dialogs.current_status", status=st_val), font=F(12, True), text_color="#7ba7cf", anchor="w").pack(fill=tk.X, pady=3)
    ctk.CTkLabel(info_frame, text=L("dialogs.date_added", date=info.get('created_at', '-')), font=F(12), anchor="w").pack(fill=tk.X, pady=3)
    
    ctk.CTkLabel(popup, text=L("dialogs.source_url"), font=F(12, True), text_color="#4a6080").pack(pady=(0, 8))
    
    url_entry = ctk.CTkEntry(popup, width=540, font=F(12, False), height=36, fg_color="#0d1117", border_color="#1e2c3a")
    url_entry.insert(0, info.get('url', ''))
    url_entry.pack(pady=5)
    
    def do_refresh():
        new_url = url_entry.get().strip()
        if not new_url: return
        info['url'] = new_url
        save_download(info)
        manager.log_event(f"URL updated for: {info['filename']}")
        messagebox.showinfo("Success", "URL updated successfully.")
        popup.destroy()
        
    btn_row = ctk.CTkFrame(popup, fg_color="transparent")
    btn_row.pack(pady=10)
    ctk.CTkButton(btn_row, text=L("dialogs.update_url"), command=do_refresh, fg_color="#4caf50", width=120).pack(side=tk.LEFT, padx=10)
    ctk.CTkButton(btn_row, text=L("dialogs.close"), command=popup.destroy, fg_color="#f44336", width=120).pack(side=tk.LEFT, padx=10)

def on_closing(manager):
    """Custom popup for closing behavior (Minimize vs Exit)"""
    popup = ctk.CTkToplevel(manager.root)
    popup.title(L("dialogs.exit_title"))
    popup.geometry("400x220")
    popup.attributes("-topmost", True)
    popup.resizable(False, False)
    
    center_window(popup, manager.root, 400, 220)

    ctk.CTkLabel(popup, text=L("dialogs.next_action"), font=F(16, True)).pack(pady=(25, 10))
    ctk.CTkLabel(popup, text=L("dialogs.exit_desc"), font=F(12)).pack(pady=(0, 25))

    btn_row = ctk.CTkFrame(popup, fg_color="transparent")
    btn_row.pack()

    def to_tray():
        manager.root.withdraw()
        popup.destroy()
        manager.log_event("NDM is running in the background (System Tray).")

    def fully_exit():
        popup.destroy()
        manager.exit_app()

    ctk.CTkButton(btn_row, text=L("dialogs.to_tray"), width=140, height=36, font=F(12), fg_color="#1e2c3a", command=to_tray).pack(side=tk.LEFT, padx=10)
    ctk.CTkButton(btn_row, text=L("dialogs.exit_app"), width=140, height=36, font=F(12), fg_color="#3a1515", command=fully_exit).pack(side=tk.LEFT, padx=10)

def show_about_popup(manager):
    """Modern & Clean About popup for NDM"""
    popup = ctk.CTkToplevel(manager.root)
    popup.title("About NDM")
    popup.attributes("-topmost", True)
    center_window(popup, manager.root, 440, 420)
    popup.resizable(False, False)
    
    # Simple & Elegant Header
    ctk.CTkLabel(popup, text="🚀", font=("Segoe UI Emoji", 48)).pack(pady=(35, 12))
    ctk.CTkLabel(popup, text=L("app.title"), font=F(20, True), text_color="#e8edf2").pack()
    ctk.CTkLabel(popup, text=L("app.version"), font=F(12), text_color="#555f6e").pack()
    
    # Centered Divider
    ctk.CTkFrame(popup, height=1, width=320, fg_color="#1e2c3a").pack(pady=25)
    
    # Description with refined line height
    desc_text = (
        "A modular, multi-threaded engine optimized for\n"
        "speed and simplicity. Built for professional\n"
        "workflows and daily downloading."
    )
    ctk.CTkLabel(popup, text=desc_text, font=F(13), text_color="#8b9bb4").pack()
    
    # Developer Credit Section
    credit_box = ctk.CTkFrame(popup, fg_color="#161e29", corner_radius=8, height=44)
    credit_box.pack(pady=25, padx=60, fill=tk.X)
    credit_box.pack_propagate(False)
    
    ctk.CTkLabel(credit_box, text=L("about.crafted_by"), font=F(12), text_color="#555f6e").pack(side=tk.LEFT, padx=(20, 5))
    ctk.CTkLabel(credit_box, text="posann", font=F(12, True), text_color="#3b8ed0").pack(side=tk.LEFT)
    
    # Action Row
    ctk.CTkButton(popup, text="Close Window", command=popup.destroy, 
                  fg_color="#1e2c3a", hover_color="#263545", 
                  width=140, height=36, corner_radius=8, font=F(12)).pack()
