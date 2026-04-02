import os
import sys
import subprocess
import shutil

# --- CONFIGURATION ---
APP_NAME = "NDM"
ENTRY_POINT = "app.py"
ICON_FILE = "ndm_logo.png"
EXTENSION_FOLDER = "extension"

def get_ctk_path():
    try:
        import customtkinter
        return os.path.dirname(customtkinter.__file__)
    except ImportError:
        print("Error: customtkinter not found. Install it first.")
        sys.exit(1)

def build(mode="portable"):
    ctk_path = get_ctk_path()
    print(f"CustomTkinter found at: {ctk_path}")
    
    # Base command
    cmd = [
        "py", "-m", "PyInstaller",
        "--noconfirm",
        "--windowed",
        f"--icon={ICON_FILE}",
        f"--add-data={ICON_FILE}{os.pathsep}.",
        f"--add-data={EXTENSION_FOLDER}{os.pathsep}{EXTENSION_FOLDER}",
        f"--add-data={ctk_path}{os.pathsep}customtkinter",
        "--name=" + (APP_NAME if mode == "installer" else APP_NAME + "-Portable"),
    ]
    
    if mode == "portable":
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")
        
    cmd.append(ENTRY_POINT)
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        build(sys.argv[1])
    else:
        print("Usage: python build_ndm.py [portable|installer]")
        print("Standard build starting: Portable...")
        build("portable")
        print("\nStandard build starting: Installer Source...")
        build("installer")
