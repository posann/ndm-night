import ctypes
from ctypes import wintypes
import os
from utils.helpers import get_resource_path

# COM Classes for Shell Drag & Drop
class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_uint8 * 8)]

# COM Prototypes
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

shell32 = ctypes.windll.shell32
ole32   = ctypes.windll.ole32
user32  = ctypes.windll.user32

shell32.SHParseDisplayName.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), wintypes.ULONG, ctypes.POINTER(wintypes.ULONG)]
shell32.SHBindToParent.argtypes = [ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)]
shell32.ILFree.argtypes = [ctypes.c_void_p]

IID_IShellFolder = GUID(0x000214E6, 0, 0, (ctypes.c_uint8*8)(0xC0,0,0,0,0,0,0,0x46))
IID_IDataObject  = GUID(0x0000010e, 0, 0, (ctypes.c_uint8*8)(0xC0,0,0,0,0,0,0,0x46))
IID_IDropSource  = GUID(0x00000121, 0, 0, (ctypes.c_uint8*8)(0xC0,0,0,0,0,0,0,0x46))
IID_IUnknown      = GUID(0x00000000, 0, 0, (ctypes.c_uint8*8)(0xC0,0,0,0,0,0,0,0x46))
CLSID_DragDropHelper = GUID(0x4657278A,0x411B,0x11D2,(ctypes.c_uint8*8)(0x83,0x9A,0,0xC0,0x4F,0xD9,0x18,0xD0))
IID_IDragSourceHelper = GUID(0xDE5BF786,0x477A,0x11D2,(ctypes.c_uint8*8)(0x83,0x9D,0,0xC0,0x4F,0xD9,0x18,0xD0))

def start_shell_drag(manager):
    """Native Shell Drag implementation for Win32"""
    manager.log_event("Initiating Native Shell Drag...")
    try:
        manager._drag_refs = []
        ole32.OleInitialize(None)

        # ── Step 1: Get Shell IDataObject for folder ──
        ext_path = get_resource_path("extension")
        if not os.path.exists(ext_path):
            manager.log_event(f"Folder extension not found: {ext_path}", "ERROR")
            return

        pidl = ctypes.c_void_p()
        if shell32.SHParseDisplayName(ext_path, None, ctypes.byref(pidl), 0, None) != 0: return
        
        psf_parent = ctypes.c_void_p()
        pidl_rel   = ctypes.c_void_p()
        if shell32.SHBindToParent(pidl, ctypes.byref(IID_IShellFolder), ctypes.byref(psf_parent), ctypes.byref(pidl_rel)) != 0: return
        
        p_data_obj = ctypes.c_void_p()
        vtbl_parent = ctypes.cast(ctypes.cast(psf_parent, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(IShellFolderVtbl))
        hr = vtbl_parent.contents.GetUIObjectOf(psf_parent, None, 1, ctypes.byref(pidl_rel), ctypes.byref(IID_IDataObject), None, ctypes.byref(p_data_obj))
        if hr != 0 or not p_data_obj:
            shell32.ILFree(pidl)
            return

        # ── Step 2: Create our DropSource ──
        def wrap(func, proto):
            obj = proto(func)
            manager._drag_refs.append(obj)
            return obj

        def is_iid_equal(p_iid, target_iid):
            try:
                query = ctypes.cast(p_iid, ctypes.POINTER(GUID)).contents
                return (query.Data1 == target_iid.Data1 and query.Data2 == target_iid.Data2 and bytes(query.Data4) == bytes(target_iid.Data4))
            except: return False

        def DS_QI(this, p_iid, ppv):
            if is_iid_equal(p_iid, IID_IDropSource) or is_iid_equal(p_iid, IID_IUnknown):
                ctypes.cast(ppv, ctypes.POINTER(ctypes.c_void_p))[0] = this
                return 0
            ctypes.cast(ppv, ctypes.POINTER(ctypes.c_void_p))[0] = None
            return 0x80004002

        class IDropSourceVtbl(ctypes.Structure):
            _fields_ = [("QI", QI_PROTO), ("AR", AR_PROTO), ("RL", AR_PROTO), ("QCD", QCD_PROTO), ("GFB", GFB_PROTO)]
        class IDropSource(ctypes.Structure):
            _fields_ = [("lpVtbl", ctypes.POINTER(IDropSourceVtbl))]

        ds_vtbl = IDropSourceVtbl(wrap(DS_QI, QI_PROTO), wrap(lambda t: 1, AR_PROTO), wrap(lambda t: 1, AR_PROTO), 
                                  wrap(lambda t,fE,gK: 0x00040101 if fE else (0 if gK&1 else 0x00040100), QCD_PROTO), 
                                  wrap(lambda t,e: 0x00040102, GFB_PROTO))
        drop_source = IDropSource(ctypes.pointer(ds_vtbl))

        # ── Step 3: Add Ghost Image ──
        p_helper = ctypes.c_void_p()
        if ole32.CoCreateInstance(ctypes.byref(CLSID_DragDropHelper), None, 1, ctypes.byref(IID_IDragSourceHelper), ctypes.byref(p_helper)) == 0:
            vtbl_h = ctypes.cast(ctypes.cast(p_helper, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
            IFW_PROTO = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.HWND, ctypes.POINTER(wintypes.POINT), ctypes.c_void_p)
            fn_ifw = IFW_PROTO(vtbl_h[4])
            cur = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(cur))
            fn_ifw(p_helper.value, wintypes.HWND(manager.drag_card.winfo_id()), ctypes.byref(cur), p_data_obj)

        # ── Step 4: DoDragDrop ──
        user32.ReleaseCapture()
        dwEffect = wintypes.DWORD()
        ole32.DoDragDrop(p_data_obj, ctypes.byref(drop_source), 1 | 2, ctypes.byref(dwEffect))
        
        shell32.ILFree(pidl)
        manager._drag_refs = []
    except Exception as e:
        manager.log_event(f"Shell Drag Error: {e}", "ERROR")
