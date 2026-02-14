"""
CS2 External — Memory Utility Module
======================================
Windows process memory okuma/yazma, modül bulma, world-to-screen
dönüşümü ve fare kontrolü fonksiyonlarını içerir.
"""

import ctypes
import math
import struct
import sys
from ctypes import wintypes

# ──────────────────────────────────────────────
#  Platform kontrolü
# ──────────────────────────────────────────────
if sys.platform != "win32":
    raise RuntimeError("Bu script yalnızca Windows üzerinde çalışır.")

# ──────────────────────────────────────────────
#  Windows API tanımları
# ──────────────────────────────────────────────
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]

kernel32.WriteProcessMemory.restype = wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [
    wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]

kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

kernel32.GetExitCodeProcess.restype = wintypes.BOOL
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]

psapi = ctypes.WinDLL('psapi', use_last_error=True)

psapi.EnumProcesses.restype = wintypes.BOOL
psapi.EnumProcesses.argtypes = [
    ctypes.POINTER(wintypes.DWORD), wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD)
]

psapi.EnumProcessModulesEx.restype = wintypes.BOOL
psapi.EnumProcessModulesEx.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), wintypes.DWORD
]

psapi.GetModuleBaseNameW.restype = wintypes.DWORD
psapi.GetModuleBaseNameW.argtypes = [
    wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD
]

user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.mouse_event.restype = None
user32.mouse_event.argtypes = [
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.DWORD, ctypes.c_ulong
]

# ── Sabitler ──
PROCESS_ALL_ACCESS = 0x1F0FFF
LIST_MODULES_ALL   = 0x03
MOUSEEVENTF_MOVE   = 0x0001
STILL_ACTIVE       = 259
MAX_PROCESSES = 2048
MAX_MODULES   = 1024
MAX_PATH      = 260


# ──────────────────────────────────────────────
#  İşlem bulma
# ──────────────────────────────────────────────

def find_process_id(process_name: str) -> int:
    """İsme göre çalışan bir işlemin PID'sini bulur."""
    processes = (wintypes.DWORD * MAX_PROCESSES)()
    cb_needed = wintypes.DWORD()
    if not psapi.EnumProcesses(processes, ctypes.sizeof(processes), ctypes.byref(cb_needed)):
        return 0

    count = min(cb_needed.value // ctypes.sizeof(wintypes.DWORD), MAX_PROCESSES)
    target = process_name.lower()

    for i in range(count):
        pid = processes[i]
        if pid == 0:
            continue
        h = kernel32.OpenProcess(0x0410, False, pid)  # QUERY_INFO | VM_READ
        if not h:
            continue
        try:
            mods = (wintypes.HMODULE * 1)()
            cb = wintypes.DWORD()
            if psapi.EnumProcessModulesEx(h, mods, ctypes.sizeof(mods), ctypes.byref(cb), LIST_MODULES_ALL):
                name_buf = ctypes.create_unicode_buffer(MAX_PATH)
                if psapi.GetModuleBaseNameW(h, mods[0], name_buf, MAX_PATH):
                    if name_buf.value.lower() == target:
                        return pid
        finally:
            kernel32.CloseHandle(h)
    return 0


# ──────────────────────────────────────────────
#  Memory sınıfı
# ──────────────────────────────────────────────

class Memory:
    """Hedef işlemin belleğine güvenli okuma/yazma erişimi sağlar."""

    def __init__(self, process_name: str):
        self.process_name = process_name
        self.handle = None
        self.pid = 0
        self.module_bases = {}  # {"client.dll": 0x...}

    @property
    def is_attached(self) -> bool:
        return self.handle is not None and self.handle != 0

    def attach(self) -> bool:
        """Hedef işleme bağlan."""
        self.pid = find_process_id(self.process_name)
        if self.pid == 0:
            return False

        self.handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, self.pid)
        if not self.handle:
            return False

        # Gerekli modüllerin bazlarını bul
        for mod_name in ["client.dll", "engine2.dll"]:
            base = self._get_module_base(mod_name)
            if base:
                self.module_bases[mod_name] = base

        return True

    def detach(self):
        """İşlem handle'ını kapat."""
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None
            self.pid = 0

    def is_process_running(self) -> bool:
        """Hedef işlemin hâlâ çalışıp çalışmadığını kontrol eder (oyun kapanınca çökme önlenir)."""
        if not self.handle or self.handle == 0:
            return False
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(self.handle, ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE

    def _get_module_base(self, module_name: str) -> int:
        """Belirtilen DLL'in taban adresini bulur."""
        if not self.handle:
            return 0
        mods = (wintypes.HMODULE * MAX_MODULES)()
        cb = wintypes.DWORD()
        if not psapi.EnumProcessModulesEx(self.handle, mods, ctypes.sizeof(mods),
                                          ctypes.byref(cb), LIST_MODULES_ALL):
            return 0
        num = min(cb.value // ctypes.sizeof(wintypes.HMODULE), MAX_MODULES)
        target = module_name.lower()
        for i in range(num):
            name_buf = ctypes.create_unicode_buffer(MAX_PATH)
            if psapi.GetModuleBaseNameW(self.handle, mods[i], name_buf, MAX_PATH):
                if name_buf.value.lower() == target:
                    return mods[i]
        return 0

    def get_base(self, module_name: str) -> int:
        """Önbelleklenmiş modül bazını döndürür."""
        return self.module_bases.get(module_name, 0)

    # ── Okuma fonksiyonları ──

    def read_bytes(self, address: int, size: int) -> bytes | None:
        if not self.handle or address == 0 or size <= 0:
            return None
        buf = ctypes.create_string_buffer(size)
        br = ctypes.c_size_t()
        if not kernel32.ReadProcessMemory(self.handle, address, buf, size, ctypes.byref(br)):
            return None
        return buf.raw

    def read_int(self, address: int) -> int:
        data = self.read_bytes(address, 4)
        return int.from_bytes(data, 'little', signed=True) if data else 0

    def read_uint(self, address: int) -> int:
        data = self.read_bytes(address, 4)
        return int.from_bytes(data, 'little', signed=False) if data else 0

    def read_long(self, address: int) -> int:
        data = self.read_bytes(address, 8)
        return int.from_bytes(data, 'little', signed=False) if data else 0

    def read_float(self, address: int) -> float:
        data = self.read_bytes(address, 4)
        return struct.unpack('<f', data)[0] if data else 0.0

    def read_bool(self, address: int) -> bool:
        data = self.read_bytes(address, 1)
        return bool(data[0]) if data else False

    def read_ptr(self, address: int) -> int:
        """8-byte pointer (64-bit)."""
        return self.read_long(address)

    def read_vec3(self, address: int) -> tuple:
        """3 float (x, y, z) okur ve tuple döndürür."""
        data = self.read_bytes(address, 12)
        if data is None:
            return (0.0, 0.0, 0.0)
        return struct.unpack('<3f', data)

    def read_view_matrix(self, address: int) -> list | None:
        """4x4 float matris (16 float) okur."""
        data = self.read_bytes(address, 64)  # 16 * 4 bytes
        if data is None:
            return None
        return list(struct.unpack('<16f', data))

    def read_string(self, address: int, max_len: int = 128) -> str:
        """Null-terminated string okur."""
        data = self.read_bytes(address, max_len)
        if data is None:
            return ""
        try:
            return data.split(b'\x00')[0].decode('utf-8', errors='replace')
        except Exception:
            return ""

    # ── Yazma fonksiyonları ──

    def write_bytes(self, address: int, data: bytes) -> bool:
        if not self.handle or address == 0:
            return False
        written = ctypes.c_size_t()
        return bool(kernel32.WriteProcessMemory(
            self.handle, address, data, len(data), ctypes.byref(written)
        ))

    def write_int(self, address: int, value: int) -> bool:
        return self.write_bytes(address, value.to_bytes(4, 'little', signed=True))

    def write_float(self, address: int, value: float) -> bool:
        return self.write_bytes(address, struct.pack('<f', value))


# ──────────────────────────────────────────────
#  World-to-Screen
# ──────────────────────────────────────────────

def get_screen_resolution() -> tuple:
    """Windows ekran çözünürlüğünü otomatik algılar."""
    w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
    h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
    return (w, h)


def get_game_window_rect() -> tuple | None:
    """CS2 oyun penceresinin konumunu ve boyutunu döndürür."""
    hwnd = user32.FindWindowW(None, "Counter-Strike 2")
    if not hwnd:
        return None
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    point = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    return (point.x, point.y, rect.right, rect.bottom)


def focus_game_window() -> bool:
    """CS2 penceresini öne getirir (Input sorunu için)."""
    hwnd = user32.FindWindowW(None, "Counter-Strike 2")
    if hwnd:
        user32.SetForegroundWindow(hwnd)
        return True
    return False


# FindWindowW, GetClientRect, ClientToScreen argtypes
user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.GetClientRect.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetSystemMetrics.argtypes = [ctypes.c_int]


def world_to_screen(pos: tuple, matrix: list, screen_w: int, screen_h: int) -> tuple | None:
    """
    3D dünya koordinatlarını 2D ekran koordinatlarına dönüştürür.
    CS2 ViewMatrix ROW-MAJOR formatındadır.

    Returns:
        (screen_x, screen_y) veya None (ekran dışıysa)
    """
    if matrix is None or len(matrix) < 16:
        return None

    x, y, z = pos

    # Row-major matris erişimi (CS2 VMatrix formatı)
    # Row 3 = perspective divide (W)
    clip_w = matrix[12] * x + matrix[13] * y + matrix[14] * z + matrix[15]

    if clip_w < 0.001:
        return None  # Kamera arkasında

    # Row 0 = screen X, Row 1 = screen Y
    clip_x = matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3]
    clip_y = matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7]

    # Ekran koordinatları
    inv_w = 1.0 / clip_w
    sx = (screen_w / 2.0) * (1.0 + clip_x * inv_w)
    sy = (screen_h / 2.0) * (1.0 - clip_y * inv_w)

    # Ekran sınırları kontrolü (sıkı)
    if sx < -50 or sx > screen_w + 50 or sy < -50 or sy > screen_h + 50:
        return None

    return (sx, sy)


# ──────────────────────────────────────────────
#  Açı hesaplama
# ──────────────────────────────────────────────

def calculate_angle(local_pos: tuple, target_pos: tuple) -> tuple:
    """
    Yerel oyuncudan hedefe olan mutlak açıları (pitch, yaw) hesaplar.

    Returns:
        (pitch, yaw) derece cinsinden
    """
    dx = target_pos[0] - local_pos[0]
    dy = target_pos[1] - local_pos[1]
    dz = target_pos[2] - local_pos[2]

    dist_2d = math.hypot(dx, dy)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = -math.degrees(math.atan2(dz, dist_2d)) if dist_2d > 0.001 else 0.0

    return (pitch, yaw)


def normalize_angle(angle: float) -> float:
    """Açıyı -180..180 aralığına normalize eder."""
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle


def angle_fov_distance(current_pitch: float, current_yaw: float,
                       target_pitch: float, target_yaw: float) -> float:
    """İki açı arasındaki FOV mesafesini hesaplar (derece)."""
    dp = target_pitch - current_pitch
    dy = normalize_angle(target_yaw - current_yaw)
    return math.hypot(dp, dy)


def mouse_move_relative(dx: int, dy: int):
    """Fare imlecini bağıl olarak hareket ettirir."""
    user32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)
