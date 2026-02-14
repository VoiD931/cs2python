"""
CS2 External — Neon Modern GUI (Violet Glow)
=============================================
"""

import sys
import time
import math
import ctypes
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QFrame, QListWidget, QStackedWidget,
    QGraphicsDropShadowEffect, QListWidgetItem, QCheckBox, QColorDialog, QScrollArea,
    QSizePolicy, QComboBox, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, QPoint, QRect, QRectF, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QLinearGradient, QIcon, QRadialGradient, QBrush

from config import Config
from utils import Memory, get_game_window_rect, focus_game_window
from esp import ESP
from aimbot import Aimbot
from misc import Misc


# ═══════════════════════════════════════════
#  ESP Overlay (Preserved)
# ═══════════════════════════════════════════
class OverlayWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.players = []
        self._frame_count = 0
        self._fps = 0
        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(1000)
        self.setWindowTitle("Overlay")
        self.setGeometry(0, 0, config.screen_width, config.screen_height)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
            Qt.Tool | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Click-through & Layered
        hwnd = int(self.winId())
        s = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, s | 0x80000 | 0x20)
        
        # OBS Bypass
        if self.config.obs_bypass:
            try:
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000011)  # WDA_EXCLUDEFROMCAPTURE
            except Exception:
                pass

    def sync_to_game(self):
        r = get_game_window_rect()
        if r:
            self.setGeometry(r[0], r[1], r[2], r[3])
            self.config.screen_width = r[2]
            self.config.screen_height = r[3]
    
    def update_players(self, p):
        self.players = p
        self.update()

    def _update_fps(self):
        self._fps = self._frame_count
        self._frame_count = 0

    def paintEvent(self, e):
        self._frame_count += 1
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        c = self.config
        cx, cy = c.screen_width / 2.0, c.screen_height / 2.0
        
        # FOV Circle
        # Draw Main FOV
        if self.config.aim_enabled and self.config.aim_fov_circle:
             p.setPen(QColor(*self.config.aim_fov_color, 255))
             p.setBrush(Qt.NoBrush)
             radius = math.tan(math.radians(self.config.aim_fov) / 2) * self.config.screen_width
             p.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        # Draw Flick FOV (Cyan)
        if self.config.flick_enabled:
             p.setPen(QColor(0, 255, 255, 200)) # Cyan, slightly transparent
             p.setBrush(Qt.NoBrush)
             radius_flick = math.tan(math.radians(self.config.flick_fov) / 2) * self.config.screen_width
             p.drawEllipse(int(cx - radius_flick), int(cy - radius_flick), int(radius_flick * 2), int(radius_flick * 2))

        # ── Radar (2D üstten) ──
        if getattr(c, "esp_radar", False) and getattr(c, "local_position", None):
            self._draw_radar(p, c)
        # ── ESP Loop ──
        if c.esp_enabled:
            for pl in self.players:
                self._dp(p, pl, c)
        # ── Özel nişangah ──
        style = getattr(c, "crosshair_style", 0)
        size = getattr(c, "crosshair_size", 6)
        gap = getattr(c, "crosshair_gap", 2)
        p.setPen(QPen(QColor(255, 255, 255, 220), 2))
        p.setBrush(Qt.NoBrush)
        if style == 1:
            p.drawEllipse(int(cx - size), int(cy - size), size * 2, size * 2)
        elif style == 2:
            p.drawEllipse(int(cx - size * 2), int(cy - size * 2), size * 4, size * 4)
        else:
            p.drawLine(int(cx - size - gap), int(cy), int(cx - gap), int(cy))
            p.drawLine(int(cx + gap), int(cy), int(cx + size + gap), int(cy))
            p.drawLine(int(cx), int(cy - size - gap), int(cx), int(cy - gap))
            p.drawLine(int(cx), int(cy + gap), int(cx), int(cy + size + gap))
        # ── FPS / Düşman sayısı ──
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lines = []
        if getattr(c, "overlay_show_fps", False):
            lines.append(f"FPS: {self._fps}")
        if getattr(c, "overlay_show_enemy_count", False):
            enemies = sum(1 for pl in self.players if pl.is_enemy)
            lines.append(f"Düşman: {enemies}")
        if lines:
            p.setPen(QColor(0, 0, 0, 200))
            p.drawText(12, 22, "  |  ".join(lines))
            p.setPen(QColor(139, 92, 246, 255))
            p.drawText(11, 21, "  |  ".join(lines))
        # ── Bomba kalan süre ──
        if getattr(c, "esp_bomb_timer", True) and getattr(c, "bomb_ticking", False):
            sec = max(0, getattr(c, "bomb_remaining_sec", 0))
            m = int(sec // 60)
            s = int(sec % 60)
            bomb_text = f"C4: {m}:{s:02d}"
            bx, by = c.screen_width - 90, 28
            p.setFont(QFont("Segoe UI", 12, QFont.Bold))
            p.setPen(QColor(0, 0, 0, 220))
            p.drawText(bx + 1, by + 1, bomb_text)
            p.setPen(QColor(255, 80, 80, 255))
            p.drawText(bx, by, bomb_text)
        p.end()

    def _draw_radar(self, p, c):
        local = c.local_position
        if not local or len(local) < 2:
            return
        radius = max(40, min(120, getattr(c, "radar_radius", 65)))
        scale = getattr(c, "radar_scale", 0.028)
        cx = 24 + radius
        cy = 24 + radius
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 180))
        p.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))
        p.setPen(QPen(QColor(139, 92, 246, 200), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))
        p.setPen(Qt.NoPen)
        for pl in self.players:
            dx = (pl.pos[0] - local[0]) * scale if len(pl.pos) >= 1 else 0
            dy = (pl.pos[1] - local[1]) * scale if len(pl.pos) >= 2 else 0
            px = cx + dx
            py = cy - dy
            if (px - cx) ** 2 + (py - cy) ** 2 > radius ** 2:
                ang = math.atan2(py - cy, px - cx)
                px = cx + radius * math.cos(ang)
                py = cy + radius * math.sin(ang)
            dot_r = 4
            if pl.is_enemy:
                p.setBrush(QColor(255, 60, 60, 240))
            else:
                p.setBrush(QColor(60, 120, 255, 240))
            p.drawEllipse(int(px - dot_r), int(py - dot_r), dot_r * 2, dot_r * 2)
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawEllipse(int(cx - 3), int(cy - 3), 6, 6)

    def _dp(self, p, pl, c):
        if pl.screen_pos is None or pl.screen_head is None:
            return
        
        sx, sy = pl.screen_pos
        hx, hy = pl.screen_head
        bh = abs(sy - hy)
        if bh < 8: return
        bw = bh * 0.45
        x1, y1 = hx - bw/2, hy
        
        col = QColor(80, 180, 255, 180) if not pl.is_enemy else (
            QColor(255, 220, 50, 220) if pl.is_visible else QColor(255, 55, 55, 200))
            
        if c.esp_snaplines and pl.screen_pos:
            sx, sy = pl.screen_pos
            lc = QColor(255, 50, 50, 150) if pl.is_enemy else QColor(50, 100, 255, 100)
            p.setPen(QPen(lc, 1.0, Qt.DashLine))
            p.drawLine(int(c.screen_width / 2), int(c.screen_height), int(sx), int(sy))

        if c.esp_box:
            cl = max(8, bh * 0.2)
            p.setPen(QPen(QColor(0,0,0,160), 3))
            self._cr(p, x1, y1, bw, bh, cl)
            p.setPen(QPen(col, 1.5))
            self._cr(p, x1, y1, bw, bh, cl)
            
        if c.esp_health_bar:
            bx = int(x1) - 7
            by, barh = int(y1), int(bh)
            hp = max(0, min(1, pl.health/100.0))
            fh = int(barh * hp)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0,0,0,160))
            p.drawRoundedRect(bx-1, by-1, 5, barh+2, 1, 1)
            g = QLinearGradient(0, by+barh, 0, by+barh-fh)
            if hp > .5:
                g.setColorAt(0, QColor(80,255,80)); g.setColorAt(1, QColor(180,255,80))
            elif hp > .25:
                g.setColorAt(0, QColor(255,200,50)); g.setColorAt(1, QColor(255,140,30))
            else:
                g.setColorAt(0, QColor(255,60,60)); g.setColorAt(1, QColor(200,30,30))
            p.setBrush(g)
            p.drawRect(bx, by+barh-fh, 3, fh)
            
        if c.esp_name:
            parts = [pl.name]
            if c.esp_distance: parts.append(f"[{pl.distance:.0f}m]")
            st = ""
            if pl.is_scoped: st += "🔭"
            if pl.is_defusing: st += "💣"
            if pl.is_crouching: st += "⬇"
            lb = "  ".join(parts) + (f"  {st}" if st else "")
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            p.setPen(QColor(0,0,0,200))
            p.drawText(int(hx)-100+1, int(y1)-14+1, 200, 14, Qt.AlignCenter, lb)
            p.setPen(QColor(255,255,255,240))
            p.drawText(int(hx)-100, int(y1)-14, 200, 14, Qt.AlignCenter, lb)

        if c.skeleton_enabled and pl.bones:
            p.setPen(QPen(QColor(255, 255, 255, 200), 1.0))
            for b1, b2 in pl.bones:
                p.drawLine(int(b1[0]), int(b1[1]), int(b2[0]), int(b2[1]))

        if pl.weapon_name:
            # Daha iyi görünürlük için arka planlı metin
            # Box'ın ALTINA çiziyoruz: y1 + h + padding
            wx = int(x1 + (bw / 2))
            wy = int(y1 + bh + 12)
            
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            p.setPen(QColor(0, 0, 0, 255))
            # Outline-ish effect
            for ox, oy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                p.drawText(wx-100+ox, wy-7+oy, 200, 14, Qt.AlignCenter, pl.weapon_name)
            
            # Ana metin (Sarımsı beyaz)
            p.setPen(QColor(230, 230, 200, 255))
            p.drawText(wx-100, wy-7, 200, 14, Qt.AlignCenter, pl.weapon_name)

    def _cr(self, p, x, y, w, h, c):
        x,y,w,h,c = int(x),int(y),int(w),int(h),int(c)
        lines = [(x,y,x+c,y),(x,y,x,y+c),(x+w,y,x+w-c,y),(x+w,y,x+w,y+c),
                 (x,y+h,x+c,y+h),(x,y+h,x,y+h-c),(x+w,y+h,x+w-c,y+h),(x+w,y+h,x+w,y+h-c)]
        for l in lines: p.drawLine(*l)


# ═══════════════════════════════════════════
#  Neon UI Widgets
# ═══════════════════════════════════════════

# Mor–siyah tema renkleri
THEME_BG = "#050508"
THEME_CARD = "#0c0c12"
THEME_BORDER = "#1f1f28"
THEME_ACCENT = "#8b5cf6"
THEME_ACCENT_DARK = "#7c3aed"
THEME_ACCENT_SOFT = "rgba(139, 92, 246, 0.12)"
THEME_TEXT = "#e8e8ec"
THEME_TEXT_DIM = "#8888a0"
THEME_GLOW = "rgba(139, 92, 246, 0.25)"

# ComboBox + açılır liste (seçenekler tam okunabilsin)
_COMBO_STYLE = f"""
    QComboBox {{
        background: #16161e; color: {THEME_TEXT}; border: 1px solid rgba(45,45,58,0.8);
        border-radius: 8px; padding: 8px 12px; min-width: 100px; font-size: 10pt;
    }}
    QComboBox:hover {{ border-color: rgba(139,92,246,0.4); }}
    QComboBox QAbstractItemView {{
        min-height: 132px; padding: 6px; background: #16161e; border: 1px solid rgba(45,45,58,0.9);
        border-radius: 8px; outline: none; selection-background-color: rgba(139,92,246,0.35);
    }}
    QComboBox QAbstractItemView::item {{ min-height: 36px; padding: 8px 12px; font-size: 10pt; }}
"""

def add_glow(widget, color=QColor(139, 92, 246), radius=18):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(radius)
    eff.setColor(color)
    eff.setOffset(0, 0)
    widget.setGraphicsEffect(eff)


class ModernTog(QWidget):
    def __init__(self, label, checked=True, callback=None, parent=None):
        super().__init__(parent)
        self.label = label
        self.checked = checked
        self.callback = callback
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 0, 12, 0)
        self.label_widget = QLabel(label)
        self.label_widget.setStyleSheet(f"color: {THEME_TEXT}; font-family: 'Segoe UI'; font-size: 10pt; font-weight: 500;")
        self._layout.addWidget(self.label_widget)
        self._layout.addStretch()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        sw_w, sw_h = 42, 22
        sw_x = self.width() - sw_w - 8
        sw_y = (self.height() - sw_h) // 2
        if self.checked:
            p.setPen(Qt.NoPen)
            grad = QLinearGradient(sw_x, sw_y, sw_x + sw_w, sw_y)
            grad.setColorAt(0, QColor(124, 58, 237))
            grad.setColorAt(1, QColor(139, 92, 246))
            p.setBrush(grad)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(30, 30, 38))
        p.drawRoundedRect(sw_x, sw_y, sw_w, sw_h, 11, 11)
        knob_x = sw_x + (sw_w - 18) if self.checked else sw_x + 3
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(int(knob_x), sw_y + 2, 18, 18)
        p.end()

    def mousePressEvent(self, event):
        self.checked = not self.checked
        if self.callback: self.callback(self.checked)
        self.update()

class ModernSld(QWidget):
    def __init__(self, label, min_val, max_val, val, suffix="", div=1.0, callback=None):
        super().__init__()
        self.div = div
        self.suffix = suffix
        self.callback = callback
        self.setFixedHeight(52)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)
        header_layout = QHBoxLayout()
        self.lbl = QLabel(label)
        self.lbl.setStyleSheet(f"color: {THEME_TEXT}; font-family: 'Segoe UI'; font-size: 10pt; font-weight: 500;")
        self.val_lbl = QLabel(self._fmt(val))
        self.val_lbl.setStyleSheet(f"color: {THEME_ACCENT}; font-weight: 700; font-family: 'Segoe UI'; font-size: 10pt;")
        header_layout.addWidget(self.lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.val_lbl)
        self.sl = QSlider(Qt.Horizontal)
        self.sl.setRange(min_val, max_val)
        self.sl.setValue(val)
        self.sl.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 5px; background: rgba(40, 40, 55, 0.8); border-radius: 3px; }}
            QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #8b5cf6); border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: #fff; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; border: 2px solid {THEME_ACCENT}; }}
        """)
        self.sl.valueChanged.connect(self._on_change)
        layout.addLayout(header_layout)
        layout.addWidget(self.sl)
        
    def _fmt(self, v):
        d = v / self.div
        if self.div >= 10: return f"{d:.1f}{self.suffix}"
        return f"{int(d)}{self.suffix}"

    def _on_change(self, v):
        self.val_lbl.setText(self._fmt(v))
        if self.callback: self.callback(v / self.div)

class ColorButton(QPushButton):
    def __init__(self, label, color_list, callback=None, parent=None):
        super().__init__(parent)
        self.label = label
        self.color_list = color_list # Reference to [r, g, b] list
        self.callback = callback
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._pick_color)
        
    def _rgb_from_list(self):
        """Renk listesini 0-255 RGB'ye çevirir (liste 0-1 veya 0-255 olabilir)."""
        r, g, b = self.color_list[0], self.color_list[1], self.color_list[2]
        if r <= 1 and g <= 1 and b <= 1:
            return int(r * 255), int(g * 255), int(b * 255)
        return int(r), int(g), int(b)

    def _pick_color(self):
        rr, gg, bb = self._rgb_from_list()
        c = QColor(rr, gg, bb)
        dlg = QColorDialog(c, self)
        dlg.setWindowTitle(f"{self.label} rengi")
        dlg.setOption(QColorDialog.DontUseNativeDialog, True)
        dlg.setMinimumSize(540, 420)
        if dlg.exec_() == QDialog.Accepted:
            new_c = dlg.selectedColor()
            if new_c.isValid():
                self.color_list[0] = new_c.red()
                self.color_list[1] = new_c.green()
                self.color_list[2] = new_c.blue()
                if self.callback:
                    self.callback()
                self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rr, gg, bb = self._rgb_from_list()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(28, 28, 38))
        p.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        p.setPen(QColor(232, 232, 236))
        p.setFont(QFont("Segoe UI", 10, QFont.Medium))
        p.drawText(14, self.height() // 2 + 5, self.label)
        cx, cy = self.width() - 38, self.height() // 2 - 10
        p.setPen(QColor(50, 50, 60))
        p.setBrush(QColor(rr, gg, bb))
        p.drawEllipse(int(cx), int(cy), 22, 22)
        p.end()


class ColorButtonFloat(QPushButton):
    """Renk seçici — config listesi 0.0–1.0 (float) formatında."""
    def __init__(self, label, color_list, callback=None, parent=None):
        super().__init__(parent)
        self.label = label
        self.color_list = color_list
        self.callback = callback
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._pick_color)

    def _rgb_from_list(self):
        r, g, b = self.color_list[0], self.color_list[1], self.color_list[2]
        return int(r * 255), int(g * 255), int(b * 255)

    def _pick_color(self):
        rr, gg, bb = self._rgb_from_list()
        c = QColor(rr, gg, bb)
        dlg = QColorDialog(c, self)
        dlg.setWindowTitle(f"{self.label} rengi")
        dlg.setOption(QColorDialog.DontUseNativeDialog, True)
        if dlg.exec_() == QDialog.Accepted:
            new_c = dlg.selectedColor()
            if new_c.isValid():
                self.color_list[0] = new_c.red() / 255.0
                self.color_list[1] = new_c.green() / 255.0
                self.color_list[2] = new_c.blue() / 255.0
                if self.callback:
                    self.callback()
                self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rr, gg, bb = self._rgb_from_list()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(28, 28, 38))
        p.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        p.setPen(QColor(232, 232, 236))
        p.setFont(QFont("Segoe UI", 10, QFont.Medium))
        p.drawText(14, self.height() // 2 + 5, self.label)
        cx, cy = self.width() - 38, self.height() // 2 - 10
        p.setPen(QColor(50, 50, 60))
        p.setBrush(QColor(rr, gg, bb))
        p.drawEllipse(int(cx), int(cy), 22, 22)
        p.end()


class SectionCard(QFrame):
    """Başlıklı bölüm kartı — sayfa içi gruplama."""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("SectionCard")
        self.setStyleSheet(f"""
            QFrame#SectionCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(18, 18, 26, 0.98), stop:1 rgba(12, 12, 18, 0.99));
                border: 1px solid rgba(38, 38, 52, 0.6);
                border-radius: 16px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # Üst accent çizgisi
        top_line = QFrame()
        top_line.setFixedHeight(2)
        top_line.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.2 {THEME_ACCENT}, stop:0.8 {THEME_ACCENT}, stop:1 transparent); border: none; border-top-left-radius: 16px; border-top-right-radius: 16px;")
        layout.addWidget(top_line)
        inner = QWidget()
        inner.setStyleSheet("background: transparent; border: none;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(20, 14, 20, 18)
        inner_layout.setSpacing(14)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"""
            color: {THEME_TEXT_DIM};
            font-family: 'Segoe UI';
            font-size: 9pt;
            font-weight: 700;
            letter-spacing: 1.2px;
            border: none;
            background: transparent;
        """)
        inner_layout.addWidget(title_lbl)
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 2, 0, 0)
        self.content_layout.setSpacing(10)
        inner_layout.addLayout(self.content_layout)
        layout.addWidget(inner)

    def addWidget(self, w):
        self.content_layout.addWidget(w)


def _scroll_page(widget):
    """Sayfa widget'ını kaydırılabilir alan içine sarar."""
    scroll = QScrollArea()
    scroll.setWidget(widget)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; outline: none; }")
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return scroll


# ═══════════════════════════════════════════
#  Game Logic Thread
# ═══════════════════════════════════════════
class GameThread(QThread):
    players_updated = pyqtSignal(list)
    game_exited = pyqtSignal()

    def __init__(self, config, memory, esp, aimbot, misc, overlay):
        super().__init__()
        self.config = config
        self.memory = memory
        self.esp = esp
        self.aimbot = aimbot
        self.misc = misc
        self.overlay = overlay
        self.running = True

    def run(self):
        while self.running:
            try:
                if self.memory.is_attached and not self.memory.is_process_running():
                    self.memory.detach()
                    self.game_exited.emit()
                    break
                rect = get_game_window_rect()
                if not rect:
                    time.sleep(0.5)
                    continue
                self.config.screen_width = rect[2]
                self.config.screen_height = rect[3]
                players = self.esp.update()
                self.config.local_position = self.esp.local_player.pos if self.esp.local_player else None
                self.aimbot.update(players, self.esp.local_player)
                self.misc.update()
                self.players_updated.emit(players)
            except Exception:
                pass
            time.sleep(0.005)

# ═══════════════════════════════════════════
#  Main GUI Window
# ═══════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.memory = Memory(self.config.process_name)
        self.esp = ESP(self.config, self.memory)
        self.aimbot = Aimbot(self.config, self.memory)
        self.misc = Misc(self.config, self.memory)
        self.overlay = OverlayWindow(self.config)

        self.running = False
        
        self.setWindowTitle("raven.cash")
        self.setFixedSize(940, 700)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Main Layout
        main_widget = QWidget()
        # Transparent central widget to hold the shadow
        main_widget.setAttribute(Qt.WA_TranslucentBackground)
        self.setCentralWidget(main_widget)
        
        # Outer Layout (Handles Margins for Shadow)
        outer_layout = QVBoxLayout(main_widget)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        
        # Wrapper Frame — premium gradient + soft border
        self.wrapper = QFrame()
        self.wrapper.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #070710, stop:0.35 #050508, stop:0.65 #050508, stop:1 #080812);
                border-radius: 20px;
                border: 1px solid rgba(40, 40, 52, 0.7);
            }}
        """)
        outer_layout.addWidget(self.wrapper)
        add_glow(self.wrapper, QColor(0, 0, 0, 200), 32)

        # Inner Layout (Holds Sidebar + Content)
        main_layout = QHBoxLayout(self.wrapper)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setFixedWidth(232)
        sidebar.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #07070d, stop:0.5 #0a0a12, stop:1 #0d0d16);
            border-top-left-radius: 20px;
            border-bottom-left-radius: 20px;
            border-right: 1px solid rgba(35, 35, 48, 0.6);
        """)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(22, 28, 22, 28)
        sl.setSpacing(6)

        # Sol üst logo: Karga emojisi + raven.cash
        logo_container = QWidget()
        logo_container.setStyleSheet("background: transparent; border: none;")
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(10)
        crow_emoji = QLabel(chr(0x1F426) + chr(0x200D) + chr(0x2B1B))  # 🐦‍⬛ karga
        crow_emoji.setStyleSheet(f"font-size: 28pt; border: none; background: transparent; color: {THEME_TEXT};")
        crow_emoji.setFixedHeight(36)
        logo_layout.addWidget(crow_emoji)
        logo_sub = QLabel("raven.cash")
        logo_sub.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        logo_sub.setStyleSheet(f"""
            color: {THEME_TEXT_DIM};
            font-family: 'Segoe UI'; font-size: 10pt; font-weight: 600;
            letter-spacing: 2px;
            border: none; background: transparent;
        """)
        logo_layout.addWidget(logo_sub)
        sl.addWidget(logo_container)
        sl.addSpacing(8)
        logo_line = QFrame()
        logo_line.setFixedHeight(1)
        logo_line.setFixedWidth(90)
        logo_line.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME_ACCENT}, stop:1 transparent);")
        sl.addWidget(logo_line)
        sl.addSpacing(28)

        # Nav Buttons
        self.nav_btns = []
        for i, name in enumerate(["Visuals", "Aimbot", "Misc", "Config"]):
            btn = QPushButton(name)
            btn.setFixedHeight(46)
            btn.setCheckable(True)
            if i == 0: btn.setChecked(True)
            btn.clicked.connect(lambda c, idx=i: self._change_page(idx))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {THEME_TEXT_DIM};
                    border: none;
                    text-align: left;
                    padding-left: 16px;
                    font-family: 'Segoe UI'; font-size: 10pt; font-weight: 600;
                    border-radius: 12px;
                }}
                QPushButton:hover {{ color: {THEME_TEXT}; background: {THEME_ACCENT_SOFT}; }}
                QPushButton:checked {{
                    color: #fff;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(139, 92, 246, 0.22), stop:1 transparent);
                    border-left: 3px solid {THEME_ACCENT};
                }}
            """)
            self.nav_btns.append(btn)
            sl.addWidget(btn)

        sl.addStretch()

        # Status pill
        self.status = QLabel("  UNDETECTED  ")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(f"""
            color: #22c55e;
            font-size: 8pt;
            font-weight: 700;
            letter-spacing: 1px;
            border: none;
            background: rgba(34, 197, 94, 0.12);
            border-radius: 20px;
            padding: 6px 4px;
        """)
        sl.addWidget(self.status)
        sl.addSpacing(12)

        # Toggle Button — premium gradient when active
        self.btn_toggle = QPushButton("ENABLE")
        self.btn_toggle.setFixedHeight(48)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._toggle_cheat)
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a24, stop:1 #14141c);
                color: #fff;
                border: 1px solid rgba(139, 92, 246, 0.5);
                border-radius: 12px;
                font-weight: bold; font-size: 10pt;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a38, stop:1 #1e1e2a);
                border-color: {THEME_ACCENT};
            }}
        """)
        add_glow(self.btn_toggle, QColor(139, 92, 246), 14)
        sl.addWidget(self.btn_toggle)
        
        main_layout.addWidget(sidebar)

        # ── Content Area ──
        content_area = QWidget()
        content_area.setStyleSheet("background: transparent; border: none;")
        cl = QVBoxLayout(content_area)
        cl.setContentsMargins(40, 38, 40, 38)
        cl.setSpacing(20)

        # Title bar + alt çizgi
        top_bar = QHBoxLayout()
        self.lbl_page = QLabel("VISUALS")
        self.lbl_page.setStyleSheet(f"color: #fff; font-size: 16pt; font-weight: 800; letter-spacing: 2px; background: transparent; border: none;")
        top_bar.addWidget(self.lbl_page)
        top_bar.addStretch()
        btn_style = f"color: {THEME_TEXT_DIM}; border: none; font-size: 13pt; font-weight: bold; background: transparent; border-radius: 8px; min-width: 32px;"
        btn_min = QPushButton("−")
        btn_min.setFixedSize(34, 34)
        btn_min.setCursor(Qt.PointingHandCursor)
        btn_min.clicked.connect(self.showMinimized)
        btn_min.setStyleSheet(f"QPushButton {{ {btn_style} }} QPushButton:hover {{ color: {THEME_TEXT}; background: rgba(255,255,255,0.06); }}")
        btn_close = QPushButton("×")
        btn_close.setFixedSize(34, 34)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet(f"QPushButton {{ {btn_style} }} QPushButton:hover {{ color: #f87171; background: rgba(248,113,113,0.12); }}")
        top_bar.addWidget(btn_min)
        top_bar.addWidget(btn_close)
        cl.addLayout(top_bar)
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.3 rgba(139,92,246,0.3), stop:0.7 rgba(139,92,246,0.3), stop:1 transparent); border: none;")
        cl.addWidget(sep)
        cl.addSpacing(18)
        
        # Stacked Pages
        self.pages = QStackedWidget()
        self.pages.addWidget(self._create_esp_page())
        self.pages.addWidget(self._create_aim_page())
        self.pages.addWidget(self._create_misc_page())
        self.pages.addWidget(self._create_cfg_page())
        
        cl.addWidget(self.pages)
        main_layout.addWidget(content_area)
        
        # Drag Logic
        self.drag_pos = None
        self.thread = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def _create_esp_page(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setSpacing(18)
        l.setContentsMargins(0, 0, 8, 0)
        # Bölüm: Genel
        card_main = SectionCard("GENEL")
        card_main.addWidget(ModernTog("Master Switch", self.config.esp_enabled, lambda v: setattr(self.config, 'esp_enabled', v)))
        card_main.addWidget(ModernTog("Kutu (Box)", self.config.esp_box, lambda v: setattr(self.config, 'esp_box', v)))
        card_main.addWidget(ModernTog("İskelet", self.config.skeleton_enabled, lambda v: setattr(self.config, 'skeleton_enabled', v)))
        card_main.addWidget(ModernTog("Snaplines", self.config.esp_snaplines, lambda v: setattr(self.config, 'esp_snaplines', v)))
        l.addWidget(card_main)
        # Bölüm: Bilgi
        card_info = SectionCard("BİLGİ")
        card_info.addWidget(ModernTog("Sağlık Çubuğu", self.config.esp_health_bar, lambda v: setattr(self.config, 'esp_health_bar', v)))
        card_info.addWidget(ModernTog("İsimler", self.config.esp_name, lambda v: setattr(self.config, 'esp_name', v)))
        card_info.addWidget(ModernTog("Mesafe", self.config.esp_distance, lambda v: setattr(self.config, 'esp_distance', v)))
        l.addWidget(card_info)
        # Bölüm: Filtre & Diğer
        card_filter = SectionCard("FİLTRE & DİĞER")
        card_filter.addWidget(ModernTog("Sadece Düşman", self.config.esp_team_check, lambda v: setattr(self.config, 'esp_team_check', v)))
        card_filter.addWidget(ModernTog("Düşman Silahı", self.config.esp_weapon_enemies, lambda v: setattr(self.config, 'esp_weapon_enemies', v)))
        card_filter.addWidget(ModernTog("Takım Silahı", self.config.esp_weapon_team, lambda v: setattr(self.config, 'esp_weapon_team', v)))
        card_filter.addWidget(ModernTog("OBS Bypass", self.config.obs_bypass, lambda v: self._toggle_obs(v)))
        l.addWidget(card_filter)
        card_overlay = SectionCard("OVERLAY & NİŞANGAH")
        card_overlay.addWidget(ModernTog("FPS göster", getattr(self.config, "overlay_show_fps", False), lambda v: setattr(self.config, "overlay_show_fps", v)))
        card_overlay.addWidget(ModernTog("Düşman sayısı", getattr(self.config, "overlay_show_enemy_count", False), lambda v: setattr(self.config, "overlay_show_enemy_count", v)))
        card_overlay.addWidget(ModernTog("Bomba sayacı (C4)", getattr(self.config, "esp_bomb_timer", True), lambda v: setattr(self.config, "esp_bomb_timer", v)))
        card_overlay.addWidget(ModernTog("Radar Hack (Oyun İçi)", getattr(self.config, "radar_hack_enabled", False), lambda v: setattr(self.config, "radar_hack_enabled", v)))
        card_overlay.addWidget(ModernTog("2D Radar (Overlay)", getattr(self.config, "esp_radar", False), lambda v: setattr(self.config, "esp_radar", v)))
        card_overlay.addWidget(ModernSld("Radar boyutu", 40, 120, int(getattr(self.config, "radar_radius", 65)), " px", 1.0, lambda v: setattr(self.config, "radar_radius", int(v))))
        row_ch = QHBoxLayout()
        lbl_ch = QLabel("Nişangah:")
        lbl_ch.setStyleSheet(f"color: {THEME_TEXT}; font-family: 'Segoe UI'; font-size: 10pt; font-weight: 500;")
        row_ch.addWidget(lbl_ch)
        combo_ch = QComboBox()
        combo_ch.addItems(["Çarpı", "Nokta", "Daire"])
        combo_ch.setCurrentIndex(getattr(self.config, "crosshair_style", 0))
        combo_ch.setStyleSheet(_COMBO_STYLE)
        combo_ch.currentIndexChanged.connect(lambda i: setattr(self.config, "crosshair_style", i))
        row_ch.addWidget(combo_ch)
        row_ch.addStretch()
        wch = QWidget()
        wch.setLayout(row_ch)
        card_overlay.addWidget(wch)
        card_overlay.addWidget(ModernSld("Nişangah boyutu", 2, 20, getattr(self.config, "crosshair_size", 6), "", 1.0, lambda v: setattr(self.config, "crosshair_size", int(v))))
        l.addWidget(card_overlay)
        l.addStretch()
        return _scroll_page(w)

    def _toggle_obs(self, enabled):
        self.config.obs_bypass = enabled
        # Update affinity immediately if window exists
        hwnd = int(self.overlay.winId())
        if enabled:
            try:
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000011) # WDA_EXCLUDEFROMCAPTURE
            except: pass
        else:
            try:
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000000) # WDA_NONE
            except: pass

    def _create_aim_page(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setSpacing(18)
        l.setContentsMargins(0, 0, 8, 0)
        # Aimbot
        card_aim = SectionCard("AIMBOT")
        card_aim.addWidget(ModernTog("Aktif", self.config.aim_enabled, lambda v: setattr(self.config, 'aim_enabled', v)))
        row_aim_key = QHBoxLayout()
        lbl_aim_key = QLabel("Aim tuşu:")
        lbl_aim_key.setStyleSheet(f"color: {THEME_TEXT}; font-family: 'Segoe UI'; font-size: 10pt; font-weight: 500;")
        row_aim_key.addWidget(lbl_aim_key)
        combo_aim_key = QComboBox()
        combo_aim_key.addItems(["Sağ Tık (ADS)", "Sol Tık"])
        combo_aim_key.setCurrentIndex(0 if getattr(self.config, "aim_key", 0x02) == 0x02 else 1)
        combo_aim_key.setStyleSheet(_COMBO_STYLE)
        combo_aim_key.currentIndexChanged.connect(lambda i: setattr(self.config, "aim_key", 0x02 if i == 0 else 0x01))
        row_aim_key.addWidget(combo_aim_key)
        row_aim_key.addStretch()
        wrap_aim_key = QWidget()
        wrap_aim_key.setLayout(row_aim_key)
        card_aim.addWidget(wrap_aim_key)
        card_aim.addWidget(ModernTog("FOV Dairesi", self.config.aim_fov_circle, lambda v: setattr(self.config, 'aim_fov_circle', v)))
        card_aim.addWidget(ModernTog("Takım Kontrolü", self.config.aim_team_check, lambda v: setattr(self.config, 'aim_team_check', v)))
        card_aim.addWidget(ModernSld("FOV", 10, 250, int(self.config.aim_fov * 10), "°", 10.0, lambda v: setattr(self.config, 'aim_fov', v)))
        card_aim.addWidget(ModernSld("Yumuşaklık", 10, 300, int(self.config.aim_smoothness * 10), "", 10.0, lambda v: setattr(self.config, 'aim_smoothness', v)))
        card_aim.addWidget(ModernTog("Mesafe sınırı (m)", getattr(self.config, 'aim_max_distance_enabled', False), lambda v: setattr(self.config, 'aim_max_distance_enabled', v)))
        card_aim.addWidget(ModernSld("Max mesafe (m)", 30, 150, int(getattr(self.config, 'aim_max_distance', 80)), " m", 1.0, lambda v: setattr(self.config, 'aim_max_distance', float(v))))
        card_aim.addWidget(ColorButton("FOV Rengi", self.config.aim_fov_color, callback=None))
        row_bone = QHBoxLayout()
        lbl_bone = QLabel("Aim hedefi:")
        lbl_bone.setStyleSheet(f"color: {THEME_TEXT}; font-family: 'Segoe UI'; font-size: 10pt; font-weight: 500;")
        row_bone.addWidget(lbl_bone)
        combo_bone = QComboBox()
        combo_bone.addItems(["Kafa", "Boyun", "Göğüs"])
        combo_bone.setCurrentIndex(["head", "neck", "chest"].index(getattr(self.config, "aim_bone", "head")))
        combo_bone.setStyleSheet(_COMBO_STYLE)
        combo_bone.currentIndexChanged.connect(lambda i: setattr(self.config, "aim_bone", ["head", "neck", "chest"][i]))
        row_bone.addWidget(combo_bone)
        row_bone.addStretch()
        wrap_bone = QWidget()
        wrap_bone.setLayout(row_bone)
        card_aim.addWidget(wrap_bone)
        l.addWidget(card_aim)
        # Flick
        card_flick = SectionCard("FLICK (KAFYA SNAP)")
        card_flick.addWidget(ModernTog("Aktif", self.config.flick_enabled, lambda v: setattr(self.config, 'flick_enabled', v)))
        card_flick.addWidget(ModernSld("Flick FOV", 5, 100, int(self.config.flick_fov * 10), "°", 10.0, lambda v: setattr(self.config, 'flick_fov', v)))
        card_flick.addWidget(ModernSld("Flick hızı (düşük=ani)", 2, 10, int(getattr(self.config, 'flick_smooth', 1.0) * 10), "", 10.0, lambda v: setattr(self.config, 'flick_smooth', max(0.2, v))))
        l.addWidget(card_flick)
        # RCS
        card_rcs = SectionCard("GERİ TEPME (RCS)")
        card_rcs.addWidget(ModernTog("RCS Aktif", self.config.rcs_enabled, lambda v: setattr(self.config, 'rcs_enabled', v)))
        card_rcs.addWidget(ModernSld("RCS X", 0, 20, int(self.config.rcs_scale_x * 10), "", 10.0, lambda v: setattr(self.config, 'rcs_scale_x', v)))
        card_rcs.addWidget(ModernSld("RCS Y", 0, 20, int(self.config.rcs_scale_y * 10), "", 10.0, lambda v: setattr(self.config, 'rcs_scale_y', v)))
        l.addWidget(card_rcs)
        l.addStretch()
        return _scroll_page(w)

    def _create_misc_page(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setSpacing(18)
        l.setContentsMargins(0, 0, 8, 0)
        card = SectionCard("MISC")
        card.addWidget(ModernTog("Bunnyhop", self.config.bhop_enabled, lambda v: setattr(self.config, 'bhop_enabled', v)))
        card.addWidget(ModernTog("No Flash", getattr(self.config, 'no_flash_enabled', False), lambda v: setattr(self.config, 'no_flash_enabled', v)))
        card.addWidget(ModernTog("Triggerbot", self.config.trigger_enabled, lambda v: setattr(self.config, 'trigger_enabled', v)))
        card.addWidget(ModernTog("Triggerbot Otomatik (nişan üstü)", getattr(self.config, 'trigger_auto', False), lambda v: setattr(self.config, 'trigger_auto', v)))
        card.addWidget(ModernSld("Triggerbot gecikme (ms)", 0, 200, int(getattr(self.config, 'trigger_delay_ms', 60)), " ms", 1.0, lambda v: setattr(self.config, 'trigger_delay_ms', int(v))))
        card.addWidget(ModernTog("Spinbot", self.config.spin_enabled, lambda v: setattr(self.config, 'spin_enabled', v)))
        card.addWidget(ModernSld("Spin Hızı", 5, 50, int(self.config.spin_speed), "", 1.0, lambda v: setattr(self.config, 'spin_speed', v)))
        card.addWidget(ModernTog("Ateş/Aim sırasında spin kapalı", getattr(self.config, 'spin_check_shoot', True), lambda v: setattr(self.config, 'spin_check_shoot', v)))
        l.addWidget(card)
        # Oyun FOV
        card_fov = SectionCard("OYUN FOV (GÖRÜŞ AÇISI)")
        card_fov.addWidget(ModernTog("Oyun FOV kullan", getattr(self.config, 'game_fov_enabled', False), lambda v: setattr(self.config, 'game_fov_enabled', v)))
        card_fov.addWidget(ModernSld("FOV değeri (60–140)", 60, 140, int(getattr(self.config, 'game_fov_value', 90)), "°", 1.0, lambda v: setattr(self.config, 'game_fov_value', int(v))))
        l.addWidget(card_fov)
        # Viewmodel FOV (el/silah)
        card_vmfov = SectionCard("SİLAH / EL FOV (VIEWMODEL)")
        card_vmfov.addWidget(ModernTog("Silah FOV kullan", getattr(self.config, 'viewmodel_fov_enabled', False), lambda v: setattr(self.config, 'viewmodel_fov_enabled', v)))
        card_vmfov.addWidget(ModernSld("Silah FOV (54–120)", 54, 120, int(getattr(self.config, 'viewmodel_fov_value', 68)), "°", 1.0, lambda v: setattr(self.config, 'viewmodel_fov_value', int(v))))
        l.addWidget(card_vmfov)
        l.addStretch()
        return _scroll_page(w)
        
    def _create_cfg_page(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setSpacing(18)
        l.setContentsMargins(0, 0, 8, 0)
        card_sys = SectionCard("SİSTEM")
        info = QLabel(f"PID: {self.memory.pid if self.memory.pid else 'N/A'}\nProcess: {self.config.process_name}\n\nSürüm: {APP_VERSION}  •  Build: {APP_BUILD}")
        info.setStyleSheet(f"color: {THEME_TEXT_DIM}; font-size: 10pt; font-family: 'Segoe UI'; line-height: 1.5;")
        info.setWordWrap(True)
        card_sys.addWidget(info)
        l.addWidget(card_sys)
        card_keys = SectionCard("TUŞLAR (KEYBINDS)")
        key_lines = [
            "Aimbot      → Sağ / Sol tık (Aimbot sayfasından seçilir)",
            "Flick       → Sol tık",
            "Triggerbot  → Nişan düşman üstündeyken otomatik veya tetikleyici",
            "Bunnyhop    → Space",
            "Spinbot     → X",
        ]
        key_lbl = QLabel("\n".join(key_lines))
        key_lbl.setStyleSheet(f"color: {THEME_TEXT_DIM}; font-size: 9pt; font-family: 'Consolas'; line-height: 1.6;")
        key_lbl.setWordWrap(True)
        card_keys.addWidget(key_lbl)
        l.addWidget(card_keys)
        l.addStretch()
        return _scroll_page(w)

    def _on_game_exited(self):
        """Oyun kapandığında overlay kapat, durumu güncelle."""
        self.running = False
        if self.thread:
            self.thread.running = False
            self.thread.wait(500)
            self.thread = None
        self.memory.detach()
        self.overlay.hide()
        self.btn_toggle.setText("ENABLE")
        self.status.setText("  OYUN KAPANDI  ")
        self.status.setStyleSheet(f"color: #f59e0b; font-size: 8pt; font-weight: 700; letter-spacing: 1px; background: rgba(245,158,11,0.12); border-radius: 20px; padding: 6px 4px;")
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a1a24, stop:1 #14141c); color: #fff; border: 1px solid rgba(139, 92, 246, 0.5); border-radius: 12px; font-weight: bold; font-size: 10pt; }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2a38, stop:1 #1e1e2a); border-color: {THEME_ACCENT}; }}
        """)

    def _change_page(self, index):
        self.pages.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)
        page_names = ["VISUALS", "AIMBOT", "MISC", "CONFIG"]
        self.lbl_page.setText(page_names[index])

    def _toggle_cheat(self):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.running = False
                self.thread.wait()
                self.thread = None
                
            self.memory.detach()
            self.overlay.hide()
            self.btn_toggle.setText("ENABLE")
            self.status.setText("IDLE")
            self.status.setText("  UNDETECTED  ")
            self.status.setStyleSheet(f"color: #22c55e; font-size: 8pt; font-weight: 700; letter-spacing: 1px; background: rgba(34, 197, 94, 0.12); border-radius: 20px; padding: 6px 4px;")
            self.btn_toggle.setStyleSheet(f"""
                QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a1a24, stop:1 #14141c); color: #fff; border: 1px solid rgba(139, 92, 246, 0.5); border-radius: 12px; font-weight: bold; font-size: 10pt; }}
                QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2a38, stop:1 #1e1e2a); border-color: {THEME_ACCENT}; }}
            """)
        else:
            if self.memory.attach():
                self.running = True
                self.overlay.sync_to_game()
                self.overlay.show()
                focus_game_window()
                
                # Start Game Thread
                self.thread = GameThread(self.config, self.memory, self.esp, self.aimbot, self.misc, self.overlay)
                self.thread.players_updated.connect(self.overlay.update_players)
                self.thread.game_exited.connect(self._on_game_exited)
                self.thread.start()
                
                self.btn_toggle.setText("DISABLE")
                self.status.setText("ACTIVE")
                self.status.setText("  CONNECTED  ")
                self.status.setStyleSheet(f"color: {THEME_ACCENT}; font-size: 8pt; font-weight: 700; letter-spacing: 1px; background: {THEME_ACCENT_SOFT}; border-radius: 20px; padding: 6px 4px;")
                self.btn_toggle.setStyleSheet(f"""
                    QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7c3aed, stop:1 #6d28d9); color: #fff; border: none; border-radius: 12px; font-weight: bold; font-size: 10pt; }}
                    QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8b5cf6, stop:1 #7c3aed); }}
                """)

    def closeEvent(self, event):
        self.running = False
        if self.thread:
            self.thread.running = False
            self.thread.wait()
        self.overlay.close()
        event.accept()

# ═══════════════════════════════════════════
#  Splash Screen — Profesyonel Açılış Ekranı
# ═══════════════════════════════════════════
_SPLASH_CODE_LINES = [
    "0x7FF8A2B4C100  mov eax, [rbp-0x14]",
    "client.dll+0x1A2B3C  dwEntityList",
    "ReadProcessMemory(hProcess, base, ...)",
    "m_vecOrigin[0] = 1247.32",
    "entity_list->GetClientEntity( i )",
    "m_iHealth -> 0x64",
    "WorldToScreen( vec, &screen )",
    "GetAsyncKeyState( VK_RBUTTON ) & 0x8000",
    "normalize( dx, dy ) -> smooth_aim",
    "dwViewMatrix = client.dll+0x1B2A4C0",
    "m_entityList->GetClientEntity( index )",
]

APP_VERSION = "1.0.0"
APP_BUILD = "external"

class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(620, 380)
        self._opacity = 1.0
        self._progress = 0.0
        self._corner_radius = 28
        self._code_lines = []
        self._line_height = 16
        self._code_font = QFont("Consolas", 8, QFont.Normal)
        self._init_code_stream()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_code)
        self._timer.start(50)
        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._tick_progress)
        self._progress_timer.start(45)

    def _init_code_stream(self):
        w, h = self.width(), self.height()
        num_cols = max(6, w // 72)
        for col in range(num_cols):
            x = 16 + col * 72
            y = random.randint(-h, h)
            text = random.choice(_SPLASH_CODE_LINES)
            speed = random.uniform(0.8, 2.0)
            alpha = random.randint(60, 120)
            self._code_lines.append({"x": x, "y": y, "text": text, "speed": speed, "alpha": alpha})

    def _tick_code(self):
        h = self.height()
        for line in self._code_lines:
            line["y"] += line["speed"]
            if line["y"] > h + self._line_height:
                line["y"] = -self._line_height
                line["text"] = random.choice(_SPLASH_CODE_LINES)
        self.update()

    def _tick_progress(self):
        if self._progress < 1.0:
            self._progress = min(1.0, self._progress + 0.028)
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        r = self._corner_radius

        # Arka plan — oval köşeli dikdörtgen (şeffaf dışarıda)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(THEME_BG))
        p.drawRoundedRect(0, 0, w, h, r, r)

        # Dış çerçeve — gradient border, oval köşeler
        border_rect = self.rect().adjusted(1, 1, -2, -2)
        grad_border = QLinearGradient(0, 0, w, h)
        grad_border.setColorAt(0, QColor(139, 92, 246, int(180 * self._opacity)))
        grad_border.setColorAt(0.5, QColor(99, 102, 241, int(120 * self._opacity)))
        grad_border.setColorAt(1, QColor(139, 92, 246, int(180 * self._opacity)))
        pen = QPen(grad_border, 2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(border_rect, r, r)

        # Arka plan akan kod satırları (daha soft)
        p.setFont(self._code_font)
        for line in self._code_lines:
            c = QColor(139, 92, 246)
            c.setAlpha(int(line["alpha"] * 0.5 * self._opacity))
            p.setPen(c)
            p.drawText(int(line["x"]), int(line["y"]), line["text"])

        # Üst bant — ince accent çizgisi
        p.setPen(Qt.NoPen)
        grad_bar = QLinearGradient(0, 0, w, 0)
        grad_bar.setColorAt(0, QColor(0, 0, 0, 0))
        grad_bar.setColorAt(0.2, QColor(139, 92, 246, 200))
        grad_bar.setColorAt(0.5, QColor(99, 102, 241, 220))
        grad_bar.setColorAt(0.8, QColor(139, 92, 246, 200))
        grad_bar.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(grad_bar)
        p.drawRoundedRect(24, 18, w - 48, 3, 2, 2)

        # Ana başlık — gradient text
        title_rect = QRectF(0, 72, w, 44)
        p.setFont(QFont("Segoe UI", 26, QFont.Bold))
        for dx, dy, color in [(2, 2, QColor(0, 0, 0, 160)), (0, 0, QColor(255, 255, 255))]:
            p.setPen(color)
            p.drawText(title_rect.adjusted(dx, dy, dx, dy), Qt.AlignCenter, "RAVEN.CASH")

        # Alt başlık
        sub_rect = QRectF(0, 118, w, 24)
        p.setFont(QFont("Segoe UI", 11, QFont.Normal))
        p.setPen(QColor(139, 92, 246, int(240 * self._opacity)))
        p.drawText(sub_rect, Qt.AlignCenter, "CS2 EXTERNAL  —  UNDETECTED")

        # Sürüm / build
        p.setPen(QColor(THEME_TEXT_DIM))
        p.setFont(QFont("Segoe UI", 9, QFont.Normal))
        p.drawText(24, h - 58, f"v{APP_VERSION}  •  {APP_BUILD}")

        # Loading bar
        bar_y = h - 42
        bar_w = w - 48
        bar_x = 24
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(28, 28, 38, 220))
        p.drawRoundedRect(int(bar_x), int(bar_y), int(bar_w), 8, 4, 4)
        fill_w = bar_w * self._progress
        grad_fill = QLinearGradient(bar_x, 0, bar_x + fill_w, 0)
        grad_fill.setColorAt(0, QColor(124, 58, 237))
        grad_fill.setColorAt(1, QColor(139, 92, 246))
        p.setBrush(grad_fill)
        p.drawRoundedRect(int(bar_x), int(bar_y), int(max(0, fill_w)), 8, 4, 4)
        p.setPen(QColor(220, 220, 230))
        p.setFont(QFont("Segoe UI", 9, QFont.Medium))
        status = "Initializing..." if self._progress < 1.0 else "Ready"
        p.drawText(QRectF(bar_x, bar_y - 20, bar_w, 18), Qt.AlignCenter, status)

        p.end()

    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, value):
        self._opacity = max(0.0, min(1.0, value))
        self.setWindowOpacity(self._opacity)

    opacity = pyqtProperty(float, _get_opacity, _set_opacity)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_screen()

    def closeEvent(self, event):
        self._timer.stop()
        self._progress_timer.stop()
        super().closeEvent(event)

def run_gui():
    app = QApplication(sys.argv)
    app.setStyleSheet(f"""
        QScrollBar:vertical {{ background: transparent; width: 6px; border-radius: 3px; margin: 2px 0; }}
        QScrollBar::handle:vertical {{ background: rgba(139, 92, 246, 0.35); border-radius: 3px; min-height: 40px; }}
        QScrollBar::handle:vertical:hover {{ background: rgba(139, 92, 246, 0.55); }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QComboBox {{ background: #16161e; color: {THEME_TEXT}; border: 1px solid rgba(45,45,58,0.8); border-radius: 8px; padding: 8px 12px; }}
        QComboBox:hover {{ border-color: rgba(139,92,246,0.4); }}
    """)
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    window = MainWindow()
    window.hide()
    def on_splash_finish():
        splash.close()
        window.show()
    anim = QPropertyAnimation(splash, b"opacity")
    anim.setDuration(1200)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.finished.connect(on_splash_finish)
    QTimer.singleShot(2200, anim.start)
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_gui()
