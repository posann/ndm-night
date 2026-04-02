import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.logic_manager import fetch_file_info

class DummyManager:
    def __init__(self):
        self.download_id = 99
        self.mode_var = type('obj', (object,), {'set': lambda self, x: None})()
        
    def show_download_info_popup(self, url, filename, content_length, supports_range):
        print(f"--- FETCH RESULT ---")
        print(f"\nURL: {url}")
        print(f"Filename: {filename}")
        print(f"Size: {content_length}")
        print(f"Supports Range: {supports_range}")
        print(f"--------------------")

    def update_stats(self):
        pass

manager = DummyManager()

class MockRoot:
    def after(self, ms, func):
        try:
            func()
        except Exception as ex:
            print(f"After func exception: {ex}")

manager.root = MockRoot()

import tkinter.messagebox
def mock_showerror(title, msg):
    print(f"SHOW_ERROR: {title} - {msg}")
tkinter.messagebox.showerror = mock_showerror

test_url = "https://drive.google.com/uc?export=download&id=1uinIey0wuHSO86TixUYWhkOL6Uf2j152"

print(f"Testing URL {test_url}")
fetch_file_info(manager, test_url)
print("Done")
