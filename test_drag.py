import os
import time
import ctypes
from ctypes import wintypes
import sys
import threading

shell32 = ctypes.windll.shell32
ole32   = ctypes.windll.ole32
user32  = ctypes.windll.user32

ole32.OleInitialize.restype = ctypes.c_long
ole32.CoCreateInstance.restype = ctypes.c_long
ole32.DoDragDrop.restype = ctypes.c_long

print(f"OleInitialize: {hex(ole32.OleInitialize(None) & 0xFFFFFFFF)}")

# ── Minimal COM Structs ──────────────────────────────────────────
class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_uint8 * 8)]

QI_PROTO = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
AR_PROTO = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)
QCD_PROTO = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_long, wintypes.DWORD)
GFB_PROTO = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.DWORD)
GUO_PROTO = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.HWND, wintypes.UINT, 
                               ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(GUID), 
                               ctypes.POINTER(wintypes.UINT), ctypes.POINTER(ctypes.c_void_p))

class IShellFolderVtbl(ctypes.Structure):
    _fields_ = [("QI", QI_PROTO), ("AR", AR_PROTO), ("RL", AR_PROTO),
                ("ParseDisplayName", ctypes.c_void_p), ("EnumObjects", ctypes.c_void_p),
                ("BindToObject", ctypes.c_void_p), ("BindToStorage", ctypes.c_void_p),
                ("CompareIDs", ctypes.c_void_p), ("CreateViewObject", ctypes.c_void_p),
                ("GetAttributesOf", ctypes.c_void_p), ("GetUIObjectOf", GUO_PROTO)]

shell32.SHParseDisplayName.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), wintypes.ULONG, ctypes.POINTER(wintypes.ULONG)]
shell32.SHBindToParent.argtypes = [ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)]
shell32.ILFree.argtypes = [ctypes.c_void_p]

IID_IShellFolder = GUID(0x000214E6, 0, 0, (ctypes.c_uint8*8)(0xC0,0,0,0,0,0,0,0x46))
IID_IDataObject  = GUID(0x0000010e, 0, 0, (ctypes.c_uint8*8)(0xC0,0,0,0,0,0,0,0x46))
IID_IDropSource  = GUID(0x00000121, 0, 0, (ctypes.c_uint8*8)(0xC0,0,0,0,0,0,0,0x46))
IID_IUnknown      = GUID(0x00000000, 0, 0, (ctypes.c_uint8*8)(0xC0,0,0,0,0,0,0,0x46))

ext_path = os.path.normpath(os.path.join(os.getcwd(), "extension"))
print(f"Path: {ext_path}")

pidl = ctypes.c_void_p()
hr = shell32.SHParseDisplayName(ext_path, None, ctypes.byref(pidl), 0, None)
print(f"SHParseDisplayName: {hex(hr & 0xFFFFFFFF)}")

psf_parent = ctypes.c_void_p()
pidl_rel   = ctypes.c_void_p()
hr = shell32.SHBindToParent(pidl, ctypes.byref(IID_IShellFolder), ctypes.byref(psf_parent), ctypes.byref(pidl_rel))
print(f"SHBindToParent: {hex(hr & 0xFFFFFFFF)}")

p_data_obj = ctypes.c_void_p()
vtbl_parent = ctypes.cast(ctypes.cast(psf_parent, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(IShellFolderVtbl))
hr = vtbl_parent.contents.GetUIObjectOf(psf_parent, None, 1, ctypes.byref(pidl_rel), ctypes.byref(IID_IDataObject), None, ctypes.byref(p_data_obj))
print(f"GetUIObjectOf: {hex(hr & 0xFFFFFFFF)}, p_data_obj: {p_data_obj.value}")

_drag_refs = []

def DS_QI(this, p_iid, ppv):
    # Just basic QI
    ctypes.cast(ppv, ctypes.POINTER(ctypes.c_void_p))[0] = this
    return 0
def wrap(f, p):
    ret = p(f)
    _drag_refs.append(ret)
    return ret

class IDropSourceVtbl(ctypes.Structure):
    _fields_ = [("QI", QI_PROTO), ("AR", AR_PROTO), ("RL", AR_PROTO),
                ("QCD", QCD_PROTO), ("GFB", GFB_PROTO)]
class IDropSource(ctypes.Structure):
    _fields_ = [("lpVtbl", ctypes.POINTER(IDropSourceVtbl))]

ds_vtbl = IDropSourceVtbl(
    wrap(DS_QI, QI_PROTO), wrap(lambda t: 1, AR_PROTO), wrap(lambda t: 1, AR_PROTO),
    wrap(lambda t,fE,gK: 0x00040101 if (fE != 0) else (0 if (gK & 1) else 0x00040100), QCD_PROTO),
    wrap(lambda t,e: 0x00040102, GFB_PROTO),
)
drop_source = IDropSource(ctypes.pointer(ds_vtbl))

print("About to start DoDragDrop. You have 5 seconds, move your mouse to where you want it.")

def drag_thread():
    time.sleep(2)
    print("DoDragDrop called from bg...")
    dwEffect = wintypes.DWORD()
    hr = ole32.DoDragDrop(p_data_obj, ctypes.byref(drop_source), 1 | 2, ctypes.byref(dwEffect))
    print(f"DoDragDrop finished: {hex(hr & 0xFFFFFFFF)}, effect: {dwEffect.value}")
    shell32.ILFree(pidl)
    import sys
    sys.exit(0)

threading.Thread(target=drag_thread).start()

# DoDragDrop needs a message loop. Wait...
try:
    while True:
        time.sleep(1)
        # In a real app the GUI is the message loop.
except KeyboardInterrupt:
    pass

