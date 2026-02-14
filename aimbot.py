"""
CS2 External — Aimbot + Triggerbot + RCS
==========================================
Ekran-tabanlı aimbot, triggerbot, RCS (geri tepme), Flick (kafa snap).
"""

import ctypes
import math
import struct
import time
from utils import mouse_move_relative

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004

# Açı -> fare hareketi (Source/CS2: sensitivity * 0.022 ≈ 1 derece başına hareket)
DEGREE_TO_MOUSE = 1.0 / 0.022


class Aimbot:
    """Ekran-tabanlı aimbot + triggerbot."""

    def __init__(self, config, memory):
        self.config = config
        self.memory = memory
        self._last_trigger = 0.0
        self._residue_x = 0.0
        self._residue_y = 0.0

    def _key(self, vk):
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)

    def update(self, players: list, local_player=None):
        # Store local player for RCS
        self.local_player = local_player
        
        if not self.memory.is_attached:
            return

        cfg = self.config
        cx = cfg.screen_width / 2.0
        cy = cfg.screen_height / 2.0
        fov_px = (cfg.aim_fov / 45.0) * (cfg.screen_width / 2.0)

        # ── Hedef filtreleme ──
        use_max_dist = getattr(cfg, "aim_max_distance_enabled", False)
        max_dist = getattr(cfg, "aim_max_distance", 80.0)
        targets = []
        for p in players:
            if cfg.aim_team_check and not p.is_enemy:
                continue
            if p.health <= 0 or p.pos == (0, 0, 0):
                continue
            if use_max_dist and p.distance > max_dist:
                continue
            targets.append(p)

        # ── En yakın hedef (pixel uzaklığı) ──
        best = None
        best_dist = 99999.0 # Start with large distance
        
        # We calculate specific FOV limits inside the loop/check phase
        # but for 'best' selection we usually want the closet to crosshair overall.
        
        # Auto-Focus modunda mesafe limiti (pixel değil, dünya koordinatı)
        # Ama burada sadece piksel olarak en yakını seçiyoruz.
        # Auto-Focus mantığı: Eğer oyuncu aim_auto_dist içindeyse,
        # FOV'a bakmaksızın listeye alacağız ve öncelik vereceğiz.

        # Search Radius Calculation
        search_fov = cfg.aim_fov
        if cfg.flick_enabled and cfg.flick_fov > search_fov:
            search_fov = cfg.flick_fov
            
        search_rad_px = (search_fov / 45.0) * (cfg.screen_width / 2.0)
        
        # Normal Aim FOV (for smooth aim)
        aim_fov_px = (cfg.aim_fov / 45.0) * (cfg.screen_width / 2.0)

        for p in targets:
            ax, ay = p.screen_aim
            dist_px = math.hypot(ax - cx, ay - cy)
            
            # Auto-Focus kontrolü
            is_auto_focused = False
            if cfg.aim_auto_focus and p.distance < cfg.aim_auto_dist:
                is_auto_focused = True
            
            # Eğer Search Radius içinde değilse VE Auto-Focus değilse atla
            if dist_px > search_rad_px and not is_auto_focused:
                continue
                
            # Önceliklendirme: Auto-focus olanlar her zaman daha "yakın" varsayılır
            # Bunu sağlamak için score'u manipüle edebiliriz veya direkt atarız.
            
            score = dist_px
            if is_auto_focused:
                score *= 0.1 # Çok daha düşük skor vererek öne geçiriyoruz
                
            if score < best_dist:
                best_dist = score
                best = p


        # ── Aimbot (Smooth) ──
        # Tabanca/yarı-otomatik: ateş (sol tık) basılıyken fare hareketi yapma; oyun her tıklamayı ayrı mermi olarak algılasın.
        VK_LBUTTON = 0x01
        firing = self._key(VK_LBUTTON)
        if cfg.aim_enabled and best is not None and self._key(cfg.aim_key) and not firing:
             ax, ay = best.screen_aim
             dist_to_crosshair = math.hypot(ax - cx, ay - cy)
             
             # Sadece aim_fov içindeyse smooth aim yap
             if dist_to_crosshair <= aim_fov_px:
                 dx = ax - cx
                 dy = ay - cy
                 
                 # Deadzone (titremeyi önler)
                 if abs(dx) >= 2.0 or abs(dy) >= 2.0:
                     smooth = max(1.0, cfg.aim_smoothness)
                     target_x = dx / smooth + self._residue_x
                     target_y = dy / smooth + self._residue_y
                     mx, my = int(target_x), int(target_y)
                     self._residue_x, self._residue_y = target_x - mx, target_y - my
                     if abs(mx) >= 1 or abs(my) >= 1:
                         mouse_move_relative(mx, my)
                 else:
                     self._residue_x = self._residue_y = 0.0

        # ── Flick (Kafa snap) ──
        # Flick FOV içinde kafaya en yakın düşmana hızlı snap; smooth < 1 = daha agresif.
        if cfg.flick_enabled and self._key(cfg.flick_key) and targets:
            flick_fov_px = (cfg.flick_fov / 45.0) * (cfg.screen_width / 2.0)
            best_flick = None
            best_head_dist = 99999.0
            for p in targets:
                if p.screen_head is None:
                    continue
                hx, hy = p.screen_head
                d = math.hypot(hx - cx, hy - cy)
                if d <= flick_fov_px and d < best_head_dist:
                    best_head_dist = d
                    best_flick = p
            if best_flick is not None and best_head_dist >= 2.0:
                ax, ay = best_flick.screen_head
                dx = ax - cx
                dy = ay - cy
                smooth = max(0.2, min(1.0, cfg.flick_smooth))
                step = 1.0 / smooth
                mx = int(dx * step)
                my = int(dy * step)
                if abs(mx) >= 1 or abs(my) >= 1:
                    mouse_move_relative(mx, my)

        # ── Triggerbot ──
        if cfg.trigger_enabled and best is not None:
            should_fire = False
            if cfg.trigger_auto:
                should_fire = self._crosshair_on(best, cx, cy)
            elif self._key(cfg.aim_key):
                should_fire = best_dist < fov_px * 0.15

            if should_fire:
                now = time.time()
                if now - self._last_trigger > cfg.trigger_delay_ms / 1000.0:
                    self._click()
                    self._last_trigger = now

        # ── RCS (Geri tepme kontrolü) ──
        if cfg.rcs_enabled and self.memory.is_attached:
            self._update_rcs()

    def _get_sensitivity(self):
        """Oyun hassasiyetini okur (RCS açı->piksel dönüşümü için)."""
        cfg = self.config
        client = self.memory.get_base("client.dll")
        if not client:
            return 1.0
        sens_base = cfg.client("dwSensitivity")
        sens_off = cfg.client("dwSensitivity_sensitivity")
        if not sens_base or not sens_off:
            return 1.0
        ptr = self.memory.read_ptr(client + sens_base)
        if not ptr:
            return 1.0
        s = self.memory.read_float(ptr + sens_off)
        return max(0.1, s) if s else 1.0

    def _update_rcs(self):
        if not self.local_player or not self.local_player.address:
            return
        mem = self.memory
        cfg = self.config
        pawn = self.local_player.address

        shots_off = cfg.netvar("C_CSPlayerPawn.m_iShotsFired")
        punch_off = cfg.netvar("C_CSPlayerPawn.m_aimPunchAngle")
        if not punch_off:
            return

        shots = mem.read_int(pawn + shots_off)
        if shots <= cfg.rcs_start_bullet:
            if hasattr(self, "_old_punch"):
                buff = mem.read_bytes(pawn + punch_off, 12)
                if buff and len(buff) >= 8:
                    pitch, yaw = struct.unpack("<ff", buff[:8])
                    self._old_punch = (pitch, yaw)
            return

        buff = mem.read_bytes(pawn + punch_off, 12)
        if not buff or len(buff) < 8:
            return
        pitch, yaw = struct.unpack("<ff", buff[:8])

        if not hasattr(self, "_old_punch"):
            self._old_punch = (pitch, yaw)
            return

        old_pitch, old_yaw = self._old_punch
        delta_pitch = pitch - old_pitch
        delta_yaw = yaw - old_yaw
        self._old_punch = (pitch, yaw)

        sens = self._get_sensitivity()
        scale = DEGREE_TO_MOUSE / sens
        move_y = delta_pitch * scale * cfg.rcs_scale_y
        move_x = -delta_yaw * scale * cfg.rcs_scale_x
        mx = int(move_x)
        my = int(move_y)
        if abs(mx) >= 1 or abs(my) >= 1:
            mouse_move_relative(mx, my)


    def _crosshair_on(self, player, cx, cy):
        if player.screen_pos is None or player.screen_head is None:
            return False
        sx, sy = player.screen_pos
        hx, hy = player.screen_head
        bh = abs(sy - hy)
        if bh < 5:
            return False
        bw = bh * 0.45
        return (hx - bw/2) <= cx <= (hx + bw/2) and hy <= cy <= sy

    def _click(self):
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.01)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
