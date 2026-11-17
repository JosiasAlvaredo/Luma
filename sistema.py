"""Pequeñas lecturas del sistema (solo Windows; en otros sistemas devuelven valores neutros)."""
import ctypes
import sys


def titulo_ventana_activa():
    if sys.platform != "win32":
        return ""
    try:
        u = ctypes.windll.user32
        h = u.GetForegroundWindow()
        n = u.GetWindowTextLengthW(h)
        if n <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, buf, n + 1)
        return buf.value[:120]
    except Exception:
        return ""


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def segundos_inactivo():
    """Segundos desde el último movimiento de mouse/teclado."""
    if sys.platform != "win32":
        return 0.0
    try:
        li = _LASTINPUTINFO()
        li.cbSize = ctypes.sizeof(li)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li))
        ctypes.windll.kernel32.GetTickCount.restype = ctypes.c_uint
        return ((ctypes.windll.kernel32.GetTickCount() - li.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:
        return 0.0
