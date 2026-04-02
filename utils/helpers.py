import os
import sys

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # In dev mode, use the project root relative to this file's location
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)

def get_data_path(filename):
    """ 
    Get absolute path to data file. 
    In portable mode, stores data in the same directory as the executable.
    Otherwise, uses the system AppData directory.
    """
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        # Check if we are running the portable version
        is_portable = "Portable" in os.path.basename(sys.executable) or \
                      os.path.exists(os.path.join(base_dir, "portable"))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        is_portable = os.path.exists(os.path.join(base_dir, "portable"))

    if is_portable:
        ndm_dir = base_dir
    else:
        app_data = os.getenv('APPDATA')
        if not app_data:
            # Fallback for non-Windows or missing env var
            app_data = os.path.expanduser("~")
        ndm_dir = os.path.join(app_data, 'NDM')
    
    if not os.path.exists(ndm_dir):
        try:
            os.makedirs(ndm_dir)
        except: pass
        
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
