"""
Watcher de gamelog.txt
Detecta líneas nuevas en tiempo real y las traduce via el Translation Service.
El modo de visualización se configura en config.yaml (display.mode).
"""

import json
import os
import re
import sys
import time
import requests
import yaml
from datetime import datetime, timezone
from dotenv import load_dotenv

# Carga variables de entorno desde .env (raíz del proyecto)
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(_ENV_PATH)

# Salida UTF-8 en Windows para que los caracteres ANSI y tildes se muestren bien
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Permite ejecutar el watcher directamente desde su carpeta
_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _ROOT)

# ---------------------------------------------------------------------------
# Carga de configuración
# ---------------------------------------------------------------------------

_CONFIG_PATH = os.path.join(_ROOT, "config.yaml")


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Markup DFHack — utilidades compartidas (logging)
# ---------------------------------------------------------------------------

_RE_TAG = re.compile(r"\[C:(\d):(\d):(\d)\]|\[B\]")


def _count_markup(text: str) -> int:
    """Cuenta el número de tokens de markup DFHack en el texto."""
    return len(_RE_TAG.findall(text))


def _strip_dfhack(text: str) -> str:
    """Elimina los códigos DFHack para logging legible."""
    return _RE_TAG.sub("", text).strip()


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

_LOG_DIR = os.path.join(_ROOT, "logs")
_MISMATCH_PATH = os.path.join(_LOG_DIR, "markup_mismatch.jsonl")
_SEPARATOR = "-" * 60


def _log_mismatch(original: str, translated: str, orig_count: int, trans_count: int) -> None:
    os.makedirs(_LOG_DIR, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "orig_markup": orig_count,
        "trans_markup": trans_count,
        "original": original,
        "translated": translated,
    }
    with open(_MISMATCH_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _log_translation(original: str, translated: str) -> None:
    """Añade la pareja EN/ES al log diario de auditoría."""
    os.makedirs(_LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(_LOG_DIR, f"translations_{today}.log")
    ts = datetime.now().strftime("%H:%M:%S")
    en_clean = _strip_dfhack(original)
    es_clean = _strip_dfhack(translated)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] EN: {en_clean}\n")
        f.write(f"[{ts}] ES: {es_clean}\n")
        f.write(_SEPARATOR + "\n")


# ---------------------------------------------------------------------------
# Traducción
# ---------------------------------------------------------------------------

def _translate(text: str, service_url: str) -> str | None:
    """Envía text al Translation Service. Devuelve la traducción o None si falla."""
    try:
        response = requests.post(
            f"{service_url}/translate",
            json={"text": text, "target": "es"},
            timeout=90,
        )
        response.raise_for_status()
        return response.json().get("translated", "")
    except requests.exceptions.ConnectionError:
        print(f"  [!] Translation Service no disponible en {service_url}. Reintentando...", flush=True)
    except requests.exceptions.Timeout:
        print("  [!] Timeout al contactar el Translation Service.", flush=True)
    except Exception as exc:
        print(f"  [!] Error inesperado: {exc}", flush=True)
    return None


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------

def watch(gamelog_path: str, poll_interval: float, service_url: str, visualizer) -> None:
    print(f"[Watcher] Vigilando: {gamelog_path}", flush=True)
    print(f"[Watcher] Servicio de traducción: {service_url}", flush=True)
    print("[Watcher] Esperando líneas nuevas... (Ctrl+C para detener)\n", flush=True)

    while not os.path.exists(gamelog_path):
        print(f"[Watcher] gamelog.txt no encontrado en {gamelog_path!r}. Esperando...", flush=True)
        time.sleep(poll_interval * 4)

    with open(gamelog_path, "r", encoding="cp437", errors="replace") as f:
        f.seek(0, 2)  # EOF — ignora el historial previo

        while True:
            line = f.readline()
            if line:
                line = line.rstrip("\n").strip()
                if not line:
                    continue

                orig_count = _count_markup(line)
                translated = _translate(line, service_url)

                if translated:
                    trans_count = _count_markup(translated)
                    if orig_count != trans_count:
                        print(
                            f"  [markup] {orig_count}→{trans_count} tokens  (ver logs/markup_mismatch.jsonl)",
                            flush=True,
                        )
                        _log_mismatch(line, translated, orig_count, trans_count)

                    _log_translation(line, translated)
                    visualizer.display(translated)
                else:
                    visualizer.display("(sin traducción disponible)")
            else:
                time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = _load_config()
    watcher_cfg = cfg.get("watcher", {})
    display_cfg = cfg.get("display", {})
    display_mode = display_cfg.get("mode", "console")

    # gamelog_path: config.yaml > construido desde DF_INSTALL_PATH env
    gamelog_path = watcher_cfg.get("gamelog_path", "")
    if not gamelog_path:
        df_path = os.environ.get("DF_INSTALL_PATH", cfg.get("df_install_path", ""))
        if df_path:
            gamelog_path = os.path.join(df_path, "gamelog.txt")
        else:
            gamelog_path = "C:/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress/gamelog.txt"

    poll_interval = float(watcher_cfg.get("poll_interval_seconds", 0.5))
    service_url = watcher_cfg.get("translation_service_url", "http://localhost:5100").rstrip("/")

    if display_mode == "overlay":
        import threading
        from PyQt6.QtWidgets import QApplication
        from visualizer.overlay import OverlayVisualizer

        app = QApplication(sys.argv)
        overlay_cfg = display_cfg.get("overlay", {})
        visualizer = OverlayVisualizer(overlay_cfg)

        thread = threading.Thread(
            target=watch,
            args=(gamelog_path, poll_interval, service_url, visualizer),
            daemon=True,
        )
        thread.start()

        try:
            sys.exit(app.exec())
        except KeyboardInterrupt:
            print("\n[Watcher] Detenido por el usuario.", flush=True)

    else:  # console (por defecto)
        from visualizer.console import ConsoleVisualizer

        beep = os.environ.get("BEEP_ENABLED", "true").lower() != "false"
        visualizer = ConsoleVisualizer(beep_enabled=beep)

        try:
            watch(gamelog_path, poll_interval, service_url, visualizer)
        except KeyboardInterrupt:
            print("\n[Watcher] Detenido por el usuario.", flush=True)
