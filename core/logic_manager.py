import tkinter as tk
from tkinter import messagebox
import threading
import os
import time
import requests
import re
import mimetypes
from urllib.parse import urlparse, unquote
from utils.helpers import format_size, get_unique_path
from utils.database import save_download, delete_download, load_downloads
from utils.localization import L
from core.downloader import perform_download

def handle_external_request(manager, url):
    """Process URL sent from Chrome extension"""
    manager.log_event(f"Received URL from Chrome: {url}")
    
    # Switch to Downloads page if needed
    if manager.current_page != "Downloads":
        manager.show_page("Downloads")
    
    def _insert_and_download():
        if getattr(manager, 'url_entry', None) and manager.url_entry.winfo_exists():
            manager.url_entry.delete(0, tk.END)
            manager.url_entry.insert(0, url)
            manager.add_download()
        else:
            manager.log_event("handle_external_request: url_entry not ready, retrying...", "WARN")
            manager.root.after(200, _insert_and_download)
    
    manager.root.after(150, _insert_and_download)

def add_download(manager):
    """Triggers the download addition flow"""
    url = manager.url_entry.get().strip()
    if not url:
        messagebox.showwarning(L("messages.warning"), L("messages.enter_url"))
        return
        
    manager.log_event(f"{L('downloads.adding')} {url[:60]}...", "INFO")
        
    # AUTO-DETECTION for Google Drive
    is_gdrive = "drive.google.com" in url or "docs.google.com" in url or "drive.usercontent.google.com" in url
    if is_gdrive:
        manager.mode_var.set("GDrive")
        new_url = convert_gdrive_url(url)
        if new_url != url:
            manager.url_entry.delete(0, tk.END)
            manager.url_entry.insert(0, new_url)
            url = new_url
    else:
        manager.mode_var.set("Manual")

    # Show status to user
    manager.stats_label.configure(text="Fetching file info...")
    
    # Start fetching in thread
    threading.Thread(target=fetch_file_info, args=(manager, url), daemon=True).start()
    
    # Clear the URL entry immediately so it's ready for the next one (User request)
    manager.url_entry.delete(0, tk.END)

def convert_gdrive_url(url):
    """Convert sharing GDrive URL to Direct Download URL"""
    import re
    patterns = [
        r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
        r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
        r'docs\.google\.com/uc\?id=([a-zA-Z0-9_-]+)',
        r'drive\.google\.com/uc\?id=([a-zA-Z0-9_-]+)'
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

def fetch_file_info(manager, url):
    """Asynchronously fetches filename and size before showing the confirmation popup"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, stream=True, allow_redirects=True, timeout=10)
        
        # Google Drive bypass logic
        confirm_token = None
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                confirm_token = value
                break
        if confirm_token:
            separator = "&" if "?" in url else "?"
            url += f"{separator}confirm={confirm_token}"
            response = session.get(url, stream=True, allow_redirects=True, timeout=10)
        
        response.raise_for_status()
        
        filename = ""
        cd = response.headers.get('content-disposition', '')
        if cd:
            fname_star = re.findall(r"filename\*=UTF-8''([^;]+)", cd, flags=re.IGNORECASE)
            fname_quoted = re.findall(r'filename="([^"]+)"', cd, flags=re.IGNORECASE)
            fname_unquoted = re.findall(r'filename=([^;]+)', cd, flags=re.IGNORECASE)
            
            if fname_star:
                filename = unquote(fname_star[0])
            elif fname_quoted:
                filename = fname_quoted[0]
            elif fname_unquoted:
                filename = fname_unquoted[0].strip("'\" \t")
        
        if not filename or filename == 'uc' or filename == 'download':
            parsed_url = urlparse(url)
            filename = os.path.basename(unquote(parsed_url.path))
            
            if not filename or filename in ['uc', 'download']:
                content_type = response.headers.get('content-type', '').split(';')[0].strip()
                ext = mimetypes.guess_extension(content_type) or ''
                
                # Manual overrides for robustness
                if content_type == 'application/pdf': ext = '.pdf'
                elif content_type == 'application/zip': ext = '.zip'
                elif content_type == 'application/x-zip-compressed': ext = '.zip'
                elif content_type == 'application/vnd.android.package-archive': ext = '.apk'
                elif content_type == 'application/x-rar-compressed': ext = '.rar'
                elif not ext: ext = '.bin'
                
                prefix = "gdrive_file_" if "drive.google.com" in url or "docs.google.com" in url else "file_"
                filename = f"{prefix}{manager.download_id}{ext}"
        
        if '?' in filename:
            filename = filename.split('?')[0]
            
        content_length = int(response.headers.get('content-length', 0))
        
        # Detect if server supports range requests (for multi-threading)
        # 1. Check Accept-Ranges header
        # 2. If it's a 206 response (unlikely here but possible)
        # 3. Content-Length must be known for reliable segmentation
        accept_ranges = response.headers.get('Accept-Ranges', '').lower()
        supports_range = (accept_ranges == 'bytes' or response.status_code == 206) and content_length > 0
        
        response.close()
        
        # Return to UI thread for the popup
        manager.root.after(0, lambda: manager.show_download_info_popup(url, filename, content_length, supports_range))
        
    except Exception as e:
        manager.root.after(0, lambda err=e: messagebox.showerror("Error", f"Failed to get URL info: {str(err)}"))
        manager.root.after(0, manager.update_stats)

def start_download(manager, url, save_path, filename, content_length, **kwargs):
    """Initializes the download metadata and starts the threading process"""
    try:
        download_info = {
            'id': manager.download_id,
            'url': url,
            'save_path': save_path,
            'filename': filename,
            'total_size': content_length,
            'downloaded': 0,
            'status': 'Starting',
            'speed': 0,
            'progress': 0,
            'start_time': time.time(),
            'created_at': time.strftime("%Y-%m-%d %H:%M"),
            'elapsed_time': "00:00",
            'eta': "--:--",
            'paused': False,
            'resume_pos': 0,
            'supports_range': kwargs.get('supports_range', False)
        }
        
        manager.downloads[manager.download_id] = download_info
        save_download(download_info)
        manager.download_id += 1
        
        manager.create_download_ui(download_info)
        threading.Thread(target=manager.perform_download_thread, args=(download_info,), daemon=True).start()
        
    except Exception as e:
        messagebox.showerror("Error", f"Gagal memulai download: {str(e)}")

def pause_download(manager, download_id):
    if download_id in manager.downloads:
        info = manager.downloads[download_id]
        info['paused'] = True
        manager.log_event(f"Download paused: {info['filename']}")
        info['status'] = 'Pausing...'
        manager.update_queue.put(('update', download_id))

def resume_download(manager, download_id):
    if download_id in manager.downloads:
        info = manager.downloads[download_id]
        info['paused'] = False
        info['status'] = 'Resuming...'
        manager.log_event(f"Download resumed: {info['filename']}")
        manager.update_queue.put(('update', download_id))
        threading.Thread(target=manager.perform_download_thread, args=(info,), daemon=True).start()

def cancel_download(manager, download_id):
    if download_id in manager.downloads:
        info = manager.downloads[download_id]
        info['paused'] = True
        info['status'] = 'Cancelled'
        manager.log_event(f"Download cancelled: {info['filename']}", "WARN")
        if info['progress'] < 100 and os.path.exists(info['save_path']):
            try: os.remove(info['save_path'])
            except: pass
        manager.update_queue.put(('remove', download_id))

def pause_all(manager):
    for d_id in list(manager.downloads.keys()):
        pause_download(manager, d_id)

def resume_all(manager):
    for d_id in list(manager.downloads.keys()):
        resume_download(manager, d_id)

def clear_completed(manager):
    for d_id in list(manager.downloads.keys()):
        if manager.downloads[d_id]['status'] == 'Completed':
            manager.remove_download_ui(d_id)

def redownload(manager, download_id):
    if download_id in manager.downloads:
        info = manager.downloads[download_id]
        if os.path.exists(info['save_path']):
            try: os.remove(info['save_path'])
            except: pass
        
        info['downloaded'] = 0
        info['resume_pos'] = 0
        info['progress'] = 0
        info['status'] = 'Starting'
        info['paused'] = False
        info['start_time'] = time.time()
        manager.log_event(f"Re-downloading file: {info['filename']}")
        
        manager.update_queue.put(('update', download_id))
        threading.Thread(target=manager.perform_download_thread, args=(info,), daemon=True).start()
