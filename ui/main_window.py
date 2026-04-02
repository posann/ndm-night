import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import threading
import os
import time
import queue
import sys
from PIL import Image

try:
    from pystray import MenuItem as item
    import pystray
except ImportError:
    pass

# Utils & Helpers
from utils.helpers import format_size, format_time, get_resource_path
from utils.database import init_db, save_download, get_all_downloads, delete_download
from core.downloader import perform_download
from utils.font_loader import load_poppins, F

# Modern Page Modules
from ui.pages.downloads_page import DownloadsPage
from ui.pages.browser_page import BrowserPage
from ui.pages.logging_page import LoggingPage
from ui.pages.about_page import AboutPage
from ui.pages.settings_page import SettingsPage
from utils.localization import L

# Refactored Components & Logic
import core.server as server
import core.logic_manager as logic_manager
import ui.components.download_row as download_row
import ui.components.dialogs as dialogs
import utils.drag_drop as drag_drop

# Load Poppins BEFORE any widgets are created
load_poppins()

class DownloadManager:
    def __init__(self, root):
        self.root = root
        self.root.title("NDM")
        self.root.geometry("1100x720")
        self.root.configure(fg_color="#0d1117")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # State Variables
        self.downloads = {}
        self.download_id = 1
        self._db_throttle = 0
        self.log_history = []
        self.log_textbox = None
        self.sidebar_buttons = {}
        self.page_frames = {}
        self.current_page = None
        self.current_tab = "Active"
        self.category_filter = "All"
        
        # Load database
        init_db()
        self.load_from_db()
        
        # Setup UI
        # Force maximize after UI is ready
        self.root.update()
        self.root.after(100, lambda: self.root.state("zoomed"))

        self.setup_ui()
        
        # Update Queue
        self.update_queue = queue.Queue()
        self.process_update_queue()
        
        # Start Services
        self.log_event("Application initialized. Starting internal server...")
        server.start_server(self)
        self.check_server_status()
        self.setup_tray()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.show_page("Active")
        
        # Focus window
        self.root.after(100, lambda: (self.root.deiconify(), self.root.focus_force(), self.root.lift()))

    # ── LOGGING ────────────────────────────────────────────────────────────
    def log_event(self, message, level="INFO"):
        """Central logging with UI text display + console output"""
        timestamp = time.strftime("[%H:%M:%S]")
        log_entry = f"{timestamp} [{level}] {message}\n"
        print(log_entry, end="")
        
        self.log_history.append(log_entry)
        if len(self.log_history) > 500: self.log_history = self.log_history[-500:]
        
        def _update_ui():
            if getattr(self, 'log_textbox', None) and self.log_textbox.winfo_exists():
                try:
                    self.log_textbox.configure(state="normal")
                    self.log_textbox.insert(tk.END, log_entry)
                    self.log_textbox.see(tk.END)
                    self.log_textbox.configure(state="disabled")
                except: pass
        self.root.after(0, _update_ui)

    # ── DELEGATIONS TO REFACTORED MODULES ──────────────────────────────────
    def handle_external_request(self, url): logic_manager.handle_external_request(self, url)
    def add_download(self): logic_manager.add_download(self)
    def start_download(self, *args, **kwargs): logic_manager.start_download(self, *args, **kwargs)
    def pause_download(self, id): logic_manager.pause_download(self, id)
    def resume_download(self, id): logic_manager.resume_download(self, id)
    def cancel_download(self, id): logic_manager.cancel_download(self, id)
    def pause_all(self): logic_manager.pause_all(self)
    def resume_all(self): logic_manager.resume_all(self)
    def clear_completed(self): logic_manager.clear_completed(self)
    def redownload(self, id): logic_manager.redownload(self, id)
    
    def create_download_ui(self, info): download_row.create_download_ui(self, info)
    def update_download_ui(self, info): download_row.update_download_ui(self, info)
    
    def show_download_info_popup(self, *args): dialogs.show_download_info_popup(self, *args)
    def show_download_details(self, id): dialogs.show_download_details(self, id)
    def on_closing(self): dialogs.on_closing(self)
    def show_about_popup(self): dialogs.show_about_popup(self)
    
    def start_shell_drag(self): drag_drop.start_shell_drag(self)

    # ── UI ARCHITECTURE ────────────────────────────────────────────────────
    def setup_ui(self):
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # ── Sidebar ──
        self.sidebar_frame = ctk.CTkFrame(self.root, width=230, corner_radius=0, fg_color="#0d1117")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        for i in range(12): self.sidebar_frame.grid_rowconfigure(i, weight=1 if i==10 else 0)
        self.sidebar_frame.grid_columnconfigure(0, weight=1)

        # Logo
        logo_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        logo_container.grid(row=0, column=0, padx=20, pady=(28, 18), sticky="ew")
        logo_top = ctk.CTkFrame(logo_container, fg_color="transparent")
        logo_top.pack(fill=tk.X)
        ctk.CTkFrame(logo_top, width=4, height=32, fg_color="#3b8ed0", corner_radius=2).pack(side=tk.LEFT, padx=(0, 10))
        ctk.CTkLabel(logo_top, text="NDM", font=F(22, True)).pack(side=tk.LEFT)
        self.app_title_label = ctk.CTkLabel(logo_container, text=L("app.title"), font=F(12), text_color="#555f6e")
        self.app_title_label.pack(anchor="w", pady=(4, 0))

        # Buttons
        NAV_BTN = {"corner_radius": 8, "height": 40, "anchor": "w", "fg_color": "transparent", "hover_color": "#1a2130", "text_color": "#e8edf2", "font": F(13, True)}
        SUB_BTN = {"corner_radius": 6, "height": 36, "anchor": "w", "fg_color": "transparent", "hover_color": "#1a2130", "text_color": "#e8edf2", "font": F(12, True)}

        self.sidebar_buttons["All"] = ctk.CTkButton(self.sidebar_frame, text=L("sidebar.downloads_header"), font=F(13, True), text_color="#3b8ed0", anchor="w", fg_color="transparent", command=lambda: self.show_page("All"))
        self.sidebar_buttons["All"].grid(row=2, column=0, padx=20, pady=(16, 4), sticky="ew")

        for i, (name, icon, key) in enumerate([("Active", "", "active"), ("Success", "", "completed"), ("Error", "", "failed")]):
            txt = icon + L(f"sidebar.{key}")
            self.sidebar_buttons[name] = ctk.CTkButton(self.sidebar_frame, text=txt, command=lambda n=name: self.show_page(n), **SUB_BTN)
            self.sidebar_buttons[name].grid(row=3+i, column=0, padx=(28, 12), pady=1, sticky="ew")

        # Tools: Browser, Settings, Logging, About
        for i, (name, icon, key) in enumerate([
            ("Browser", "", "sidebar.integration"), 
            ("Settings", "", "settings.title"),
            ("Logging", "", "sidebar.activity_log"),
            ("About", "", "sidebar.about_ndm")
        ]):
            txt = icon + L(key)
            self.sidebar_buttons[name] = ctk.CTkButton(self.sidebar_frame, text=txt, command=lambda n=name: self.show_page(n), **NAV_BTN)
            self.sidebar_buttons[name].grid(row=6+i, column=0, padx=12, pady=1, sticky="ew")

        # Footer
        footer = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        footer.grid(row=11, column=0, padx=16, pady=(8, 20), sticky="ew")
        self.autostart_var = tk.BooleanVar(value=self.check_autostart_status())
        self.autostart_switch = ctk.CTkSwitch(footer, text=L("sidebar.start_on_boot"), variable=self.autostart_var, command=self.toggle_autostart, font=F(12), text_color="#555f6e")
        self.autostart_switch.pack(anchor="w")

        self.content_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="#111920")
        self.content_frame.grid(row=0, column=1, sticky="nsew")

    def show_page(self, name):
        if self.current_page == name: return
        D_PAGES = {"All", "Active", "Success", "Error"}
        for n, b in self.sidebar_buttons.items():
            is_a = (n == name)
            b.configure(fg_color="#182030" if is_a else "transparent", text_color="#e8edf2" if is_a else ("#6b7a8d" if n in D_PAGES else "#8b9bb4"))

        target_key = "Downloads" if name in D_PAGES else name
        if self.current_page:
            curr_key = "Downloads" if self.current_page in D_PAGES else self.current_page
            if curr_key in self.page_frames and target_key != curr_key: self.page_frames[curr_key].pack_forget()

        if target_key not in self.page_frames:
            if target_key == "Downloads": self.page_frames[target_key] = DownloadsPage(self.content_frame, self)
            elif target_key == "Browser": self.page_frames[target_key] = BrowserPage(self.content_frame, self)
            elif target_key == "Logging": self.page_frames[target_key] = LoggingPage(self.content_frame, self)
            elif target_key == "Settings": self.page_frames[target_key] = SettingsPage(self.content_frame, self)
            elif target_key == "About": self.page_frames[target_key] = AboutPage(self.content_frame, self)

        self.page_frames[target_key].pack(fill=tk.BOTH, expand=True)
        if name in D_PAGES:
            self.current_tab = name
            self.filter_downloads()
            self.update_bulk_buttons_state()
        self.current_page = name

    # ── LOGIC & HELPERS ─────────────────────────────────────────────────────
    def perform_download_thread(self, info):
        perform_download(info, self.update_queue)

    def open_folder(self, filepath):
        folder = os.path.dirname(filepath)
        if os.path.exists(folder): os.startfile(folder)

    def paste_url(self):
        try:
            url = self.root.clipboard_get()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)
        except: messagebox.showwarning("Warning", "Could not paste URL")

    # ──────────────────────────────────────────────────────────────────────────
    # Filtering & Stats
    # ──────────────────────────────────────────────────────────────────────────
    FILE_CATEGORIES = {
        "Compressed": {".zip", ".rar", ".7z", ".tar", ".gz"},
        "Video": {".mp4", ".mkv", ".avi", ".mov"},
        "Audio": {".mp3", ".wav", ".flac"},
        "Image": {".jpg", ".jpeg", ".png", ".webp"},
        "Document": {".pdf", ".docx", ".xlsx", ".txt"},
        "Program": {".exe", ".msi", ".apk"}
    }

    def filter_downloads(self, selected_tab=None):
        try:
            if selected_tab: self.current_tab = selected_tab
            q = self.search_var.get().strip().lower() if hasattr(self, 'search_var') else ""
            cat = getattr(self, 'category_filter', 'All')

            items = []
            for d_id, info in self.downloads.items():
                if 'ui_frame' not in info or not info['ui_frame'].winfo_exists(): continue
                info['ui_frame'].pack_forget()
                info['is_visible'] = False

                st = info.get('status', '').lower()
                is_f = "error" in st and not ("connection" in st or "paused" in st or "resumable" in st)
                tab_cat = "Success" if st == 'completed' else ("Error" if (st == 'cancelled' or is_f) else "Active")

                if self.current_tab != 'All' and tab_cat != self.current_tab: continue
                if q and q not in info.get('filename', '').lower() and q not in info.get('url', '').lower(): continue
                if cat != "All" and os.path.splitext(info.get('filename', ''))[1].lower() not in self.FILE_CATEGORIES.get(cat, set()): continue
                items.append(info)

            items.sort(key=lambda x: x.get('completed_at' if self.current_tab=="Success" else 'id', 0), reverse=True)
            for info in items:
                info['ui_frame'].pack(fill=tk.X, pady=5, padx=5)
                info['is_visible'] = True
        except: pass

    def update_stats(self):
        try:
            active = sum(1 for d in self.downloads.values() if d['status'] not in ['Completed', 'Cancelled', 'Error'])
            completed = sum(1 for d in self.downloads.values() if d['status'] == 'Completed')
            total = sum(d['total_size'] for d in self.downloads.values())
            if hasattr(self, 'stats_label') and self.stats_label.winfo_exists():
                active_txt = L("downloads.stats.active", count=active)
                done_txt = L("downloads.stats.completed", count=completed)
                total_txt = L("downloads.stats.total", size=format_size(total))
                self.stats_label.configure(text=f"{active_txt} | {done_txt} | {total_txt}")
            self.update_bulk_buttons_state()
        except: pass

    def refresh_ui(self):
        """Refreshes sidebar buttons and other static UI elements after a language change"""
        # Updates App Title
        if hasattr(self, 'app_title_label'):
            self.app_title_label.configure(text=L("app.title"))
            
        # Updates Downloads button
        self.sidebar_buttons["All"].configure(text=L("sidebar.downloads_header"))
        
        # Updates Category labels
        sub_items = [("Active", "", "sidebar.active"), 
                     ("Success", "", "sidebar.completed"), 
                     ("Error", "", "sidebar.failed")]
        for name, icon, key in sub_items:
            if name in self.sidebar_buttons:
                self.sidebar_buttons[name].configure(text=icon + L(key))
        
        # Updates Tool labels
        tool_items = [("Browser", "", "sidebar.integration"), 
                      ("Settings", "", "settings.title"),
                      ("Logging", "", "sidebar.activity_log"), 
                      ("About", "", "sidebar.about_ndm")]
        for name, icon, key in tool_items:
            if name in self.sidebar_buttons:
                self.sidebar_buttons[name].configure(text=icon + L(key))
        
        # Updates Footer Switch
        if hasattr(self, 'autostart_switch'):
            self.autostart_switch.configure(text=L("sidebar.start_on_boot"))
                
        # Re-trigger stats update to refresh labels like "Active: {count}"
        self.update_stats()
        
        # Refresh current active page if it has a setup_ui or refresh method
        if self.current_page:
            target_key = "Downloads" if self.current_page in {"All", "Active", "Success", "Error"} else self.current_page
            if target_key in self.page_frames:
                page = self.page_frames[target_key]
                # If page has a specific refresh/re-init method, use it
                if hasattr(page, 'setup_ui'):
                    for widget in page.winfo_children():
                        widget.destroy()
                    page.setup_ui()
                elif hasattr(page, 'refresh_ui'):
                    page.refresh_ui()

    def process_update_queue(self):
        try:
            while True:
                up_type, data = self.update_queue.get_nowait()
                if up_type == 'update' and data in self.downloads:
                    info = self.downloads[data]
                    old_s, curr_s = info.get('last_filtered_status', ''), info.get('status', '')
                    self.update_download_ui(info)
                    
                    if self.current_tab != "All" and old_s and old_s != curr_s:
                        s_t = lambda s: "Success" if s == "Completed" else ("Error" if ("Error" in s or s == "Cancelled") else "Active")
                        if s_t(old_s) != s_t(curr_s): self.filter_downloads()
                    
                    info['last_filtered_status'] = curr_s
                    self.update_stats()
                    if curr_s in ['Completed', 'Paused', 'Cancelled', 'Error'] or self._db_throttle % 10 == 0: save_download(info)
                    self._db_throttle += 1
                elif up_type == 'complete' and data in self.downloads:
                    if 'completed_at' not in self.downloads[data]:
                        self.downloads[data]['completed_at'] = time.time()
                        save_download(self.downloads[data])
                    self.filter_downloads()
                    messagebox.showinfo("Download Complete", f"Finished: {self.downloads[data]['filename']}")
                elif up_type == 'remove':
                    self.remove_download_ui(data)
                    self.filter_downloads()
        except queue.Empty: pass
        finally: self.root.after(100, self.process_update_queue)

    def remove_download_ui(self, id):
        if id in self.downloads:
            if 'ui_frame' in self.downloads[id]: self.downloads[id]['ui_frame'].destroy()
            del self.downloads[id]
            delete_download(id)
            self.update_stats()

    def update_bulk_buttons_state(self):
        try:
            count = len(self.get_selected_ids())
            state = "normal" if count > 0 else "disabled"
            if hasattr(self, 'bulk_btns'):
                for k in ['delete', 'pause', 'resume']:
                    if k in self.bulk_btns and self.bulk_btns[k].winfo_exists(): self.bulk_btns[k].configure(state=state)
                
                if 'clear_success' in self.bulk_btns and self.bulk_btns['clear_success'].winfo_exists():
                    if getattr(self, 'current_tab', '') == "Success":
                        self.bulk_btns['clear_success'].pack(side=tk.RIGHT, padx=5)
                        self.bulk_btns['clear_success'].configure(state="normal" if any(d['status'] == 'Completed' for d in self.downloads.values()) else "disabled")
                    else: self.bulk_btns['clear_success'].pack_forget()
        except: pass

    def get_selected_ids(self):
        return [d_id for d_id, info in self.downloads.items() if info.get('ui_check') and info['ui_check'].get()]

    def clear_selected(self):
        sel = self.get_selected_ids()
        if sel and messagebox.askyesno("Confirm", f"Remove {len(sel)} items?"):
            for d_id in sel: self.cancel_download(d_id)
            if hasattr(self, 'select_all_var'): self.select_all_var.set(False)

    def pause_selected(self): [self.pause_download(d_id) for d_id in self.get_selected_ids()]
    def resume_selected(self): [self.resume_download(d_id) for d_id in self.get_selected_ids()]
    def toggle_select_all(self):
        val = self.select_all_var.get()
        for info in self.downloads.values():
            # Only select items that are currently filtered/visible to the user
            if info.get('is_visible') and 'ui_check' in info:
                info['ui_check'].set(val)
        self.update_bulk_buttons_state()

    # ── Database & Tray ──
    def load_from_db(self):
        loaded = get_all_downloads()
        if loaded:
            self.download_id = max(loaded.keys()) + 1
            for d_id, info in loaded.items():
                self.downloads[d_id] = info
                if info.get('status') not in ['Completed', 'Cancelled', 'Error'] and not info.get('status', '').startswith('Paused'):
                    info['status'] = 'Paused (App Closed)'
                    info['paused'] = True
                    save_download(info)
        self.root.after(100, self.restore_ui_from_db)

    def restore_ui_from_db(self):
        for info in self.downloads.values():
            if 'ui_frame' not in info: self.create_download_ui(info)
        self.update_stats()

    def setup_tray(self):
        try:
            image = Image.open(get_resource_path("ndm_logo.png"))
            menu = (item('Open NDM', self.show_window, default=True), item('Pause All', self.pause_all), item('Resume All', self.resume_all), item('Exit', self.exit_app))
            self.tray_icon = pystray.Icon("NDM", image, "NDM", menu)
            self.tray_icon.action = self.show_window
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except: pass

    def show_window(self, icon=None, item=None):
        self.root.after(0, lambda: (self.root.deiconify(), self.root.lift(), self.root.focus_force()))

    def exit_app(self, icon=None, item=None):
        if hasattr(self, 'tray_icon'): self.tray_icon.stop()
        self.root.after(0, self.root.quit)
        os._exit(0)

    def check_server_status(self):
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                is_a = (s.connect_ex(('127.0.0.1', 5555)) == 0)
                if hasattr(self, 'status_dot') and self.status_dot.winfo_exists():
                    self.status_dot.configure(text_color="#4caf50" if is_a else "#f44336")
                    self.status_text.configure(text="Server Active (Port 5555)" if is_a else "Server Offline")
        except: pass
        self.root.after(5000, self.check_server_status)

    def check_autostart_status(self):
        import winreg as reg
        try:
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_READ)
            reg.QueryValueEx(key, "NDM_Nusantara_DM")
            reg.CloseKey(key)
            return True
        except: return False

    def toggle_autostart(self):
        import winreg as reg
        cmd = f'"{sys.executable}"' if getattr(sys, 'frozen', False) else f'python "{os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "app.py")}"'
        try:
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_SET_VALUE)
            if self.autostart_var.get(): reg.SetValueEx(key, "NDM_Nusantara_DM", 0, reg.REG_SZ, cmd)
            else:
                try: reg.DeleteValue(key, "NDM_Nusantara_DM")
                except: pass
            reg.CloseKey(key)
        except: pass
