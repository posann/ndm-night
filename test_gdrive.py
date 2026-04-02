import sys
import os

# Add to path to import logic_manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.logic_manager import fetch_file_info
import threading
import time

class DummyManager:
    def __init__(self):
        self.download_id = 99
        self.mode_var = type('obj', (object,), {'set': lambda self, x: None})()
        from tkinter import Tk, Label
        self.root = Tk()
        self.stats_label = Label(self.root, text="")
        
    def show_download_info_popup(self, url, filename, content_length, supports_range):
        print(f"--- FETCH RESULT ---")
        print(f"URL: {url}")
        print(f"Filename: {filename}")
        print(f"Size: {content_length}")
        print(f"Supports Range: {supports_range}")
        print(f"--------------------")
        
        self.root.quit()

    def update_stats(self):
        pass

manager = DummyManager()
test_url = "https://drive.google.com/uc?export=download&id=1-Uq1Y_4qE0W6gE5lVXYo9cOoC5d-9rSj"

try:
    threading.Thread(target=fetch_file_info, args=(manager, test_url), daemon=True).start()
    manager.root.after(10000, manager.root.quit)
    manager.root.mainloop()
except Exception as e:
    print(e)
