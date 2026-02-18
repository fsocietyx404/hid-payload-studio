import sys
import os
from pathlib import Path

import cv2
from PyQt6.QtCore import Qt, QTimer, QRegularExpression
from PyQt6.QtGui import QImage, QPixmap, QFont, QTextCharFormat, QColor, QSyntaxHighlighter
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QFileDialog,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QMessageBox,
    QSizePolicy,
)

# ─── HID KEYMAP (US Layout) ────────────────────────────────────────────────
KEYMAP = {
    "a": 0x04, "b": 0x05, "c": 0x06, "d": 0x07, "e": 0x08, "f": 0x09, "g": 0x0A, "h": 0x0B,
    "i": 0x0C, "j": 0x0D, "k": 0x0E, "l": 0x0F, "m": 0x10, "n": 0x11, "o": 0x12, "p": 0x13,
    "q": 0x14, "r": 0x15, "s": 0x16, "t": 0x17, "u": 0x18, "v": 0x19, "w": 0x1A, "x": 0x1B,
    "y": 0x1C, "z": 0x1D,
    "1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22, "6": 0x23, "7": 0x24, "8": 0x25,
    "9": 0x26, "0": 0x27,
    "enter": 0x28, "esc": 0x29, "backspace": 0x2A, "tab": 0x2B, "space": 0x2C,
    "-": 0x2D, "equals": 0x2E, "[": 0x2F, "]": 0x30, "\\": 0x31,
    ";": 0x33, "'": 0x34, "`": 0x35, ",": 0x36, ".": 0x37, "/": 0x38,
    "f1": 0x3A, "f2": 0x3B, "f3": 0x3C, "f4": 0x3D, "f5": 0x3E, "f6": 0x3F,
    "f7": 0x40, "f8": 0x41, "f9": 0x42, "f10": 0x43, "f11": 0x44, "f12": 0x45,
    "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52,
}
MODIFIERS = {"ctrl": 0x01, "shift": 0x02, "alt": 0x04, "gui": 0x08, "win": 0x08, "windows": 0x08}


def parse_key(key_str: str) -> tuple[int, list[int]]:
    parts = [p.strip() for p in key_str.lower().split("-")]
    mod = 0
    keys: list[int] = []
    for p in parts:
        if p in MODIFIERS:
            mod |= MODIFIERS[p]
        elif p in KEYMAP:
            keys.append(KEYMAP[p])
    return mod, keys


def compile_duckyscript(text: str) -> bytes:
    binary = bytearray()
    line_nr = 0
    for line in text.splitlines():
        line_nr += 1
        line = line.strip()
        if not line or line.startswith(("REM", "//", "#")):
            continue
        parts = line.split(maxsplit=1)
        cmd = parts[0].upper()
        arg = parts[1].strip() if len(parts) > 1 else ""
        try:
            if cmd == "DELAY":
                ms = int(arg)
                reports = max(1, (ms + 10) // 12)
                binary += b"\x00" * 8 * reports
            elif cmd == "STRING":
                for char in arg:
                    mod = 0
                    key = 0
                    c = char.lower()
                    if c in KEYMAP:
                        key = KEYMAP[c]
                    if char.isupper() or char in r"""!@#$%^&*()_+{}|:"<>?~""":
                        mod |= MODIFIERS["shift"]
                    if char == " ":
                        key = KEYMAP["space"]
                    if char == "\n":
                        key = KEYMAP["enter"]
                        mod = 0
                    if key:
                        packet = bytearray(8)
                        packet[0] = mod
                        packet[2] = key
                        binary += packet
                        binary += b"\x00" * 16
            elif cmd in ["ENTER", "TAB", "ESC", "BACKSPACE"]:
                key = KEYMAP.get(cmd.lower(), 0)
                if key:
                    packet = bytearray(8)
                    packet[2] = key
                    binary += packet + b"\x00" * 16
            else:
                mod, keys = parse_key(cmd)
                if arg:
                    mod2, keys2 = parse_key(arg)
                    mod |= mod2
                    keys.extend(keys2)
                if keys:
                    packet = bytearray(8)
                    packet[0] = mod
                    for i, k in enumerate(keys[:6]):
                        packet[2 + i] = k
                    binary += packet + b"\x00" * 16
        except Exception as e:
            print(f"Fehler Zeile {line_nr}: {line} → {e}")
    return binary


# ─── Syntax Highlighting für DuckyScript ───────────────────────────────────
class DuckyHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        # Keyword-Farbe wie im Tk-Editor (#f472b6)
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor("#f472b6"))
        kw_format.setFontWeight(QFont.Weight.Bold)

        keywords = [
            "DELAY", "STRING", "ENTER", "TAB", "ESC", "BACKSPACE",
            "GUI", "WINDOWS", "ALT", "CTRL", "SHIFT", "REM",
        ]
        for kw in keywords:
            pattern = QRegularExpression(rf"\b{kw}\b")
            self._rules.append((pattern, kw_format))

        # Kommentar-Farbe (#64748b)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#64748b"))

        # REM am Zeilenanfang oder nach Leerzeichen
        self._rules.append(
            (QRegularExpression(r"(^|\s)REM[^\n]*"), comment_format)
        )
        # // Kommentar
        self._rules.append(
            (QRegularExpression(r"//[^\n]*"), comment_format)
        )
        # # Kommentar
        self._rules.append(
            (QRegularExpression(r"#[^\n]*"), comment_format)
        )

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                start = m.capturedStart()
                length = m.capturedLength()
                self.setFormat(start, length, fmt)


class VideoBackgroundLabel(QLabel):
    """Zeigt Frames eines Videos skaliert auf die Widget-Größe."""

    def __init__(self, video_path: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setScaledContents(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._cap = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)

        if not os.path.exists(video_path):
            QMessageBox.critical(self, "Video-Fehler", f"background.mp4 nicht gefunden:\n{video_path}")
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            QMessageBox.critical(self, "Video-Fehler", f"Video konnte nicht geöffnet werden:\n{video_path}")
            return

        self._cap = cap
        self._timer.start(33)  # ~30 FPS

    def _next_frame(self):
        if self._cap is None:
            return
        ok, frame = self._cap.read()
        if not ok:
            # Loop
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
            if not ok:
                return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        self.setPixmap(pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                  Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        if self.pixmap() is not None:
            self.setPixmap(
                self.pixmap().scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        super().resizeEvent(event)

    def close(self):
        self._timer.stop()
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        super().close()


class DuckyEncoderWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DuckyScript → payload.dd  |  PyQt BadUSB Encoder")
        self.resize(1180, 820)

        self.last_dir = str(Path.home() / "Desktop")

        # Video-Hintergrund
        # Im PyInstaller-Exe-Fall liegt background.mp4 neben der EXE,
        # im normalen Python-Run neben diesem Skript.
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).resolve().parent
        else:
            base_dir = Path(__file__).resolve().parent
        video_path = base_dir / "background.mp4"
        self.video_label = VideoBackgroundLabel(str(video_path), self)

        # Transparente Overlay-Fläche
        self.overlay = QWidget(self)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.overlay.setStyleSheet("background: transparent;")

        # Gesamtlayout (Overlay)
        root_layout = QVBoxLayout(self.overlay)
        root_layout.setContentsMargins(20, 20, 20, 16)
        root_layout.setSpacing(12)

        center_row = QHBoxLayout()
        center_row.setSpacing(12)
        root_layout.addLayout(center_row, stretch=1)

        # Editor-Panel (halbtransparent)
        editor_frame = QFrame()
        editor_frame.setStyleSheet(
            """
            QFrame {
                background-color: rgba(15, 23, 42, 190);
                border: 1px solid rgba(15, 23, 42, 220);
                border-radius: 12px;
            }
            QPlainTextEdit {
                background-color: transparent;
                color: #e2e8f0;
                selection-background-color: #1d4ed8;
                selection-color: white;
            }
            """
        )
        editor_layout = QVBoxLayout(editor_frame)
        editor_layout.setContentsMargins(16, 16, 16, 16)
        editor_layout.setSpacing(0)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        editor_layout.addWidget(self.editor)

        # Syntax-Highlighter aktivieren
        self.highlighter = DuckyHighlighter(self.editor.document())

        # Sidebar (leicht transparent)
        sidebar_frame = QFrame()
        sidebar_frame.setFixedWidth(260)
        sidebar_frame.setStyleSheet(
            """
            QFrame {
                background-color: rgba(15, 23, 42, 200);
                border-radius: 12px;
            }
            QLabel {
                color: #e5e7eb;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #e5e7eb;
                text-align: left;
                padding: 10px 16px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(30, 64, 175, 160);
            }
            """
        )
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        sidebar_layout.setSpacing(10)

        title = QLabel("BadUSB Encoder")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        sidebar_layout.addWidget(title)
        sidebar_layout.addSpacing(10)

        btn_load = QPushButton("📂  Payload laden")
        btn_save = QPushButton("💾  Als payload.dd speichern")
        btn_example = QPushButton("🔄  Beispiel laden")
        btn_clear = QPushButton("🗑️  Alles löschen")

        btn_load.clicked.connect(self.load_file)
        btn_save.clicked.connect(self.compile_and_save)
        btn_example.clicked.connect(self.load_example)
        btn_clear.clicked.connect(self.clear_editor)

        for btn in (btn_load, btn_save, btn_example, btn_clear):
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch(1)

        center_row.addWidget(editor_frame, stretch=4)
        center_row.addWidget(sidebar_frame, stretch=2)

        # Statusleiste unten
        status_frame = QFrame()
        status_frame.setStyleSheet(
            """
            QFrame {
                background-color: rgba(15, 23, 42, 210);
                border-radius: 8px;
            }
            QLabel {
                color: #cbd5f5;
            }
            """
        )
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(16, 6, 16, 6)

        self.status_label = QLabel("Bereit – viel Spaß beim Basteln deines BadUSB 🚀")
        status_layout.addWidget(self.status_label)

        root_layout.addWidget(status_frame, stretch=0)

        # Beispiel laden
        self.load_example()

    def resizeEvent(self, event):
        self.video_label.setGeometry(self.rect())
        self.overlay.setGeometry(self.rect())
        super().resizeEvent(event)

    # ─── Editor-Aktionen ────────────────────────────────────────────────────
    def clear_editor(self):
        self.editor.clear()
        self.status_label.setText("Editor geleert")

    def load_example(self):
        example = """DELAY 2000
GUI r
DELAY 400
STRING powershell -NoP -Exec Bypass -C "Start-Process cmd"
ENTER
DELAY 1500
STRING whoami
ENTER
DELAY 800
STRING notepad
ENTER
DELAY 600
STRING Hallo vom Pico W BadUSB!
ENTER"""
        self.editor.setPlainText(example)
        self.status_label.setText("Beispiel-Payload geladen")

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Payload laden",
            self.last_dir,
            "Text / DuckyScript (*.txt *.ds *.dd);;Alle Dateien (*.*)",
        )
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
            self.editor.setPlainText(content)
            self.last_dir = str(Path(path).parent)
            self.status_label.setText(f"Geladen: {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Konnte Datei nicht lesen:\n{e}")

    def compile_and_save(self):
        source = self.editor.toPlainText().rstrip()
        if not source.strip():
            QMessageBox.warning(self, "Leer", "Nichts zum Kompilieren da.")
            return

        self.status_label.setText("Kompiliere ...")
        QApplication.processEvents()

        try:
            bin_data = compile_duckyscript(source)
            size = len(bin_data)

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Payload speichern",
                str(Path(self.last_dir) / "payload.dd"),
                "pico-ducky Payload (*.dd *.bin);;Alle Dateien (*.*)",
            )
            if not path:
                self.status_label.setText("Abgebrochen")
                return

            Path(path).write_bytes(bin_data)
            self.last_dir = str(Path(path).parent)
            self.status_label.setText(f"Gespeichert: {size:,} Bytes → {Path(path).name}")
            QMessageBox.information(
                self,
                "Fertig",
                f"Payload gespeichert!\nGröße: {size:,} Bytes\n\n"
                f"Tipp: Auf Pico W als payload.dd kopieren.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            self.status_label.setText("Fehler beim Speichern")

    def closeEvent(self, event):
        self.video_label.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = DuckyEncoderWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()