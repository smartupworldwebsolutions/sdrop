import atexit
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import winreg
import zipfile
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import (
    QAbstractNativeEventFilter,
    QFileInfo,
    QMimeData,
    QPoint,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QDrag,
    QFont,
    QGuiApplication,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFileIconProvider,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSystemTrayIcon,
    QTabBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "SDrop"
APP_VERSION = "2.0.0"
APP_PUBLISHER = "SmartUpWorld"
APP_URL = "https://smartupworld.com"
APP_USER_MODEL_ID = "SmartUpWorld.SDrop.2"

# --- Win32 Native Setup (DPI + Taskbar Grouping) ---
if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass
    try:
        # PER_MONITOR_AWARE_V2 (-4)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

VK_LBUTTON = 0x01
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
HOTKEY_TOGGLE_ID = 1001
VK_D = 0x44

# Curated Neon Palettes: (primary_hex, glow_rgba, dark_tint_hex)
NEON_THEMES: Dict[str, Tuple[str, str, str]] = {
    "Electric Cyan": ("#00F0FF", "rgba(0, 240, 255, 160)", "#082F49"),
    "Cyber Magenta": ("#FF2A85", "rgba(255, 42, 133, 160)", "#4C0519"),
    "Neon Lime": ("#39FF14", "rgba(57, 255, 20, 150)", "#052E16"),
    "Ultraviolet": ("#A855F7", "rgba(168, 85, 247, 165)", "#2E1065"),
    "Solar Amber": ("#FFB000", "rgba(255, 176, 0, 160)", "#451A03"),
}

SHAKE_PRESETS: Dict[str, Tuple[int, int, float]] = {
    # name: (min_dx_px, required_reversals, window_sec)
    "Off": (9999, 99, 0.1),
    "Low": (22, 5, 0.70),
    "Medium": (15, 4, 0.65),
    "High": (10, 3, 0.60),
}

HOTKEY_PRESETS: Dict[str, Optional[Tuple[int, int]]] = {
    "Win + Alt + D": (MOD_WIN | MOD_ALT, VK_D),
    "Ctrl + Alt + D": (MOD_CONTROL | MOD_ALT, VK_D),
    "Ctrl + Shift + D": (MOD_CONTROL | MOD_SHIFT, VK_D),
    "Disabled": None,
}

CONFIG_DIR = Path.home() / ".sdrop"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSION_FILE = CONFIG_DIR / "session.json"
SESSION_TEMP_DIR = Path(tempfile.gettempdir()) / f"sdrop_session_{os.getpid()}"

DEFAULT_CONFIG = {
    "theme": "Electric Cyan",
    "opacity": 96,
    "shake_sensitivity": "Medium",
    "hotkey": "Win + Alt + D",
    "drag_action": "copy",  # "copy" or "move"
    "always_on_top": True,
    "auto_remove_after_drag": False,
    "auto_hide_when_empty": False,
    "persist_session": True,
    "snap_to_edges": True,
    "start_with_windows": False,
}


def cleanup_temp_dir():
    try:
        if SESSION_TEMP_DIR.exists():
            shutil.rmtree(SESSION_TEMP_DIR, ignore_errors=True)
    except Exception:
        pass


atexit.register(cleanup_temp_dir)


def ensure_session_temp() -> Path:
    SESSION_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_TEMP_DIR


def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                cfg.update(data)
        except Exception:
            pass
    return cfg


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, CONFIG_FILE)


def set_windows_startup(enabled: bool):
    if sys.platform != "win32":
        return
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                if getattr(sys, "frozen", False):
                    cmd = f'"{sys.executable}"'
                else:
                    cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
    except Exception:
        pass


def get_cursor_pos() -> QPoint:
    if sys.platform != "win32":
        return QCursor.pos()
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return QPoint(pt.x, pt.y)


def is_left_button_down() -> bool:
    if sys.platform != "win32":
        return bool(QApplication.mouseButtons() & Qt.MouseButton.LeftButton)
    return bool(ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)


def create_app_pixmap(size: int = 64, accent_hex: str = "#00F0FF") -> QPixmap:
    """Renders the SmartUpWorld SDrop neon vector icon cleanly at any resolution."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.08
    rect_size = size - 2 * margin
    bg_path = QPainterPath()
    bg_path.addRoundedRect(margin, margin, rect_size, rect_size, size * 0.24, size * 0.24)

    p.fillPath(bg_path, QColor("#0B0F19"))
    p.setPen(QPen(QColor(accent_hex), max(2.0, size * 0.055)))
    p.drawPath(bg_path)

    # Dashed inner neon drop tray
    inner = size * 0.24
    inner_size = size - 2 * inner
    pen = QPen(QColor(accent_hex), max(1.5, size * 0.04), Qt.PenStyle.DashLine)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawRoundedRect(int(inner), int(inner), int(inner_size), int(inner_size), int(size * 0.12), int(size * 0.12))

    # Crisp white down arrow
    cx = size / 2.0
    cy = size / 2.0
    arrow_pen = QPen(QColor("#F8FAFC"), max(2.0, size * 0.065), Qt.PenStyle.SolidLine)
    arrow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    arrow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(arrow_pen)
    p.drawLine(int(cx), int(cy - size * 0.13), int(cx), int(cy + size * 0.13))
    p.drawLine(int(cx - size * 0.10), int(cy + size * 0.03), int(cx), int(cy + size * 0.13))
    p.drawLine(int(cx + size * 0.10), int(cy + size * 0.03), int(cx), int(cy + size * 0.13))

    p.end()
    return pm


def ensure_ico_file() -> str:
    """Generates sdrop.ico for PyInstaller & Inno Setup."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ico_path = CONFIG_DIR / "sdrop.ico"
    pm = create_app_pixmap(256, "#00F0FF")
    pm.save(str(ico_path), "ICO")
    return str(ico_path)


def format_size(num_bytes: int) -> str:
    val = float(max(0, num_bytes))
    for unit in ("B", "KB", "MB", "GB"):
        if val < 1024:
            return f"{val:.0f} {unit}" if unit == "B" else f"{val:.1f} {unit}"
        val /= 1024
    return f"{val:.1f} TB"


@dataclass
class ShelfEntry:
    kind: str  # "file", "url", "text", "image"
    title: str
    subtitle: str
    file_path: Optional[str] = None
    url: Optional[str] = None
    text: Optional[str] = None
    image: Optional[QImage] = None
    size_bytes: int = 0
    created_at: float = field(default_factory=time.time)

    def ensure_temp_image_file(self) -> Optional[str]:
        """Materializes an in-memory QImage into the managed session temp folder."""
        if self.kind != "image" or self.image is None or self.image.isNull():
            return None
        if self.file_path and os.path.exists(self.file_path):
            return self.file_path
        tmp_dir = ensure_session_temp()
        fname = f"sdrop_img_{int(time.time() * 1000)}.png"
        out_path = str(tmp_dir / fname)
        self.image.save(out_path, "PNG")
        self.file_path = out_path
        try:
            self.size_bytes = os.path.getsize(out_path)
        except Exception:
            pass
        return out_path

    def to_dict(self) -> Optional[dict]:
        """Serializable representation for session persistence."""
        if self.kind == "file" and self.file_path and os.path.exists(self.file_path):
            return {
                "kind": "file",
                "title": self.title,
                "subtitle": self.subtitle,
                "file_path": self.file_path,
                "size_bytes": self.size_bytes,
            }
        if self.kind == "url" and self.url:
            return {"kind": "url", "title": self.title, "subtitle": self.subtitle, "url": self.url}
        if self.kind == "text" and self.text:
            return {"kind": "text", "title": self.title, "subtitle": self.subtitle, "text": self.text}
        return None


def build_mime_for_entries(entries: List[ShelfEntry]) -> QMimeData:
    """Packages one or more ShelfEntries into native Windows QMimeData (files, images, URLs, text)."""
    mime = QMimeData()
    urls: List[QUrl] = []
    texts: List[str] = []
    first_image: Optional[QImage] = None

    for e in entries:
        if e.kind == "file" and e.file_path and os.path.exists(e.file_path):
            urls.append(QUrl.fromLocalFile(e.file_path))
            texts.append(e.file_path)
        elif e.kind == "image" and e.image is not None and not e.image.isNull():
            img_path = e.ensure_temp_image_file()
            if img_path:
                urls.append(QUrl.fromLocalFile(img_path))
            if first_image is None:
                first_image = e.image
        elif e.kind == "url" and e.url:
            urls.append(QUrl(e.url))
            texts.append(e.url)
        elif e.kind == "text" and e.text:
            texts.append(e.text)

    if urls:
        mime.setUrls(urls)
    if first_image is not None and len(entries) == 1:
        mime.setImageData(first_image)
    if texts:
        mime.setText("\n".join(texts))
    return mime


class GlobalHotkeyFilter(QAbstractNativeEventFilter):
    """Receives native Win32 WM_HOTKEY events even when the shelf window is hidden."""

    def __init__(self, on_triggered):
        super().__init__()
        self.on_triggered = on_triggered

    def nativeEventFilter(self, eventType, message):
        if sys.platform == "win32" and eventType in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            try:
                ptr = int(message)
                if ptr:
                    msg = wintypes.MSG.from_address(ptr)
                    if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_TOGGLE_ID:
                        self.on_triggered()
                        return True, 0
            except Exception:
                pass
        return False, 0


class ShakeDetector:
    """Detects rapid horizontal mouse shakes while the left mouse button is held down."""

    def __init__(self, on_shake_detected, sensitivity: str = "Medium"):
        self.on_shake_detected = on_shake_detected
        self._dragging = False
        self._last_x = 0
        self._last_dir = 0
        self._reversals: List[float] = []
        self._last_trigger = 0.0
        self.set_sensitivity(sensitivity)

        self.timer = QTimer()
        self.timer.setInterval(20)  # 50 Hz
        self.timer.timeout.connect(self._poll)
        self.timer.start()

    def set_sensitivity(self, sensitivity: str):
        self.sensitivity = sensitivity if sensitivity in SHAKE_PRESETS else "Medium"
        self.min_dx, self.req_reversals, self.window_sec = SHAKE_PRESETS[self.sensitivity]

    def _poll(self):
        if self.sensitivity == "Off":
            return

        pressed = is_left_button_down()
        pos = get_cursor_pos()

        if pressed and not self._dragging:
            self._dragging = True
            self._last_x = pos.x()
            self._last_dir = 0
            self._reversals.clear()
            return

        if not pressed:
            self._dragging = False
            self._reversals.clear()
            self._last_dir = 0
            return

        dx = pos.x() - self._last_x
        self._last_x = pos.x()

        if abs(dx) < self.min_dx:
            return

        direction = 1 if dx > 0 else -1
        now = time.monotonic()

        if self._last_dir != 0 and direction != self._last_dir:
            self._reversals.append(now)
            self._reversals = [t for t in self._reversals if now - t <= self.window_sec]

            if len(self._reversals) >= self.req_reversals and (now - self._last_trigger) > 1.2:
                self._reversals.clear()
                self._last_trigger = now
                self.on_shake_detected(pos)

        self._last_dir = direction


class ZipWorker(QThread):
    """Background worker that recursively zips files & folders with filename deduplication."""

    finished_zip = pyqtSignal(str, int)
    failed_zip = pyqtSignal(str)

    def __init__(self, paths: List[str]):
        super().__init__()
        self.paths = paths

    def run(self):
        try:
            tmp_dir = ensure_session_temp()
            zip_path = str(tmp_dir / f"SDrop_Bundle_{int(time.time())}.zip")
            used_names = set()
            file_count = 0

            def unique_arcname(candidate: str) -> str:
                norm = candidate.replace("\\", "/")
                if norm not in used_names:
                    used_names.add(norm)
                    return norm
                stem, ext = os.path.splitext(norm)
                idx = 1
                while True:
                    alt = f"{stem} ({idx}){ext}"
                    if alt not in used_names:
                        used_names.add(alt)
                        return alt
                    idx += 1

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for src in self.paths:
                    if not os.path.exists(src):
                        continue
                    if os.path.isfile(src):
                        zf.write(src, arcname=unique_arcname(os.path.basename(src)))
                        file_count += 1
                    elif os.path.isdir(src):
                        base_folder = os.path.basename(os.path.normpath(src)) or "folder"
                        for root, _, files in os.walk(src):
                            for fn in files:
                                full = os.path.join(root, fn)
                                rel = os.path.relpath(full, src)
                                arc = unique_arcname(os.path.join(base_folder, rel))
                                zf.write(full, arcname=arc)
                                file_count += 1

            if file_count == 0:
                self.failed_zip.emit("No readable files found to zip.")
                return
            self.finished_zip.emit(zip_path, file_count)
        except Exception as exc:
            self.failed_zip.emit(str(exc))


class PreviewDialog(QDialog):
    """Lightweight Quick Preview popup triggered by Spacebar."""

    def __init__(self, entry: ShelfEntry, accent_hex: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Preview — {entry.title}")
        self.resize(480, 420)
        self.setStyleSheet(f"""
            QDialog {{ background-color: #0B0F19; color: #F8FAFC; border: 1px solid {accent_hex}; }}
            QLabel {{ color: #E2E8F0; font-family: "Segoe UI"; }}
            QTextEdit {{ background-color: #111827; color: #F1F5F9; border: 1px solid #334155; border-radius: 8px; padding: 8px; font-family: Consolas, monospace; font-size: 12px; }}
            QPushButton {{ background-color: #1E293B; color: #F8FAFC; border: 1px solid {accent_hex}; border-radius: 6px; padding: 6px 14px; font-weight: 600; }}
            QPushButton:hover {{ background-color: {accent_hex}; color: #0B0F19; }}
        """)

        layout = QVBoxLayout(self)
        header = QLabel(f"<b>{entry.title}</b><br><span style='color:#94A3B8;font-size:11px;'>{entry.subtitle}</span>")
        header.setWordWrap(True)
        layout.addWidget(header)

        img: Optional[QImage] = None
        if entry.kind == "image" and entry.image is not None:
            img = entry.image
        elif entry.kind == "file" and entry.file_path and os.path.isfile(entry.file_path):
            ext = Path(entry.file_path).suffix.lower()
            if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico"}:
                loaded = QImage(entry.file_path)
                if not loaded.isNull():
                    img = loaded

        if img is not None:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setPixmap(QPixmap.fromImage(img).scaled(440, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            scroll.setWidget(lbl)
            layout.addWidget(scroll, 1)
        elif entry.kind == "text" and entry.text:
            te = QTextEdit()
            te.setReadOnly(True)
            te.setPlainText(entry.text)
            layout.addWidget(te, 1)
        else:
            info = QTextEdit()
            info.setReadOnly(True)
            details = [f"Type: {entry.kind.upper()}"]
            if entry.file_path:
                details.append(f"Path: {entry.file_path}")
                if os.path.exists(entry.file_path):
                    st = os.stat(entry.file_path)
                    details.append(f"Size: {format_size(st.st_size)}")
                    details.append(f"Modified: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))}")
            elif entry.url:
                details.append(f"URL: {entry.url}")
            info.setPlainText("\n".join(details))
            layout.addWidget(info, 1)

        close_btn = QPushButton("Close (Esc / Space)")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Escape):
            self.accept()
            return
        super().keyPressEvent(event)


class SettingsDialog(QDialog):
    """Purposeful, clutter-free customization dialog for SDrop."""

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.cfg = dict(cfg)
        self.setWindowTitle(f"{APP_NAME} Settings — {APP_PUBLISHER}")
        self.setMinimumWidth(390)

        accent = NEON_THEMES.get(cfg.get("theme", "Electric Cyan"), NEON_THEMES["Electric Cyan"])[0]
        self.setStyleSheet(f"""
            QDialog {{ background-color: #0B0F19; color: #F8FAFC; font-family: "Segoe UI"; }}
            QLabel {{ color: #E2E8F0; font-size: 12px; }}
            QComboBox {{ background-color: #111827; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 5px 8px; }}
            QComboBox:hover {{ border-color: {accent}; }}
            QCheckBox {{ color: #E2E8F0; spacing: 8px; font-size: 12px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid #475569; background: #111827; }}
            QCheckBox::indicator:checked {{ background-color: {accent}; border-color: {accent}; }}
            QPushButton {{ background-color: #1E293B; color: #F8FAFC; border: 1px solid #334155; border-radius: 7px; padding: 7px 14px; font-weight: 600; }}
            QPushButton#SaveBtn {{ background-color: {accent}; color: #0B0F19; border: none; }}
            QPushButton#SaveBtn:hover {{ background-color: #F8FAFC; }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.theme_cb = QComboBox()
        self.theme_cb.addItems(list(NEON_THEMES.keys()))
        self.theme_cb.setCurrentText(cfg.get("theme", "Electric Cyan"))
        form.addRow("Neon Accent Theme:", self.theme_cb)

        opacity_row = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(70, 100)
        self.opacity_slider.setValue(int(cfg.get("opacity", 96)))
        self.opacity_lbl = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_lbl.setText(f"{v}%"))
        opacity_row.addWidget(self.opacity_slider, 1)
        opacity_row.addWidget(self.opacity_lbl)
        form.addRow("Window Opacity:", opacity_row)

        self.shake_cb = QComboBox()
        self.shake_cb.addItems(list(SHAKE_PRESETS.keys()))
        self.shake_cb.setCurrentText(cfg.get("shake_sensitivity", "Medium"))
        form.addRow("Shake-to-Summon:", self.shake_cb)

        self.hotkey_cb = QComboBox()
        self.hotkey_cb.addItems(list(HOTKEY_PRESETS.keys()))
        self.hotkey_cb.setCurrentText(cfg.get("hotkey", "Win + Alt + D"))
        form.addRow("Global Hotkey:", self.hotkey_cb)

        self.drag_cb = QComboBox()
        self.drag_cb.addItems(["Copy (Safe Default)", "Move (Same Drive)"])
        self.drag_cb.setCurrentIndex(1 if cfg.get("drag_action") == "move" else 0)
        form.addRow("Default Drag-Out:", self.drag_cb)

        layout.addLayout(form)

        # Behavior checkboxes
        self.chk_top = QCheckBox("Keep shelf Always on Top by default")
        self.chk_top.setChecked(bool(cfg.get("always_on_top", True)))
        layout.addWidget(self.chk_top)

        self.chk_auto_remove = QCheckBox("Auto-remove items from shelf after dragging out")
        self.chk_auto_remove.setChecked(bool(cfg.get("auto_remove_after_drag", False)))
        layout.addWidget(self.chk_auto_remove)

        self.chk_auto_hide = QCheckBox("Auto-hide shelf when emptied")
        self.chk_auto_hide.setChecked(bool(cfg.get("auto_hide_when_empty", False)))
        layout.addWidget(self.chk_auto_hide)

        self.chk_snap = QCheckBox("Snap shelf smoothly to screen edges")
        self.chk_snap.setChecked(bool(cfg.get("snap_to_edges", True)))
        layout.addWidget(self.chk_snap)

        self.chk_persist = QCheckBox("Remember shelf items across restarts")
        self.chk_persist.setChecked(bool(cfg.get("persist_session", True)))
        layout.addWidget(self.chk_persist)

        self.chk_startup = QCheckBox("Start SDrop automatically with Windows")
        self.chk_startup.setChecked(bool(cfg.get("start_with_windows", False)))
        layout.addWidget(self.chk_startup)

        # Footer buttons
        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save & Apply")
        save_btn.setObjectName("SaveBtn")
        save_btn.clicked.connect(self._save)
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _save(self):
        self.cfg["theme"] = self.theme_cb.currentText()
        self.cfg["opacity"] = self.opacity_slider.value()
        self.cfg["shake_sensitivity"] = self.shake_cb.currentText()
        self.cfg["hotkey"] = self.hotkey_cb.currentText()
        self.cfg["drag_action"] = "move" if self.drag_cb.currentIndex() == 1 else "copy"
        self.cfg["always_on_top"] = self.chk_top.isChecked()
        self.cfg["auto_remove_after_drag"] = self.chk_auto_remove.isChecked()
        self.cfg["auto_hide_when_empty"] = self.chk_auto_hide.isChecked()
        self.cfg["snap_to_edges"] = self.chk_snap.isChecked()
        self.cfg["persist_session"] = self.chk_persist.isChecked()
        self.cfg["start_with_windows"] = self.chk_startup.isChecked()
        self.accept()


class ShelfListWidget(QListWidget):
    """Supports dragging selected items out with safe Copy/Move semantics."""

    dragCompleted = pyqtSignal(list)

    def __init__(self, get_cfg_fn, parent=None):
        super().__init__(parent)
        self.get_cfg_fn = get_cfg_fn
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setIconSize(QSize(28, 28))
        self.setSpacing(5)

    def startDrag(self, supportedActions):
        selected = self.selectedIndexes()
        if not selected:
            return

        rows = sorted({idx.row() for idx in selected})
        entries: List[ShelfEntry] = []
        for r in rows:
            entry = self.item(r).data(Qt.ItemDataRole.UserRole)
            if isinstance(entry, ShelfEntry):
                entries.append(entry)

        if not entries:
            return

        cfg = self.get_cfg_fn()
        accent = NEON_THEMES.get(cfg.get("theme", "Electric Cyan"), NEON_THEMES["Electric Cyan"])[0]
        mime = build_mime_for_entries(entries)

        drag = QDrag(self)
        drag.setMimeData(mime)

        badge = QPixmap(190, 38)
        badge.fill(Qt.GlobalColor.transparent)
        p = QPainter(badge)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#0B0F19"))
        p.setPen(QPen(QColor(accent), 2))
        p.drawRoundedRect(1, 1, 188, 36, 10, 10)
        p.setPen(QColor("#F8FAFC"))
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        mode_tag = "Move" if cfg.get("drag_action") == "move" else "Copy"
        label = f"{mode_tag} {len(entries)} item{'s' if len(entries) > 1 else ''}"
        p.drawText(badge.rect(), Qt.AlignmentFlag.AlignCenter, label)
        p.end()

        drag.setPixmap(badge)
        drag.setHotSpot(QPoint(20, 19))

        if cfg.get("drag_action") == "move":
            result = drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, Qt.DropAction.MoveAction)
        else:
            result = drag.exec(Qt.DropAction.CopyAction, Qt.DropAction.CopyAction)

        if result != Qt.DropAction.IgnoreAction:
            self.dragCompleted.emit(rows)


class DragAllButton(QPushButton):
    """Drag handle that drags EVERY item on the active shelf (files, folders, images, links, text)."""

    allDraggedOut = pyqtSignal()

    def __init__(self, get_entries_fn, get_cfg_fn, parent=None):
        super().__init__("Drag All", parent)
        self.get_entries_fn = get_entries_fn
        self.get_cfg_fn = get_cfg_fn
        self._press_pos: Optional[QPoint] = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._press_pos is not None
            and (event.pos() - self._press_pos).manhattanLength() >= QApplication.startDragDistance()
        ):
            self._press_pos = None
            entries = self.get_entries_fn()
            if not entries:
                return
            cfg = self.get_cfg_fn()
            mime = build_mime_for_entries(entries)
            drag = QDrag(self)
            drag.setMimeData(mime)

            if cfg.get("drag_action") == "move":
                res = drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, Qt.DropAction.MoveAction)
            else:
                res = drag.exec(Qt.DropAction.CopyAction, Qt.DropAction.CopyAction)

            if res != Qt.DropAction.IgnoreAction:
                self.allDraggedOut.emit()
            return
        super().mouseMoveEvent(event)


class ShelfTabData:
    def __init__(self, name: str):
        self.name = name
        self.entries: List[ShelfEntry] = []
        self.undo_stack: List[List[ShelfEntry]] = []


class SDropShelfWindow(QWidget):
    settingsChanged = pyqtSignal(dict)

    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.tabs: List[ShelfTabData] = [ShelfTabData("Main")]
        self.active_tab_idx = 0
        self.icon_provider = QFileIconProvider()
        self._drag_offset: Optional[QPoint] = None
        self._pinned = bool(cfg.get("always_on_top", True))
        self._zip_worker: Optional[ZipWorker] = None

        self.setWindowTitle(f"{APP_NAME} — {APP_PUBLISHER}")
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(368, 460)
        self.setMinimumSize(320, 300)

        self._apply_window_flags()
        self._build_ui()
        self.apply_config(cfg)

    def _apply_window_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)  # Room for outer neon glow

        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        outer.addWidget(self.container)

        self.glow = QGraphicsDropShadowEffect(self)
        self.glow.setBlurRadius(24)
        self.glow.setOffset(0, 0)
        self.container.setGraphicsEffect(self.glow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header Row
        header = QHBoxLayout()
        header.setSpacing(6)

        self.title_lbl = QLabel("SDROP")
        self.title_lbl.setObjectName("TitleLabel")
        header.addWidget(self.title_lbl)

        self.count_lbl = QLabel("0")
        self.count_lbl.setObjectName("CountBadge")
        header.addWidget(self.count_lbl)

        header.addStretch()

        self.pin_btn = QPushButton("Pin")
        self.pin_btn.setObjectName("HeaderBtn")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(self._pinned)
        self.pin_btn.setToolTip("Keep shelf always on top")
        self.pin_btn.clicked.connect(self._toggle_pin)
        header.addWidget(self.pin_btn)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("HeaderBtn")
        settings_btn.setToolTip("Settings & Neon Customization")
        settings_btn.clicked.connect(self._open_settings)
        header.addWidget(settings_btn)

        hide_btn = QPushButton("✕")
        hide_btn.setObjectName("CloseBtn")
        hide_btn.setToolTip("Hide to system tray (items stay saved)")
        hide_btn.clicked.connect(self.hide)
        header.addWidget(hide_btn)

        layout.addLayout(header)

        # Multi-Shelf Tab Bar Row
        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)

        self.tab_bar = QTabBar()
        self.tab_bar.setObjectName("ShelfTabs")
        self.tab_bar.setExpanding(False)
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.addTab("Main")
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.tabCloseRequested.connect(self._close_tab)
        self.tab_bar.tabBarDoubleClicked.connect(self._rename_tab)
        tab_row.addWidget(self.tab_bar, 1)

        add_tab_btn = QPushButton("+")
        add_tab_btn.setObjectName("AddTabBtn")
        add_tab_btn.setFixedSize(26, 24)
        add_tab_btn.setToolTip("New shelf tab")
        add_tab_btn.clicked.connect(self._add_new_tab)
        tab_row.addWidget(add_tab_btn)

        layout.addLayout(tab_row)

        # Empty Drop Zone
        self.empty_zone = QLabel(
            "Drop files, folders, browser images,\nlinks, or press Ctrl+V to paste.\n\n"
            "Shake mouse while dragging any file\nor press your global hotkey to summon."
        )
        self.empty_zone.setObjectName("EmptyZone")
        self.empty_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_zone.setWordWrap(True)
        layout.addWidget(self.empty_zone, 1)

        # Item List
        self.list_widget = ShelfListWidget(lambda: self.cfg)
        self.list_widget.setObjectName("ShelfList")
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_item_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.dragCompleted.connect(self._on_items_dragged_out)
        self.list_widget.hide()
        layout.addWidget(self.list_widget, 1)

        # Status / Stats Line
        self.status_lbl = QLabel("Ready • Copy mode")
        self.status_lbl.setObjectName("StatusLabel")
        layout.addWidget(self.status_lbl)

        # Action Row 1 (Primary)
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self.drag_all_btn = DragAllButton(lambda: self._current_tab().entries, lambda: self.cfg)
        self.drag_all_btn.setObjectName("PrimaryBtn")
        self.drag_all_btn.setToolTip("Click & drag this button to drop all items at once")
        self.drag_all_btn.allDraggedOut.connect(self._on_all_dragged_out)
        row1.addWidget(self.drag_all_btn, 1)

        self.zip_btn = QPushButton("Zip All")
        self.zip_btn.setObjectName("SecondaryBtn")
        self.zip_btn.setToolTip("Bundle stacked files & folders into a ZIP on the shelf")
        self.zip_btn.clicked.connect(self._zip_all_files)
        row1.addWidget(self.zip_btn)

        self.copy_folder_btn = QPushButton("To Folder")
        self.copy_folder_btn.setObjectName("SecondaryBtn")
        self.copy_folder_btn.setToolTip("Copy all stacked files/folders into a chosen folder")
        self.copy_folder_btn.clicked.connect(self._copy_all_to_folder)
        row1.addWidget(self.copy_folder_btn)

        layout.addLayout(row1)

        # Action Row 2 (Quick Utility)
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        paste_btn = QPushButton("Paste")
        paste_btn.setObjectName("SubtleBtn")
        paste_btn.setToolTip("Paste clipboard image, file, link, or text (Ctrl+V)")
        paste_btn.clicked.connect(self._paste_clipboard)
        row2.addWidget(paste_btn)

        copy_paths_btn = QPushButton("Copy Paths")
        copy_paths_btn.setObjectName("SubtleBtn")
        copy_paths_btn.setToolTip("Copy all file paths / URLs on this shelf")
        copy_paths_btn.clicked.connect(self._copy_all_paths)
        row2.addWidget(copy_paths_btn)

        undo_btn = QPushButton("Undo")
        undo_btn.setObjectName("SubtleBtn")
        undo_btn.setToolTip("Undo last removal or clear (Ctrl+Z)")
        undo_btn.clicked.connect(self._undo)
        row2.addWidget(undo_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("DangerBtn")
        clear_btn.clicked.connect(self.clear_current_tab)
        row2.addWidget(clear_btn)

        layout.addLayout(row2)

    def apply_config(self, cfg: dict):
        self.cfg = cfg
        theme_name = cfg.get("theme", "Electric Cyan")
        accent, _, dark_tint = NEON_THEMES.get(theme_name, NEON_THEMES["Electric Cyan"])

        self.setWindowOpacity(max(0.7, min(1.0, cfg.get("opacity", 96) / 100.0)))
        self.setWindowIcon(QIcon(create_app_pixmap(64, accent)))
        self.glow.setColor(QColor(accent))

        self._base_stylesheet = f"""
            #MainContainer {{
                background-color: #0B0F19;
                border: 1.5px solid {accent};
                border-radius: 14px;
            }}
            #TitleLabel {{
                color: {accent};
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 1.5px;
            }}
            #CountBadge {{
                background-color: {dark_tint};
                color: {accent};
                border: 1px solid {accent};
                font-family: "Segoe UI";
                font-size: 11px;
                font-weight: 700;
                padding: 1px 7px;
                border-radius: 9px;
            }}
            #HeaderBtn, #CloseBtn, #AddTabBtn {{
                background-color: #131B2E;
                color: #CBD5E1;
                border: 1px solid #26324B;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            #HeaderBtn:hover, #AddTabBtn:hover {{
                border-color: {accent};
                color: {accent};
            }}
            #HeaderBtn:checked {{
                background-color: {dark_tint};
                color: {accent};
                border-color: {accent};
            }}
            #CloseBtn:hover {{
                background-color: #DC2626;
                color: #FFFFFF;
                border-color: #EF4444;
            }}
            QTabBar#ShelfTabs::tab {{
                background-color: #131B2E;
                color: #94A3B8;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 3px 10px;
                margin-right: 4px;
                font-size: 11px;
                font-weight: 600;
            }}
            QTabBar#ShelfTabs::tab:selected {{
                background-color: {dark_tint};
                color: {accent};
                border-color: {accent};
            }}
            #EmptyZone {{
                color: #94A3B8;
                background-color: #0F1626;
                border: 1.5px dashed #334155;
                border-radius: 10px;
                font-family: "Segoe UI";
                font-size: 12px;
                padding: 16px;
            }}
            #ShelfList {{
                background-color: #0F1626;
                border: 1px solid #1E293B;
                border-radius: 10px;
                padding: 4px;
                color: #F1F5F9;
                font-family: "Segoe UI";
                font-size: 12px;
                outline: none;
            }}
            #ShelfList::item {{
                background-color: #131B2E;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 6px 8px;
            }}
            #ShelfList::item:hover {{
                border-color: {accent};
            }}
            #ShelfList::item:selected {{
                background-color: {dark_tint};
                border: 1px solid {accent};
                color: #FFFFFF;
            }}
            #StatusLabel {{
                color: #64748B;
                font-family: "Segoe UI";
                font-size: 11px;
            }}
            #PrimaryBtn {{
                background-color: {accent};
                color: #0B0F19;
                border: none;
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: 800;
                font-size: 12px;
            }}
            #PrimaryBtn:hover {{
                background-color: #F8FAFC;
                color: #0B0F19;
            }}
            #SecondaryBtn {{
                background-color: #131B2E;
                color: #E2E8F0;
                border: 1px solid #26324B;
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
            #SecondaryBtn:hover {{
                border-color: {accent};
                color: {accent};
            }}
            #SubtleBtn {{
                background-color: #0F1626;
                color: #94A3B8;
                border: 1px solid #1E293B;
                border-radius: 7px;
                padding: 5px 8px;
                font-size: 11px;
            }}
            #SubtleBtn:hover {{
                color: #F8FAFC;
                border-color: {accent};
            }}
            #DangerBtn {{
                background-color: #0F1626;
                color: #FCA5A5;
                border: 1px solid #3B1D26;
                border-radius: 7px;
                padding: 5px 10px;
                font-size: 11px;
            }}
            #DangerBtn:hover {{
                background-color: #7F1D1D;
                color: #FFFFFF;
                border-color: #EF4444;
            }}
        """
        self.setStyleSheet(self._base_stylesheet)
        self._sync_ui_state()

    # --- Tab Management ---
    def _current_tab(self) -> ShelfTabData:
        self.active_tab_idx = max(0, min(self.active_tab_idx, len(self.tabs) - 1))
        return self.tabs[self.active_tab_idx]

    def _add_new_tab(self):
        name = f"Shelf {len(self.tabs) + 1}"
        self.tabs.append(ShelfTabData(name))
        idx = self.tab_bar.addTab(name)
        self.tab_bar.setCurrentIndex(idx)
        self._save_session()

    def _close_tab(self, index: int):
        if len(self.tabs) <= 1:
            self.clear_current_tab()
            return
        self.tabs.pop(index)
        self.tab_bar.removeTab(index)
        self.active_tab_idx = self.tab_bar.currentIndex()
        self._rebuild_list_widget()
        self._save_session()

    def _rename_tab(self, index: int):
        if index < 0 or index >= len(self.tabs):
            return
        new_name, ok = QInputDialog.getText(self, "Rename Shelf", "Shelf name:", text=self.tabs[index].name)
        if ok and new_name.strip():
            self.tabs[index].name = new_name.strip()[:24]
            self.tab_bar.setTabText(index, self.tabs[index].name)
            self._save_session()

    def _on_tab_changed(self, index: int):
        if 0 <= index < len(self.tabs):
            self.active_tab_idx = index
            self._rebuild_list_widget()

    # --- Frameless Drag + Edge Snap ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 54:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_offset is not None and self.cfg.get("snap_to_edges", True):
            self._snap_to_nearest_edge()
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def _snap_to_nearest_edge(self):
        screen = QGuiApplication.screenAt(self.frameGeometry().center()) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x, y = self.x(), self.y()
        threshold = 28
        if abs(x - geo.left()) <= threshold:
            x = geo.left()
        elif abs((x + self.width()) - geo.right()) <= threshold:
            x = geo.right() - self.width()
        if abs(y - geo.top()) <= threshold:
            y = geo.top()
        elif abs((y + self.height()) - geo.bottom()) <= threshold:
            y = geo.bottom() - self.height()
        self.move(x, y)

    # --- Drag & Drop Ingestion ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage() or event.mimeData().hasText():
            accent = NEON_THEMES.get(self.cfg.get("theme", "Electric Cyan"), NEON_THEMES["Electric Cyan"])[0]
            self.glow.setBlurRadius(36)
            self.container.setStyleSheet(
                f"#MainContainer {{ background-color: #0B0F19; border: 2.5px solid {accent}; border-radius: 14px; }}"
            )
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.glow.setBlurRadius(24)
        self.container.setStyleSheet("")

    def dropEvent(self, event):
        self.glow.setBlurRadius(24)
        self.container.setStyleSheet("")
        self._ingest_mime(event.mimeData())
        event.acceptProposedAction()

    def keyPressEvent(self, event):
        mods = event.modifiers()
        if mods == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_V:
            self._paste_clipboard()
            return
        if mods == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C:
            self._copy_selected_to_clipboard()
            return
        if mods == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Z:
            self._undo()
            return
        if event.key() == Qt.Key.Key_Delete:
            self._remove_selected()
            return
        if event.key() == Qt.Key.Key_Space:
            self._preview_selected()
            return
        super().keyPressEvent(event)

    def _push_undo(self):
        tab = self._current_tab()
        tab.undo_stack.append(list(tab.entries))
        if len(tab.undo_stack) > 20:
            tab.undo_stack.pop(0)

    def _undo(self):
        tab = self._current_tab()
        if not tab.undo_stack:
            self.status_lbl.setText("Nothing to undo")
            return
        tab.entries = tab.undo_stack.pop()
        self._rebuild_list_widget()
        self._save_session()
        self.status_lbl.setText("Undid last change")

    def _paste_clipboard(self):
        cb = QApplication.clipboard()
        if cb and cb.mimeData():
            self._ingest_mime(cb.mimeData())

    def _copy_selected_to_clipboard(self):
        items = self.list_widget.selectedItems()
        if not items:
            return
        entries = [it.data(Qt.ItemDataRole.UserRole) for it in items if isinstance(it.data(Qt.ItemDataRole.UserRole), ShelfEntry)]
        if entries:
            QApplication.clipboard().setMimeData(build_mime_for_entries(entries))
            self.status_lbl.setText(f"Copied {len(entries)} item(s) to clipboard")

    def _ingest_mime(self, mime: QMimeData):
        tab = self._current_tab()
        added = 0

        # 1. Local files/folders take top priority
        local_urls = [u for u in mime.urls() if u.isLocalFile()] if mime.hasUrls() else []
        if local_urls:
            self._push_undo()
            for url in local_urls:
                path = url.toLocalFile()
                if any(e.file_path == path for e in tab.entries):
                    continue
                p = Path(path)
                sz = p.stat().st_size if p.is_file() else 0
                size_str = format_size(sz) if p.is_file() else "Folder"
                entry = ShelfEntry(
                    kind="file",
                    title=p.name or path,
                    subtitle=f"{size_str} • {p.parent}",
                    file_path=path,
                    size_bytes=sz,
                )
                tab.entries.append(entry)
                self._append_widget_item(entry)
                added += 1

        # 2. Browser / clipboard images (checked BEFORE web URLs so Chrome/Edge image drags capture the bitmap)
        elif mime.hasImage():
            img = QImage(mime.imageData())
            if not img.isNull():
                self._push_undo()
                src_note = "Clipboard / Web Image"
                if mime.hasUrls():
                    web_urls = [u.toString() for u in mime.urls() if not u.isLocalFile()]
                    if web_urls:
                        src_note = web_urls[0][:42]
                entry = ShelfEntry(
                    kind="image",
                    title=f"Image ({img.width()}×{img.height()})",
                    subtitle=src_note,
                    image=img,
                )
                tab.entries.append(entry)
                self._append_widget_item(entry)
                added += 1

        # 3. Web links
        elif mime.hasUrls():
            self._push_undo()
            for url in mime.urls():
                u = url.toString()
                if any(e.url == u for e in tab.entries):
                    continue
                entry = ShelfEntry(kind="url", title=u[:56], subtitle="Web Link", url=u)
                tab.entries.append(entry)
                self._append_widget_item(entry)
                added += 1

        # 4. Plain text snippets
        elif mime.hasText():
            txt = mime.text().strip()
            if txt:
                self._push_undo()
                first_line = txt.splitlines()[0][:50]
                entry = ShelfEntry(
                    kind="text",
                    title=first_line,
                    subtitle=f"Text snippet • {len(txt)} chars",
                    text=txt,
                )
                tab.entries.append(entry)
                self._append_widget_item(entry)
                added += 1

        if added:
            self._sync_ui_state()
            self._save_session()

    def _append_widget_item(self, entry: ShelfEntry):
        accent = NEON_THEMES.get(self.cfg.get("theme", "Electric Cyan"), NEON_THEMES["Electric Cyan"])[0]
        item = QListWidgetItem(f"{entry.title}\n{entry.subtitle}")
        item.setData(Qt.ItemDataRole.UserRole, entry)

        if entry.kind == "file" and entry.file_path and os.path.exists(entry.file_path):
            ext = Path(entry.file_path).suffix.lower()
            if ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
                pm = QPixmap(entry.file_path)
                if not pm.isNull():
                    item.setIcon(QIcon(pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
                else:
                    item.setIcon(self.icon_provider.icon(QFileInfo(entry.file_path)))
            else:
                item.setIcon(self.icon_provider.icon(QFileInfo(entry.file_path)))
        elif entry.kind == "image" and entry.image is not None:
            item.setIcon(QIcon(QPixmap.fromImage(entry.image).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
        else:
            item.setIcon(QIcon(create_app_pixmap(32, accent)))

        self.list_widget.addItem(item)

    def _rebuild_list_widget(self):
        self.list_widget.clear()
        for entry in self._current_tab().entries:
            self._append_widget_item(entry)
        self._sync_ui_state()

    def _sync_ui_state(self):
        entries = self._current_tab().entries
        count = len(entries)
        total_bytes = sum(e.size_bytes for e in entries)
        self.count_lbl.setText(str(count))
        has_items = count > 0
        self.empty_zone.setVisible(not has_items)
        self.list_widget.setVisible(has_items)

        mode = "Move mode" if self.cfg.get("drag_action") == "move" else "Copy mode"
        if has_items:
            size_info = f" • {format_size(total_bytes)}" if total_bytes > 0 else ""
            self.status_lbl.setText(f"{count} item{'s' if count != 1 else ''}{size_info} • {mode} • Space to preview")
        else:
            self.status_lbl.setText(f"Ready • {mode}")

    # --- Item Actions ---
    def _on_items_dragged_out(self, rows: List[int]):
        if self.cfg.get("auto_remove_after_drag", False) or self.cfg.get("drag_action") == "move":
            tab = self._current_tab()
            self._push_undo()
            for r in sorted(rows, reverse=True):
                if 0 <= r < len(tab.entries):
                    tab.entries.pop(r)
            self._rebuild_list_widget()
            self._save_session()
            if not tab.entries and self.cfg.get("auto_hide_when_empty", False):
                self.hide()

    def _on_all_dragged_out(self):
        if self.cfg.get("auto_remove_after_drag", False) or self.cfg.get("drag_action") == "move":
            self.clear_current_tab()
            if self.cfg.get("auto_hide_when_empty", False):
                self.hide()

    def _remove_selected(self):
        selected = self.list_widget.selectedIndexes()
        if not selected:
            return
        tab = self._current_tab()
        self._push_undo()
        for r in sorted({i.row() for i in selected}, reverse=True):
            if 0 <= r < len(tab.entries):
                tab.entries.pop(r)
        self._rebuild_list_widget()
        self._save_session()
        if not tab.entries and self.cfg.get("auto_hide_when_empty", False):
            self.hide()

    def clear_current_tab(self):
        tab = self._current_tab()
        if not tab.entries:
            return
        self._push_undo()
        tab.entries.clear()
        self._rebuild_list_widget()
        self._save_session()

    def _preview_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(entry, ShelfEntry):
            accent = NEON_THEMES.get(self.cfg.get("theme", "Electric Cyan"), NEON_THEMES["Electric Cyan"])[0]
            PreviewDialog(entry, accent, self).exec()

    def _on_item_double_clicked(self, item: QListWidgetItem):
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(entry, ShelfEntry):
            return
        if entry.kind == "file" and entry.file_path and os.path.exists(entry.file_path):
            if sys.platform == "win32":
                os.startfile(entry.file_path)
        elif entry.kind == "url" and entry.url:
            if sys.platform == "win32":
                os.startfile(entry.url)
        else:
            self._preview_selected()

    def _copy_all_paths(self):
        lines = []
        for e in self._current_tab().entries:
            if e.file_path:
                lines.append(e.file_path)
            elif e.url:
                lines.append(e.url)
            elif e.text:
                lines.append(e.text)
        if lines:
            QApplication.clipboard().setText("\n".join(lines))
            self.status_lbl.setText(f"Copied {len(lines)} path(s)/item(s)")

    def _copy_all_to_folder(self):
        paths = [e.file_path for e in self._current_tab().entries if e.kind == "file" and e.file_path and os.path.exists(e.file_path)]
        for e in self._current_tab().entries:
            if e.kind == "image" and e.image is not None:
                p = e.ensure_temp_image_file()
                if p:
                    paths.append(p)
        if not paths:
            self.status_lbl.setText("No files or images to copy")
            return

        dest = QFileDialog.getExistingDirectory(self, "Choose Destination Folder")
        if not dest:
            return

        copied = 0
        for src in paths:
            try:
                name = os.path.basename(os.path.normpath(src))
                target = os.path.join(dest, name)
                if os.path.isdir(src):
                    shutil.copytree(src, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, target)
                copied += 1
            except Exception:
                pass
        self.status_lbl.setText(f"Copied {copied} item(s) to {os.path.basename(dest) or dest}")

    def _zip_all_files(self):
        if self._zip_worker and self._zip_worker.isRunning():
            return
        paths = []
        for e in self._current_tab().entries:
            if e.kind == "file" and e.file_path and os.path.exists(e.file_path):
                paths.append(e.file_path)
            elif e.kind == "image" and e.image is not None:
                p = e.ensure_temp_image_file()
                if p:
                    paths.append(p)
        if not paths:
            self.status_lbl.setText("No files or images to zip")
            return

        self.zip_btn.setEnabled(False)
        self.zip_btn.setText("Zipping...")
        self.status_lbl.setText("Compressing files in background...")

        self._zip_worker = ZipWorker(paths)
        self._zip_worker.finished_zip.connect(self._on_zip_finished)
        self._zip_worker.failed_zip.connect(self._on_zip_failed)
        self._zip_worker.start()

    def _on_zip_finished(self, zip_path: str, file_count: int):
        self.zip_btn.setEnabled(True)
        self.zip_btn.setText("Zip All")
        p = Path(zip_path)
        sz = p.stat().st_size if p.exists() else 0
        tab = self._current_tab()
        self._push_undo()
        entry = ShelfEntry(
            kind="file",
            title=p.name,
            subtitle=f"{format_size(sz)} • Zipped ({file_count} files)",
            file_path=zip_path,
            size_bytes=sz,
        )
        tab.entries.append(entry)
        self._append_widget_item(entry)
        self._sync_ui_state()
        self.status_lbl.setText(f"Created {p.name}")

    def _on_zip_failed(self, err: str):
        self.zip_btn.setEnabled(True)
        self.zip_btn.setText("Zip All")
        self.status_lbl.setText(f"Zip failed: {err}")

    def _convert_image_entry(self, entry: ShelfEntry, fmt: str):
        img: Optional[QImage] = None
        base_name = "sdrop_image"
        if entry.kind == "image" and entry.image is not None:
            img = entry.image
        elif entry.kind == "file" and entry.file_path and os.path.isfile(entry.file_path):
            loaded = QImage(entry.file_path)
            if not loaded.isNull():
                img = loaded
                base_name = Path(entry.file_path).stem
        if img is None or img.isNull():
            return

        ext = fmt.lower()
        out_path = str(ensure_session_temp() / f"{base_name}_converted_{int(time.time())}.{ext}")
        quality = 90 if ext == "jpg" else -1
        qt_fmt = "JPEG" if ext == "jpg" else fmt.upper()
        if img.save(out_path, qt_fmt, quality):
            p = Path(out_path)
            sz = p.stat().st_size
            new_entry = ShelfEntry(
                kind="file",
                title=p.name,
                subtitle=f"{format_size(sz)} • Converted {fmt.upper()}",
                file_path=out_path,
                size_bytes=sz,
            )
            self._current_tab().entries.append(new_entry)
            self._append_widget_item(new_entry)
            self._sync_ui_state()
            self.status_lbl.setText(f"Converted to {p.name}")

    def _show_item_menu(self, pos: QPoint):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        entry: ShelfEntry = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        preview_act = menu.addAction("Quick Preview (Space)")
        open_act = menu.addAction("Open") if entry.kind in ("file", "url") else None
        reveal_act = menu.addAction("Open Containing Folder") if (entry.kind == "file" and entry.file_path) else None
        copy_act = menu.addAction("Copy to Clipboard (Ctrl+C)")
        copy_path_act = menu.addAction("Copy Path / Text")

        # Non-destructive image conversion submenu
        is_image = entry.kind == "image" or (
            entry.kind == "file"
            and entry.file_path
            and Path(entry.file_path).suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}
        )
        conv_png = conv_jpg = conv_bmp = None
        if is_image:
            conv_menu = menu.addMenu("Convert Image Copy...")
            conv_png = conv_menu.addAction("Export as PNG")
            conv_jpg = conv_menu.addAction("Export as JPG (90%)")
            conv_bmp = conv_menu.addAction("Export as BMP")

        menu.addSeparator()
        remove_act = menu.addAction("Remove from Shelf (Del)")

        chosen = menu.exec(self.list_widget.mapToGlobal(pos))
        if not chosen:
            return
        if chosen == preview_act:
            self._preview_selected()
        elif open_act and chosen == open_act:
            self._on_item_double_clicked(item)
        elif reveal_act and chosen == reveal_act and entry.file_path:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", f"/select,{os.path.normpath(entry.file_path)}"])
        elif chosen == copy_act:
            self._copy_selected_to_clipboard()
        elif chosen == copy_path_act:
            QApplication.clipboard().setText(entry.file_path or entry.url or entry.text or "")
        elif conv_png and chosen == conv_png:
            self._convert_image_entry(entry, "png")
        elif conv_jpg and chosen == conv_jpg:
            self._convert_image_entry(entry, "jpg")
        elif conv_bmp and chosen == conv_bmp:
            self._convert_image_entry(entry, "bmp")
        elif chosen == remove_act:
            self._remove_selected()

    def _toggle_pin(self, checked: bool):
        self._pinned = checked
        self._apply_window_flags()

    def _open_settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            save_config(dlg.cfg)
            set_windows_startup(bool(dlg.cfg.get("start_with_windows", False)))
            self._pinned = bool(dlg.cfg.get("always_on_top", True))
            self.pin_btn.setChecked(self._pinned)
            self._apply_window_flags()
            self.apply_config(dlg.cfg)
            self.settingsChanged.emit(dlg.cfg)

    def summon_near(self, cursor_pos: QPoint):
        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = min(max(geo.left() + 8, cursor_pos.x() + 20), geo.right() - self.width() - 8)
        y = min(max(geo.top() + 8, cursor_pos.y() - self.height() // 2), geo.bottom() - self.height() - 8)
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    # --- Session Persistence ---
    def _save_session(self):
        if not self.cfg.get("persist_session", True):
            return
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            payload = []
            for t in self.tabs:
                items = [d for e in t.entries if (d := e.to_dict()) is not None]
                payload.append({"name": t.name, "items": items})
            tmp = SESSION_FILE.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp, SESSION_FILE)
        except Exception:
            pass

    def load_session(self):
        if not self.cfg.get("persist_session", True) or not SESSION_FILE.exists():
            return
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list) or not data:
                return
            self.tabs.clear()
            while self.tab_bar.count():
                self.tab_bar.removeTab(0)

            for tab_obj in data:
                t = ShelfTabData(str(tab_obj.get("name", "Main")))
                for it in tab_obj.get("items", []):
                    kind = it.get("kind")
                    if kind == "file":
                        fp = it.get("file_path")
                        if fp and os.path.exists(fp):
                            t.entries.append(
                                ShelfEntry(
                                    kind="file",
                                    title=it.get("title", os.path.basename(fp)),
                                    subtitle=it.get("subtitle", ""),
                                    file_path=fp,
                                    size_bytes=int(it.get("size_bytes", 0)),
                                )
                            )
                    elif kind == "url" and it.get("url"):
                        t.entries.append(ShelfEntry(kind="url", title=it.get("title", it["url"]), subtitle="Web Link", url=it["url"]))
                    elif kind == "text" and it.get("text"):
                        t.entries.append(ShelfEntry(kind="text", title=it.get("title", "Snippet"), subtitle=it.get("subtitle", "Text"), text=it["text"]))
                self.tabs.append(t)
                self.tab_bar.addTab(t.name)

            if not self.tabs:
                self.tabs.append(ShelfTabData("Main"))
                self.tab_bar.addTab("Main")

            self.active_tab_idx = 0
            self.tab_bar.setCurrentIndex(0)
            self._rebuild_list_widget()
        except Exception:
            pass


class SDropController:
    def __init__(self, app: QApplication):
        self.app = app
        self.app.setQuitOnLastWindowClosed(False)
        self.cfg = load_config()

        self.shelf = SDropShelfWindow(self.cfg)
        self.shelf.load_session()
        self.shelf.settingsChanged.connect(self._on_settings_changed)

        self.shake_detector = ShakeDetector(self.shelf.summon_near, self.cfg.get("shake_sensitivity", "Medium"))

        # Native Global Hotkey Filter
        self.hotkey_filter = GlobalHotkeyFilter(self._toggle_shelf)
        self.app.installNativeEventFilter(self.hotkey_filter)
        self._register_global_hotkey(self.cfg.get("hotkey", "Win + Alt + D"))

        # System Tray
        accent = NEON_THEMES.get(self.cfg.get("theme", "Electric Cyan"), NEON_THEMES["Electric Cyan"])[0]
        self.tray = QSystemTrayIcon(QIcon(create_app_pixmap(64, accent)), self.app)
        self.tray.setToolTip(f"{APP_NAME} v{APP_VERSION} — {APP_PUBLISHER}")

        menu = QMenu()
        toggle_act = QAction("Show / Hide Shelf", menu)
        toggle_act.triggered.connect(self._toggle_shelf)
        menu.addAction(toggle_act)

        new_tab_act = QAction("New Shelf Tab", menu)
        new_tab_act.triggered.connect(lambda: (self.shelf.summon_near(get_cursor_pos()), self.shelf._add_new_tab()))
        menu.addAction(new_tab_act)

        settings_act = QAction("Settings && Neon Themes...", menu)
        settings_act.triggered.connect(self.shelf._open_settings)
        menu.addAction(settings_act)

        menu.addSeparator()
        about_act = QAction(f"About {APP_NAME} ({APP_PUBLISHER})", menu)
        about_act.triggered.connect(lambda: os.startfile(APP_URL) if sys.platform == "win32" else None)
        menu.addAction(about_act)

        quit_act = QAction("Quit SDrop", menu)
        quit_act.triggered.connect(self._quit)
        menu.addAction(quit_act)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        self.app.aboutToQuit.connect(self._cleanup_on_exit)
        self.shelf.summon_near(get_cursor_pos())

    def _register_global_hotkey(self, preset_name: str):
        if sys.platform != "win32":
            return
        try:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_TOGGLE_ID)
        except Exception:
            pass
        combo = HOTKEY_PRESETS.get(preset_name)
        if combo:
            mods, vk = combo
            ctypes.windll.user32.RegisterHotKey(None, HOTKEY_TOGGLE_ID, mods | MOD_NOREPEAT, vk)

    def _on_settings_changed(self, cfg: dict):
        self.cfg = cfg
        self.shake_detector.set_sensitivity(cfg.get("shake_sensitivity", "Medium"))
        self._register_global_hotkey(cfg.get("hotkey", "Win + Alt + D"))
        accent = NEON_THEMES.get(cfg.get("theme", "Electric Cyan"), NEON_THEMES["Electric Cyan"])[0]
        self.tray.setIcon(QIcon(create_app_pixmap(64, accent)))

    def _toggle_shelf(self):
        if self.shelf.isVisible():
            self.shelf.hide()
        else:
            self.shelf.summon_near(get_cursor_pos())

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_shelf()

    def _cleanup_on_exit(self):
        if sys.platform == "win32":
            try:
                ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_TOGGLE_ID)
            except Exception:
                pass
        self.shelf._save_session()
        cleanup_temp_dir()

    def _quit(self):
        self._cleanup_on_exit()
        self.app.quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_PUBLISHER)
    controller = SDropController(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()