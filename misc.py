"""
CS2 External — Misc Modülü
============================
Bhop, Spinbot (mevlana), Oyun/Viewmodel FOV.
"""

import ctypes
import struct
import time

VK_SPACE = 0x20
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP    = 0x0002
FL_ONGROUND = (1 << 0)

user32 = ctypes.windll.user32

ENTITY_STRIDE = 0x70


class Misc:
    """Bhop, Spinbot, FOV yöneticisi."""

    def __init__(self, config, memory):
        self.config = config
        self.memory = memory
        self._spin_angle = 0.0
        self._tp_was_enabled = False
        self._tp_key_down = False

    def update(self):
        """Her tick — tüm misc özelliklerini çalıştırır."""
        if not self.memory.is_attached:
            return

        if self.config.bhop_enabled:
            self._bhop()

        if self.config.spin_enabled:
            self._spinbot()

        self._no_flash()
        self._triggerbot()

        self._game_fov()
        self._viewmodel_fov()

    # ──────────────────────────────────
    #  Bhop
    # ──────────────────────────────────

    def _bhop(self):
        if not (user32.GetAsyncKeyState(self.config.bhop_key) & 0x8000):
            return

        mem = self.memory
        cfg = self.config
        client = mem.get_base("client.dll")
        if not client:
            return

        pawn = mem.read_ptr(client + cfg.client("dwLocalPlayerPawn"))
        if not pawn:
            return

        flags = mem.read_uint(pawn + cfg.netvar("C_BaseEntity.m_fFlags"))
        if flags & FL_ONGROUND:
            self._key_up(VK_SPACE)
            time.sleep(0.008)
            self._key_down(VK_SPACE)

    # ──────────────────────────────────
    #  Spinbot (Mevlana - Anti-Aim)
    #  Kamerayı DEĞİŞTİRMEZ, sadece
    #  sunucuya giden açıyı değiştirir.
    # ──────────────────────────────────

    def _spinbot(self):
        """
        Save → spin → restore yöntemi.
        Mevcut açıyı kaydeder, spin açısı yazar, ardından eski açıyı geri yükler.
        Sonuç: sunucu spin açısını alır ama kamera yerinde kalır.
        """
        if not (user32.GetAsyncKeyState(self.config.spin_key) & 0x8000):
            return

        cfg = self.config
        mem = self.memory
        
        # Eğer ateş ediyorsan veya aim alıyorsan ve ayar açıksa, spin atma
        if cfg.spin_check_shoot:
            # VK_LBUTTON = 0x01
            if (user32.GetAsyncKeyState(0x01) & 0x8000) or (user32.GetAsyncKeyState(cfg.aim_key) & 0x8000):
                return
        client = mem.get_base("client.dll")
        if not client:
            return

        va_addr = client + cfg.client("dwViewAngles")

        # 1) Mevcut açıları oku ve kaydet
        original = mem.read_bytes(va_addr, 12)
        if not original:
            return

        pitch, yaw, roll = struct.unpack('<3f', original)

        # 2) Spin açısı hesapla
        self._spin_angle += cfg.spin_speed
        if self._spin_angle > 180.0:
            self._spin_angle -= 360.0

        # 3) Spin açısını yaz (bu tick'te sunucu bunu alır)
        spin_data = struct.pack('<3f', pitch, self._spin_angle, roll)
        mem.write_bytes(va_addr, spin_data)

        # 4) Kısa gecikme — sunucu bu tick'i yakalaması için
        # External silent aim için kritik. Çok kısa bir bekleme (1-2ms) yeterlidir.
        # Kullanici istegi uzerine "kamera donmesin" dendi, sleep kaldiriliyor.
        # Bu durumda sunucu spini gormeyebilir ama client view stabil kalir (flicker azalir).
        # time.sleep(0.002)

        # 5) Orijinal açıları geri yükle (kamera yerinde kalır)
        mem.write_bytes(va_addr, original)

        # 5) Orijinal açıları geri yükle (kamera yerinde kalır)
        mem.write_bytes(va_addr, original)

    # ──────────────────────────────────
    #  No Flash
    # ──────────────────────────────────

    def _no_flash(self):
        """Körlüğü kaldırır (FlashDuration = 0)."""
        if not getattr(self.config, 'no_flash_enabled', False):
            return

        mem = self.memory
        cfg = self.config
        client = mem.get_base("client.dll")
        if not client: return

        pawn = mem.read_ptr(client + cfg.client("dwLocalPlayerPawn"))
        if not pawn: return

        # Flash süresini oku, 0 değilse 0 yap
        # m_flFlashDuration: 5624 (default), config'den al
        curr_val = mem.read_float(pawn + cfg.m_flFlashDuration)
        if curr_val > 0.0:
            mem.write_float(pawn + cfg.m_flFlashDuration, 0.0)

    # ──────────────────────────────────
    #  Triggerbot
    # ──────────────────────────────────

    def _triggerbot(self):
        """Crosshair üzerindeki düşmana otomatik ateş eder."""
        if not getattr(self.config, 'trigger_enabled', False):
            return

        # Tuş kontrolü (Auto değilse)
        if not self.config.trigger_auto:
            # varsayılan VK_MENU (Alt) ya da config
            key = getattr(self.config, 'trigger_key', 0x12) # VK_ALT default
            if not (user32.GetAsyncKeyState(key) & 0x8000):
                return

        mem = self.memory
        cfg = self.config
        client = mem.get_base("client.dll")
        if not client: return

        local_pawn = mem.read_ptr(client + cfg.client("dwLocalPlayerPawn"))
        if not local_pawn: return

        # Crosshair ID
        ent_idx = mem.read_int(local_pawn + cfg.netvar("C_CSPlayerPawn.m_iIDEntIndex"))
        if ent_idx <= 0:
            return

        # Entity List'ten pawn bul
        ent_list = mem.read_ptr(client + cfg.client("dwEntityList"))
        if not ent_list: return

        # entry = list + 8 * (idx >> 9) + 16
        chunk = mem.read_ptr(ent_list + 8 * (ent_idx >> 9) + 16)
        if not chunk: return

        # pawn = chunk + 120 * (idx & 0x1FF)
        # Genelde 0x78 (120) stride
        target_pawn = mem.read_ptr(chunk + 120 * (ent_idx & 0x1FF))
        if not target_pawn or target_pawn == local_pawn:
            return

        # Takım kontrolü
        local_team = mem.read_int(local_pawn + cfg.netvar("C_BaseEntity.m_iTeamNum"))
        target_team = mem.read_int(target_pawn + cfg.netvar("C_BaseEntity.m_iTeamNum"))

        if local_team == target_team and local_team != 0:
            return # Dost ateşi yok
            
        # Canlı mı?
        hp = mem.read_int(target_pawn + cfg.netvar("C_BaseEntity.m_iHealth"))
        if hp <= 0:
            return

        # Ateş et
        time.sleep(getattr(cfg, 'trigger_delay_ms', 0) / 1000.0)
        user32.mouse_event(0x0002, 0, 0, 0, 0) # MOUSEEVENTF_LEFTDOWN
        time.sleep(0.01)
        user32.mouse_event(0x0004, 0, 0, 0, 0) # MOUSEEVENTF_LEFTUP

    # ──────────────────────────────────
    #  Oyun FOV (görüş açısı)

    # ──────────────────────────────────

    def _game_fov(self):
        """Oyuncu FOV değerini yazar (CBasePlayerController.m_iDesiredFOV)."""
        if not getattr(self.config, 'game_fov_enabled', False):
            return
        fov = getattr(self.config, 'game_fov_value', 0)
        if fov < 60 or fov > 140:
            return
        mem = self.memory
        cfg = self.config
        client = mem.get_base("client.dll")
        if not client:
            return
        controller = mem.read_ptr(client + cfg.client("dwLocalPlayerController"))
        if not controller:
            return
        offset = cfg.netvar("CBasePlayerController.m_iDesiredFOV")
        if offset:
            mem.write_int(controller + offset, fov)

    # ──────────────────────────────────
    #  Viewmodel FOV (el/silah görüş açısı)
    # ──────────────────────────────────

    def _viewmodel_fov(self):
        """El/silah FOV: Local pawn + m_flViewmodelFOV. Birden fazla offset denenir (client build farkı)."""
        if not getattr(self.config, "viewmodel_fov_enabled", False):
            return
        fov = float(getattr(self.config, "viewmodel_fov_value", 68))
        if fov < 54 or fov > 120:
            return
        mem = self.memory
        cfg = self.config
        client = mem.get_base("client.dll")
        if not client:
            return
        local_pawn = mem.read_ptr(client + cfg.client("dwLocalPlayerPawn"))
        if not local_pawn:
            return
        offsets = getattr(cfg, "_viewmodel_fov_offsets", None) or [getattr(cfg, "m_flViewmodelFOV", 9252), 9252]
        
        # 1. Try writing to Pawn directly (m_flViewmodelFOV)
        for off in offsets:
            if off and isinstance(off, (int, float)):
                mem.write_float(local_pawn + int(off), fov)

        # 2. Reverse Lookup Strategy: Find entities that own the Pawn (Viewmodel/Weapon)
        # Because m_hViewModel is unreliable, we find the Viewmodel by its Owner Handle.
        
        # Get Local Pawn Handle from Controller
        # We need to find the controller first.
        # dwLocalPlayerController points to the controller address.
        controller = mem.read_ptr(client + cfg.client("dwLocalPlayerController"))
        if controller:
            h_pawn = mem.read_uint(controller + getattr(cfg, "m_hPlayerPawn", 2316))
            if h_pawn and h_pawn != 0xFFFFFFFF:
                # Scan first 64 entities (Players/Weapons/Viewmodels often low index)
                # We look for entities where m_hOwner == h_pawn
                # Offsets found by scan: 0x10 and 0x160
                
                entity_list = mem.read_ptr(client + cfg.client("dwEntityList"))
                if entity_list:
                    # We only check first chunk (0-512) for speed
                    list_entry = mem.read_ptr(entity_list + 0x10)
                    if list_entry:
                        for i in range(1, 64): # Check first 64 indices
                            ent_ptr = mem.read_ptr(list_entry + 120 * i)
                            if not ent_ptr: continue
                            
                            # Check ownership
                            # We check 0x10 and 0x160
                            # Also 0x148 (common for m_hOwnerEntity)
                            owner_candidates = [0x10, 0x160, 0x148]
                            is_owned = False
                            for off in owner_candidates:
                                try:
                                    val = mem.read_uint(ent_ptr + off)
                                    if val == h_pawn:
                                        is_owned = True
                                        break
                                except: pass
                            
                            if is_owned:
                                # This entity belongs to us. Write FOV.
                                mem.write_float(ent_ptr + getattr(cfg, "m_flViewmodelFOV", 9252), fov)

        # 3. Fallback: Try writing to ViewModel entity via m_pViewModelServices (Original method)
        # ... (Left as backup)
        h_vm = None
        
        # Try direct handle offset first (most reliable found)
        direct_off = getattr(cfg, "viewmodel_handle_offset", 0x3ECC)
        if direct_off:
            h_vm = mem.read_uint(local_pawn + direct_off)
            
        # Fallback to services
        if not h_vm or h_vm == 0xFFFFFFFF:
             vm_services = mem.read_ptr(local_pawn + getattr(cfg, "m_pViewModelServices", 0x1308))
             if vm_services:
                 h_vm = mem.read_uint(vm_services + getattr(cfg, "m_hViewModel", 0x40))
        
        if h_vm and h_vm != 0xFFFFFFFF:
            # Handle to Entity Index
            vm_idx = h_vm & 0x7FFF
            # Get Entity from List
            entity_list = mem.read_ptr(client + cfg.client("dwEntityList"))
            if entity_list:
                 # Logic for CConcreteEntityList / GameEntitySystem
                 # List entry logic:
                 list_entry = mem.read_ptr(entity_list + 0x10 + 8 * ((vm_idx & 0x7FFF) >> 9))
                 if list_entry:
                     vm_pawn = mem.read_ptr(list_entry + 120 * (vm_idx & 0x1FF))
                     if vm_pawn:
                         mem.write_float(vm_pawn + getattr(cfg, "m_flViewmodelFOV", 9252), fov)

    # ──────────────────────────────────
    #  Tuş simülasyonu
    # ──────────────────────────────────

    def _key_down(self, vk):
        sc = user32.MapVirtualKeyW(vk, 0)
        user32.keybd_event(vk, sc, KEYEVENTF_SCANCODE, 0)

    def _key_up(self, vk):
        sc = user32.MapVirtualKeyW(vk, 0)
        user32.keybd_event(vk, sc, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0)
