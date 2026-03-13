"""
Visualizador de consola.
Renderiza el markup DFHack como secuencias ANSI y lo imprime por stdout.
Extraído de backend/watcher/gamelog_watcher.py.
"""

import os
import re
import shutil

from .base import BaseVisualizer

# ---------------------------------------------------------------------------
# Markup DFHack → ANSI
# ---------------------------------------------------------------------------

# Paleta CGA estándar → códigos ANSI (foreground 30-37, background 40-47)
_CGA_FG = [30, 34, 32, 36, 31, 35, 33, 37]
_CGA_BG = [40, 44, 42, 46, 41, 45, 43, 47]
_ANSI_RESET = "\033[0m"
_RE_TAG = re.compile(r"\[C:(\d):(\d):(\d)\]|\[B\]")


def _render_markup(text: str) -> str:
    """
    Convierte los códigos DFHack en secuencias ANSI.
    Siempre emite ANSI_RESET al final para que no queden colores abiertos.
    """
    def _sub(m: re.Match) -> str:
        if m.group(0) == "[B]":
            return "\n"
        fg, bg, bright = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"\033[{_CGA_FG[fg % 8] + (60 if bright else 0)};{_CGA_BG[bg % 8]}m"

    return _RE_TAG.sub(_sub, text) + _ANSI_RESET


# ---------------------------------------------------------------------------
# Word wrap con ANSI
# ---------------------------------------------------------------------------

_RE_ANSI_STRIP = re.compile(r"\033\[[0-9;]*m")


def _visual_len(s: str) -> int:
    """Longitud visual de una cadena ignorando los códigos ANSI."""
    return len(_RE_ANSI_STRIP.sub("", s))


def _wrap(text: str, width: int) -> str:
    """
    Aplica word wrap a texto que puede contener códigos ANSI.
    Los códigos ANSI no cuentan como espacio visual.
    Los \\n existentes se respetan como saltos duros.
    """
    out_lines = []

    for hard_line in text.split("\n"):
        if not hard_line:
            out_lines.append("")
            continue

        words = []
        buf = ""
        i = 0
        while i < len(hard_line):
            ch = hard_line[i]
            if ch == "\033" and i + 1 < len(hard_line) and hard_line[i + 1] == "[":
                end = hard_line.index("m", i + 2) + 1
                buf += hard_line[i:end]
                i = end
            elif ch == " ":
                words.append(buf)
                buf = ""
                i += 1
            else:
                buf += ch
                i += 1
        words.append(buf)

        line = ""
        line_len = 0
        for word in words:
            wlen = _visual_len(word)
            if line_len == 0:
                line, line_len = word, wlen
            elif line_len + 1 + wlen <= width:
                line += " " + word
                line_len += 1 + wlen
            else:
                out_lines.append(line)
                line, line_len = word, wlen
        out_lines.append(line)

    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
# Visualizador
# ---------------------------------------------------------------------------

class ConsoleVisualizer(BaseVisualizer):
    """Imprime las traducciones en la consola con colores ANSI."""

    def __init__(self, beep_enabled: bool = True):
        self._beep = beep_enabled

    def display(self, text: str) -> None:
        cols = shutil.get_terminal_size().columns
        rendered = _render_markup(text)
        print(_wrap(rendered, cols) + "\n", flush=True)
        if self._beep:
            print("\a", end="", flush=True)
