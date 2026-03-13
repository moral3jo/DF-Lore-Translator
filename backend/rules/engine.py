"""
Rule Engine — resuelve patrones conocidos localmente sin llamar a caché ni a la API.

Flujo de uso:
    result = engine.match(text)
    if result:
        # result = {"translated": str, "engine": str, "rule": str}
        return result
    # si None → continuar con caché → API

Las reglas se cargan una sola vez al importar el módulo.
Para recargarlas sin reiniciar el servidor llama a reload_rules().
"""

import json
import os
import re
from datetime import datetime, timezone

import yaml

from . import handlers as _handlers

_RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.yaml")
_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
_LOG_PATH = os.path.join(_LOG_DIR, "rules_debug.jsonl")


# ---------------------------------------------------------------------------
# Carga de reglas
# ---------------------------------------------------------------------------

def _load() -> list[dict]:
    with open(_RULES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


_rules: list[dict] = _load()


def reload_rules() -> None:
    """Recarga rules.yaml en caliente sin reiniciar el servidor."""
    global _rules
    _rules = _load()
    print(f"[RuleEngine] {len(_rules)} regla(s) cargada(s).", flush=True)


# ---------------------------------------------------------------------------
# Logging de debug
# ---------------------------------------------------------------------------

def _log(original: str, translated: str, rule: str) -> None:
    os.makedirs(_LOG_DIR, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "rule": rule,
        "original": original,
        "translated": translated,
    }
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[RuleEngine] regla={rule!r}  {original!r} → {translated!r}", flush=True)


# ---------------------------------------------------------------------------
# Match principal
# ---------------------------------------------------------------------------

def match(text: str) -> dict | None:
    """
    Recorre las reglas en orden. Devuelve el primer match como:
        {"translated": str, "engine": "rule:<handler>", "rule": str}
    o None si ninguna regla aplica.
    """
    for rule in _rules:
        pattern = rule.get("pattern", "")
        handler_name = rule.get("handler", "")

        m = re.match(pattern, text)
        if m is None:
            continue

        handler_fn = getattr(_handlers, handler_name, None)
        if handler_fn is None:
            print(f"[RuleEngine] Warning: handler '{handler_name}' no existe en handlers.py", flush=True)
            continue

        result = handler_fn(text, m)
        _log(text, result, handler_name)
        return {"translated": result, "engine": f"rule:{handler_name}", "rule": handler_name}

    return None
