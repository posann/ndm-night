import os
import sys

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_data_path(filename):
    """ Get absolute path to data file in AppData directory for persistent storage """
    app_data = os.getenv('APPDATA')
    ndm_dir = os.path.join(app_data, 'NDM')
    if not os.path.exists(ndm_dir):
        os.makedirs(ndm_dir)
    return os.path.join(ndm_dir, filename)

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def get_unique_path(target_path, existing_in_queue=None):
    if existing_in_queue is None:
        existing_in_queue = []
        
    if not os.path.exists(target_path) and target_path not in existing_in_queue:
        return target_path
    
    base, ext = os.path.splitext(target_path)
    counter = 1
    
    final_path = target_path
    while os.path.exists(final_path) or final_path in existing_in_queue:
        counter += 1
        final_path = f"{base}-{counter}{ext}"
    
    return final_path

def format_time(seconds):
    if seconds is None or seconds < 0:
        return "--:--"
    if seconds == float('inf'):
        return "Infinity"
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{00:02d}:{minutes:02d}:{seconds:02d}"

def center_window(window, parent, width, height):
    """ Centers a window relative to its parent, or the screen if parent is hidden. """
    window.update_idletasks()
    
    # If parent is hidden or minimized, center on screen
    if parent.state() == "withdrawn" or parent.state() == "iconic":
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
    else:
        # Center relative to parent window
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        
        x = parent_x + (parent_w // 2) - (width // 2)
        y = parent_y + (parent_h // 2) - (height // 2)
        
    window.geometry(f"{width}x{height}+{x}+{y}")
