import sys
import threading
import winsound
from typing import Optional

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QPropertyAnimation, QTimer, pyqtSignal, QRect, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QIcon, QPixmap

from engine import AssistantEngine

class FloatingOrb(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self.state = "idle"
        self._glow_radius = 10
        self._orb_color = QColor("#ffffff")
        
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(self._orb_color)
        self.shadow.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pulse)
        self.pulse_dir = 1
        self.pulse_val = 0

    def set_state(self, state: str) -> None:
        self.state = state
        if state == "listening":
            self._orb_color = QColor("#34d399") # Emerald
            self.timer.start(50)
        elif state == "processing":
            self._orb_color = QColor("#3b82f6") # Blue
            self.timer.start(30)
        elif state == "error":
            self._orb_color = QColor("#fb7185") # Rose
            self.timer.stop()
            self._glow_radius = 20
        else:
            self._orb_color = QColor("#ffffff")
            self.timer.stop()
            self._glow_radius = 10
        
        self.shadow.setColor(self._orb_color)
        self.update()

    def update_pulse(self) -> None:
        self.pulse_val += self.pulse_dir * 1
        if self.pulse_val > 15:
            self.pulse_dir = -1
        elif self.pulse_val < 0:
            self.pulse_dir = 1
            
        self._glow_radius = 10 + self.pulse_val
        self.shadow.setBlurRadius(self._glow_radius * 2)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = 15 + (self.pulse_val / 3 if self.state in ["listening", "processing"] else 0)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._orb_color))
        painter.drawEllipse(int(center_x - radius), int(center_y - radius), int(radius * 2), int(radius * 2))


class GoofyUI(QWidget):
    state_changed = pyqtSignal(str, str) # state, message

    def __init__(self) -> None:
        super().__init__()
        self.initUI()
        self.state_changed.connect(self.update_ui)

    def initUI(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.orb = FloatingOrb()
        self.layout.addWidget(self.orb, alignment=Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("Listening...")
        self.label.setStyleSheet("""
            color: white;
            font-family: 'Inter', sans-serif;
            font-size: 16px;
            font-weight: 500;
            background-color: rgba(10, 10, 10, 0.85);
            padding: 8px 16px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        """)
        self.layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(self.layout)
        self.resize(300, 150)
        
        # Position at bottom
        self.screen_rect = QApplication.primaryScreen().geometry()
        self.hidden_y = self.screen_rect.height()
        self.visible_y = int(self.screen_rect.height() - self.height() - 50)
        self.x_pos = int((self.screen_rect.width() - self.width()) / 2)
        
        self.move(self.x_pos, self.hidden_y)
        
        # Setup System Tray
        self.setup_tray()
        
        # We start hidden
        self.is_visible = False

    def setup_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple icon programmatically if none exists
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor("#3b82f6")))
        painter.drawEllipse(2, 2, 28, 28)
        painter.end()
        
        self.tray_icon.setIcon(QIcon(pixmap))
        
        tray_menu = QMenu()
        quit_action = tray_menu.addAction("Quit Goofy")
        quit_action.triggered.connect(QApplication.instance().quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
    def play_sound(self, state: str) -> None:
        try:
            if state == "listening":
                # High pitched short beep
                winsound.Beep(800, 150)
            elif state == "success":
                # Happy chime
                winsound.Beep(600, 100)
                winsound.Beep(800, 150)
            elif state == "error":
                # Sad beep
                winsound.Beep(300, 300)
        except Exception as e:
            print(f"[UI] Sound error: {e}")

    def animate_window(self, show: bool = True) -> None:
        if show == self.is_visible:
            return
            
        self.is_visible = show
        if show:
            self.show()
            start_y = self.hidden_y
            end_y = self.visible_y
        else:
            start_y = self.visible_y
            end_y = self.hidden_y
            
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(400)
        self.anim.setStartValue(QRect(self.x_pos, start_y, self.width(), self.height()))
        self.anim.setEndValue(QRect(self.x_pos, end_y, self.width(), self.height()))
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack if show else QEasingCurve.Type.InBack)
        
        if not show:
            self.anim.finished.connect(self.hide)
            
        self.anim.start()

    def update_ui(self, state: str, message: str) -> None:
        self.label.setText(message)
        self.orb.set_state(state)
        
        # Always show the UI if it's doing something!
        if state != "idle":
            self.animate_window(True)

        if state == "listening":
            self.play_sound("listening")
        elif state == "success":
            self.play_sound("success")
        elif state == "error":
            self.play_sound("error")
            
        if state == "idle":
            QTimer.singleShot(2000, lambda: self.animate_window(False))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running in tray
    
    ex = GoofyUI()
    
    # Initialize and start the engine
    try:
        engine = AssistantEngine()
        engine.state_changed.connect(ex.update_ui)
        
        # Show visual confirmation that Goofy is alive!
        ex.update_ui("success", "Goofy is Online!")
        QTimer.singleShot(3000, lambda: ex.update_ui("idle", ""))
        
        engine.start()
    except Exception as e:
        print(f"Failed to start audio engine: {e}")
        ex.update_ui("error", f"Engine Error: {str(e)[:20]}...")
    
    sys.exit(app.exec())
