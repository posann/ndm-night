import tkinter as tk
import customtkinter as ctk
import os
import time
from utils.helpers import format_size, format_time
from utils.font_loader import F
from utils.database import save_download, delete_download, load_downloads
from utils.localization import L

def create_download_ui(manager, download_info):
    """Initializes the UI row for a single download item"""
    # Initial status colors (Active)
    frame_bg = "#1a1212"
    border_c = "#2d1a1a"
    
    # Main container for each download row
    frame = ctk.CTkFrame(manager.downloads_frame, fg_color=frame_bg, corner_radius=12, border_width=1, border_color=border_c)
    
    # Store UI references
    download_info['ui_frame'] = frame
    download_info['is_visible'] = False
    
    # Header Row (Checkbox + Filename)
    header_row = ctk.CTkFrame(frame, fg_color="transparent")
    header_row.pack(fill=tk.X, padx=12, pady=(12, 6))
    
    # Checkbox
    check_var = tk.BooleanVar(value=False)
    download_info['ui_check'] = check_var
    checkbox = ctk.CTkCheckBox(
        header_row, text="", variable=check_var, width=20, 
        command=manager.update_bulk_buttons_state,
        fg_color="#1f538d", hover_color="#1a4070"
    )
    checkbox.pack(side=tk.LEFT, padx=(0, 8))
    
    # Filename
    name_label = ctk.CTkLabel(header_row, text=download_info['filename'], 
                              font=F(14, True), text_color="#e8edf2", anchor='w')
    name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # Progress bar
    progress_bar = ctk.CTkProgressBar(frame, height=10, fg_color="#0d1117", progress_color="#1f538d")
    progress_bar.set(0)
    progress_bar.pack(fill=tk.X, padx=12, pady=6)
    
    # Stats Container
    stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
    stats_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
    stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
    
    # Section 1: Status & Speed
    status_var = tk.StringVar(value="Status: Starting...")
    status_var = tk.StringVar(value=f"{L('row.status')}: {L('status.starting')}")
    speed_var = tk.StringVar(value="0 B/s")
    ctk.CTkLabel(stats_frame, textvariable=status_var, font=F(12, True), text_color="#7ba7cf", anchor='w').grid(row=0, column=0, sticky='w')
    ctk.CTkLabel(stats_frame, textvariable=speed_var, font=F(12), text_color="#3b8ed0", anchor='w').grid(row=1, column=0, sticky='w')
    
    # Section 2: Size Progress
    size_var = tk.StringVar(value=f"0 B / {L('row.unknown')}")
    ctk.CTkLabel(stats_frame, text=L("row.progress"), font=F(12, True), text_color="#4a6080").grid(row=0, column=1)
    ctk.CTkLabel(stats_frame, textvariable=size_var, font=F(12)).grid(row=1, column=1)
    
    # Section 3: ETA & Time
    eta_var = tk.StringVar(value="--:--")
    time_var = tk.StringVar(value="00:00")
    ctk.CTkLabel(stats_frame, textvariable=eta_var, font=F(12), text_color="#e67e22", anchor='e').grid(row=0, column=2, sticky='e')
    ctk.CTkLabel(stats_frame, textvariable=time_var, font=F(12), text_color="#555f6e", anchor='e').grid(row=1, column=2, sticky='e')
    
    # Date Info (Small at bottom)
    date_var = tk.StringVar(value=f"{L('row.added')}: {download_info.get('created_at', '-')}")
    ctk.CTkLabel(frame, textvariable=date_var, font=('Arial', 11), text_color="gray40", anchor='e').pack(side=tk.RIGHT, padx=10, pady=(0, 5))
    
    # Button frame
    btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
    btn_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
    
    # Store variables for updates
    download_info['ui_vars'] = {
        'status': status_var,
        'speed': speed_var,
        'size': size_var,
        'eta': eta_var,
        'time': time_var,
        'date': date_var
    }
    
    btn_style = {"corner_radius": 8, "width": 105, "height": 32, "font": F(12)}
    download_id = download_info['id']

    pause_btn = ctk.CTkButton(btn_frame, text=L("row.pause"), 
                              command=lambda: manager.pause_download(download_id),
                              fg_color="#3a2d10", hover_color="#4a3a18", **btn_style)
    
    resume_btn = ctk.CTkButton(btn_frame, text=L("row.resume"), 
                               command=lambda: manager.resume_download(download_id),
                               fg_color="#1a3d2a", hover_color="#22503a", **btn_style)
    
    cancel_btn = ctk.CTkButton(btn_frame, text=L("row.cancel"), 
                               command=lambda: manager.cancel_download(download_id),
                               fg_color="#3a1515", hover_color="#4a1e1e", **btn_style)
    
    info_btn = ctk.CTkButton(btn_frame, text=L("row.details"), 
                                command=lambda id=download_id: manager.show_download_details(id),
                                fg_color="#1e2c3a", hover_color="#263545", **btn_style)
    
    open_btn = ctk.CTkButton(btn_frame, text=L("row.open_folder", default="Open Folder"), 
                             command=lambda: manager.open_folder(download_info['save_path']),
                             fg_color="#1f538d", hover_color="#1a4070", **btn_style)
                             
    redownload_btn = ctk.CTkButton(btn_frame, text=L("row.redownload", default="Re-download"), 
                             command=lambda: manager.redownload(download_id),
                             fg_color="#3a2d10", hover_color="#4a3a18", **btn_style)
    
    # Simpan referensi widget
    download_info['ui_progress'] = progress_bar
    download_info['ui_buttons'] = {
        'pause': pause_btn, 
        'resume': resume_btn, 
        'cancel': cancel_btn, 
        'info': info_btn, 
        'open': open_btn,
        'redownload': redownload_btn
    }
    
    update_download_ui(manager, download_info)
    manager.filter_downloads()

def update_download_ui(manager, download_info):
    """Updates the UI row for a single download item based on its status"""
    if 'ui_vars' in download_info:
        vars = download_info['ui_vars']
        
        # Format values
        speed_text = format_size(download_info['speed']) + "/s" if download_info['speed'] > 0 else "0 B/s"
        downloaded_text = format_size(download_info['downloaded'])
        total_text = format_size(download_info['total_size']) if download_info['total_size'] > 0 else L('row.unknown')
        
        # Update individual labels
        status_key = f"status.{download_info['status'].lower()}"
        vars['status'].set(f"{L('row.status')}: {L(status_key, default=download_info['status'])}")
        vars['speed'].set(f"{speed_text}")
        vars['size'].set(f"{downloaded_text} / {total_text}")
        vars['eta'].set(f"{download_info.get('eta', '--:--')}")
        vars['time'].set(f"{download_info.get('elapsed_time', '00:00')}")
        
        # Set CTkProgressBar takes float between 0 and 1
        if 'ui_progress' in download_info:
            try:
                progress_val = download_info['progress'] / 100.0 if download_info['progress'] else 0
                download_info['ui_progress'].set(progress_val)
            except Exception:
                pass
        
        # Update Button Visibility based on status
        status = download_info.get('status', '')
        # Update Background Color based on status
        if status == 'Completed':
            category = "Success"
            frame_bg = "#0d2216" # Subtle dark green
            border_c = "#143a25"
        elif 'Error' in status or status == 'Cancelled':
            category = "Error"
            frame_bg = "#2a1515" # Subtle dark red
            border_c = "#3d2020"
        else:
            category = "Active"
            frame_bg = "#1a1212" # Very subtle deep red/burgundy
            border_c = "#2d1a1a"
        
        # Apply dynamic colors
        if 'ui_frame' in download_info:
            download_info['ui_frame'].configure(fg_color=frame_bg, border_color=border_c)
            
        update_buttons_visibility(download_info, category)

def update_buttons_visibility(download_info, category):
    """Internal helper to manage which action buttons are visible for each status"""
    buttons = download_info.get('ui_buttons', {})
    if not isinstance(buttons, dict):
        return
        
    try:
        for btn in buttons.values():
            btn.pack_forget()
            
        if category == "Active":
            buttons['info'].pack(side=tk.LEFT, padx=5)
            if download_info.get('paused', False):
                buttons['resume'].pack(side=tk.LEFT, padx=5)
            else:
                buttons['pause'].pack(side=tk.LEFT, padx=5)
            buttons['cancel'].pack(side=tk.LEFT, padx=5)
        elif category == "Success":
            buttons['info'].pack(side=tk.LEFT, padx=5)
            buttons['open'].pack(side=tk.LEFT, padx=5)
            buttons['redownload'].pack(side=tk.LEFT, padx=5)
        elif category == "Error":
            buttons['info'].pack(side=tk.LEFT, padx=5)
            buttons['resume'].pack(side=tk.LEFT, padx=5)
            buttons['cancel'].pack(side=tk.LEFT, padx=5)
    except Exception:
        pass
