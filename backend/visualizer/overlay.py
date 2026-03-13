"""
Visualizador overlay con PyQt6.

Ventana flotante completamente transparente que muestra las traducciones
encima del juego con texto contorneado para máxima legibilidad.
Configurable desde config.yaml (sección display.overlay).

Arquitectura de ventanas:
  _ControlBar    — barra pequeña e interactiva con botón de arrastre y colapso.
  _OverlayWindow — área de texto, 100 % transparente y click-through.

display() es thread-safe: puede llamarse desde cualquier hilo.
"""

import ctypes
import re
import sys
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QFont, QPainter, QTextDocument, QCursor
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget, QScrollArea, QSizePolicy,
)

from .base import BaseVisualizer

# Altura de la barra de control en píxeles
_BAR_H = 22

# ---------------------------------------------------------------------------
# Click-through en Windows via WS_EX_TRANSPARENT
# ---------------------------------------------------------------------------

def _make_click_through(hwnd: int) -> None:
    """Aplica WS_EX_LAYERED | WS_EX_TRANSPARENT al HWND (solo Windows)."""
    if sys.platform != "win32":
        return
    GWL_EXSTYLE       = -20
    WS_EX_LAYERED     = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT
    )


# ---------------------------------------------------------------------------
# Paleta CGA → HTML
# ---------------------------------------------------------------------------

_CGA_COLORS = [
    "#000000", "#0000AA", "#00AA00", "#00AAAA",
    "#AA0000", "#AA00AA", "#AA5500", "#AAAAAA",
    "#555555", "#5555FF", "#55FF55", "#55FFFF",
    "#FF5555", "#FF55FF", "#FFFF55", "#FFFFFF",
]

_RE_TAG   = re.compile(r"\[C:(\d):(\d):(\d)\]|\[B\]")
_RE_COLOR = re.compile(r"color:#[0-9A-Fa-f]{6}")


def _escape_html(text: str) -> str:
    return (
        text
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;").replace("'", "&#39;")
    )


def _markup_to_html(text: str, default_color: str = "#FFFFFF") -> str:
    """Convierte markup DFHack [C:fg:bg:bright] a spans HTML coloreados."""
    result: list[str] = []
    open_span = False
    last = 0

    for m in _RE_TAG.finditer(text):
        plain = text[last:m.start()]
        if plain:
            result.append(_escape_html(plain))
        last = m.end()

        if m.group(0) == "[B]":
            if open_span:
                result.append("</span>")
                open_span = False
            result.append("<br>")
        else:
            fg, bg, bright = int(m.group(1)), int(m.group(2)), int(m.group(3))
            fg_color = _CGA_COLORS[(fg + (8 if bright else 0)) % 16]
            if open_span:
                result.append("</span>")
            result.append(f'<span style="color:{fg_color};">')
            open_span = True

    remaining = text[last:]
    if remaining:
        result.append(_escape_html(remaining))
    if open_span:
        result.append("</span>")

    return "".join(result)


# ---------------------------------------------------------------------------
# Widget de texto con contorno
# ---------------------------------------------------------------------------

class _OutlinedLabel(QWidget):
    """
    Renderiza texto HTML con contorno sólido usando QTextDocument + QPainter.
    Dibuja el documento 8 veces desplazado con el color del contorno y luego
    una vez encima con los colores reales.
    """

    def __init__(
        self,
        html: str,
        default_color: str,
        outline_color: str,
        outline_width: int,
        font: QFont,
    ) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setFont(font)

        self._outline_width = outline_width
        self._pad = outline_width + 2

        self._doc = QTextDocument()
        self._doc.setDefaultFont(font)
        self._doc.setHtml(f'<span style="color:{default_color};">{html}</span>')

        outline_html = _RE_COLOR.sub(f"color:{outline_color}", html)
        self._outline_doc = QTextDocument()
        self._outline_doc.setDefaultFont(font)
        self._outline_doc.setHtml(
            f'<span style="color:{outline_color};">{outline_html}</span>'
        )

    def _sync_width(self) -> None:
        inner = max(self.width() - self._pad * 2, 1)
        self._doc.setTextWidth(inner)
        self._outline_doc.setTextWidth(inner)

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        self._sync_width()
        self.setMinimumHeight(int(self._doc.size().height()) + self._pad * 2)
        super().resizeEvent(event)

    def sizeHint(self) -> QSize:
        return QSize(400, int(self._doc.size().height()) + self._pad * 2)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        self._sync_width()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        pad  = self._pad
        ow   = self._outline_width
        clip = QRectF(0, 0, self._doc.textWidth(), self._doc.size().height())

        for dx, dy in (
            (-ow, -ow), (0, -ow), (ow, -ow),
            (-ow,   0),           (ow,   0),
            (-ow,  ow), (0,  ow), (ow,  ow),
        ):
            painter.save()
            painter.translate(pad + dx, pad + dy)
            self._outline_doc.drawContents(painter, clip)
            painter.restore()

        painter.translate(pad, pad)
        self._doc.drawContents(painter, clip)
        painter.end()


# ---------------------------------------------------------------------------
# Barra de control (interactiva — NO click-through)
# ---------------------------------------------------------------------------

_BTN_STYLE = """
    QPushButton {{
        background: rgba(0,0,0,130);
        color: rgba(255,255,255,210);
        border: none;
        border-radius: 4px;
        font-size: 11px;
        padding: 0px 5px;
    }}
    QPushButton:hover   {{ background: rgba(80,80,80,180); }}
    QPushButton:pressed {{ background: rgba(120,120,120,200); }}
"""

_DRAG_STYLE = """
    QLabel {
        color: rgba(255,255,255,150);
        background: rgba(0,0,0,100);
        border-radius: 4px;
        font-size: 12px;
        padding: 0px 6px;
    }
"""


class _ControlBar(QWidget):
    """
    Pequeña barra flotante con dos botones:
      ⠿  arrastrar  — mueve toda la overlay (barra + ventana de texto juntas).
      ▼/▲ colapsar  — muestra u oculta la ventana de texto.

    Esta ventana NO es click-through para poder recibir eventos de ratón.
    """

    def __init__(self, text_window: "_OverlayWindow", config: dict) -> None:
        super().__init__()
        self._text   = text_window
        self._cfg    = config
        self._collapsed  = False
        self._drag_pos: Optional[QPoint] = None

        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._cfg.get("always_on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        x = int(self._cfg.get("x", 10))
        y = int(self._cfg.get("y", 10))
        w = int(self._cfg.get("width", 700))
        # Se coloca encima de la ventana de texto
        self.setGeometry(x, max(0, y - _BAR_H), w, _BAR_H)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(6)

        # Botón de arrastre — arrastrar aquí mueve toda la overlay
        self._drag_btn = QLabel("⠿")
        self._drag_btn.setStyleSheet(_DRAG_STYLE)
        self._drag_btn.setFixedHeight(_BAR_H - 6)
        self._drag_btn.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        self._drag_btn.setToolTip("Arrastra para mover")
        layout.addWidget(self._drag_btn)

        layout.addStretch()

        # Botón de colapsar/expandir
        self._btn_collapse = QPushButton("▼")
        self._btn_collapse.setFixedSize(22, _BAR_H - 6)
        self._btn_collapse.setStyleSheet(_BTN_STYLE)
        self._btn_collapse.setToolTip("Colapsar / expandir")
        self._btn_collapse.clicked.connect(self._toggle_collapse)
        layout.addWidget(self._btn_collapse)

    # -- Colapsar --

    def _toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._text.hide()
            self._btn_collapse.setText("▲")
            self._btn_collapse.setToolTip("Expandir")
        else:
            self._text.show()
            self._btn_collapse.setText("▼")
            self._btn_collapse.setToolTip("Colapsar")

    # -- Arrastrar (mueve barra + ventana de texto juntas) --

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            delta_x = new_pos.x() - self.x()
            delta_y = new_pos.y() - self.y()
            self.move(new_pos)
            self._text.move(self._text.x() + delta_x, self._text.y() + delta_y)

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        self._drag_pos = None


# ---------------------------------------------------------------------------
# Ventana de texto (click-through)
# ---------------------------------------------------------------------------

class _OverlayWindow(QWidget):
    """
    Ventana PyQt6 sin bordes, siempre encima, completamente transparente
    y click-through. Muestra los mensajes con _OutlinedLabel.
    """

    _sig_add = pyqtSignal(str)

    def __init__(self, config: dict) -> None:
        super().__init__()
        self._cfg = config
        self._message_widgets: list[tuple[_OutlinedLabel, Optional[QTimer]]] = []

        self._setup_window()
        self._setup_ui()
        self._sig_add.connect(self._on_add_message)

    def _setup_window(self) -> None:
        cfg = self._cfg
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if cfg.get("always_on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowOpacity(float(cfg.get("opacity", 1.0)))
        self.setGeometry(
            int(cfg.get("x", 10)),
            int(cfg.get("y", 10)),
            int(cfg.get("width", 700)),
            int(cfg.get("height", 300)),
        )
        self.setWindowTitle("DF Lore Translator Overlay")

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")
        self._scroll = scroll
        outer.addWidget(scroll)

        self._msg_container = QWidget()
        self._msg_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._msg_container.setStyleSheet("background: transparent;")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(6, 6, 6, 6)
        self._msg_layout.setSpacing(4)
        self._msg_layout.addStretch()
        scroll.setWidget(self._msg_container)

    # -- Mensajes --

    def _on_add_message(self, text: str) -> None:
        cfg = self._cfg
        max_msgs      = int(cfg.get("max_messages", 10))
        fade_secs     = float(cfg.get("fade_seconds", 0))
        font_family   = cfg.get("font_family", "Consolas")
        font_size     = int(cfg.get("font_size", 13))
        default_color = cfg.get("default_text_color", "#FFFFFF")
        outline_color = cfg.get("outline_color", "#000000")
        outline_width = int(cfg.get("outline_width", 2))

        html  = _markup_to_html(text, default_color)
        font  = QFont(font_family, font_size)
        label = _OutlinedLabel(html, default_color, outline_color, outline_width, font)

        self._msg_layout.insertWidget(self._msg_layout.count() - 1, label)

        QTimer.singleShot(
            50,
            lambda: self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()
            ),
        )

        timer: Optional[QTimer] = None
        if fade_secs > 0:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda lbl=label: self._remove_label(lbl))
            timer.start(int(fade_secs * 1000))

        self._message_widgets.append((label, timer))

        while len(self._message_widgets) > max_msgs:
            old_label, old_timer = self._message_widgets.pop(0)
            if old_timer:
                old_timer.stop()
            old_label.deleteLater()

    def _remove_label(self, label: _OutlinedLabel) -> None:
        self._message_widgets = [
            (lbl, tmr) for lbl, tmr in self._message_widgets if lbl is not label
        ]
        label.deleteLater()

    def add_message(self, text: str) -> None:
        """Thread-safe."""
        self._sig_add.emit(text)

    def showEvent(self, event) -> None:  # noqa: ANN001
        super().showEvent(event)
        _make_click_through(int(self.winId()))


# ---------------------------------------------------------------------------
# Visualizador público
# ---------------------------------------------------------------------------

class OverlayVisualizer(BaseVisualizer):
    """
    Visualizador con ventana flotante PyQt6.

    Dos ventanas:
      - Barra de control  (interactiva): botón de arrastre + colapsar/expandir.
      - Área de texto     (click-through): traducciones con texto contorneado
                          sobre fondo completamente transparente.

    Requiere que exista una QApplication antes de instanciar.
    display() es thread-safe.
    """

    def __init__(self, config: dict) -> None:
        self._text_window = _OverlayWindow(config)
        self._control_bar = _ControlBar(self._text_window, config)
        self._text_window.show()
        self._control_bar.show()

    def display(self, text: str) -> None:
        self._text_window.add_message(text)

    def close(self) -> None:
        self._control_bar.close()
        self._text_window.close()
