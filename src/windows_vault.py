"""
maccre_core/orchestration/windows_vault.py
============================================
Zero-dependency, ctypes-native interface to the Windows Credential Manager.

No PyPI packages required. Reads secrets directly from advapi32.dll,
eliminating supply-chain risk from third-party vault libraries.
"""
import ctypes
from ctypes import wintypes
from typing import Optional


class _FILETIME(ctypes.Structure):
    _fields_ = [
        ('dwLowDateTime', wintypes.DWORD),
        ('dwHighDateTime', wintypes.DWORD),
    ]


class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ('flags', wintypes.DWORD),
        ('type', wintypes.DWORD),
        ('target_name', wintypes.LPWSTR),
        ('comment', wintypes.LPWSTR),
        ('last_written', _FILETIME),
        ('credential_blob_size', wintypes.DWORD),
        ('credential_blob', ctypes.POINTER(ctypes.c_char)),
        ('persist', wintypes.DWORD),
        ('attribute_count', wintypes.DWORD),
        ('attributes', ctypes.c_void_p),
        ('target_alias', wintypes.LPWSTR),
        ('user_name', wintypes.LPWSTR),
    ]


def get_native_credential(target_name: str) -> Optional[str]:
    """Reads a credential directly from the Windows OS Vault via advapi32.dll.

    Args:
        target_name: The credential target name as stored in Windows Credential Manager.

    Returns:
        The credential secret as a string, or None if not found.
    """
    advapi32 = ctypes.WinDLL('advapi32.dll')
    CredRead = advapi32.CredReadW
    CredRead.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
    CredRead.restype = wintypes.BOOL
    CredFree = advapi32.CredFree
    CredFree.argtypes = [ctypes.c_void_p]

    cred_ptr = ctypes.POINTER(CREDENTIAL)()
    if CredRead(target_name, 1, 0, ctypes.byref(cred_ptr)):
        try:
            blob_size = cred_ptr.contents.credential_blob_size
            blob_bytes = ctypes.string_at(cred_ptr.contents.credential_blob, blob_size)
            return blob_bytes.decode('utf-16-le')
        finally:
            CredFree(cred_ptr)
    return None
