import os
import sys
import yaml

# Añade backend/ al path para que los módulos sean importables
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Carga variables de entorno desde .env (raíz del proyecto)
from dotenv import load_dotenv
_project_root = os.path.join(os.path.dirname(__file__), "..", "..")
load_dotenv(os.path.join(_project_root, ".env"))

from flask import Flask, request, jsonify
from translator.factory import get_translator
from translation_cache import TranslationCache
from rules import engine as rule_engine

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Inicialización
# ---------------------------------------------------------------------------

_backend_dir = os.path.join(os.path.dirname(__file__), "..")
_config_path = os.path.join(_backend_dir, "config.yaml")

with open(_config_path, "r", encoding="utf-8") as f:
    _config = yaml.safe_load(f)

_translator = get_translator(_config)

# Caché SQLite
_cache_rel = _config.get("cache", {}).get("path", "cache/translations.db")
_cache_path = os.path.join(_backend_dir, _cache_rel)
_cache = TranslationCache(_cache_path)
print(f"[Cache] SQLite en: {os.path.abspath(_cache_path)}")

# Sincronización de glosario (solo DeepL)
if _config.get("engine") == "deepl":
    from translator.glossary_manager import sync
    from translator.deepl_translator import DeepLTranslator
    _glossary_path = os.path.join(_backend_dir, "glossary.txt")
    assert isinstance(_translator, DeepLTranslator)
    _translator.glossary_id = sync(_translator.client, _glossary_path)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/translate", methods=["POST"])
def translate():
    data = request.get_json(force=True, silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "El campo 'text' es obligatorio"}), 400

    text = data["text"].strip()
    if not text:
        return jsonify({"error": "El texto está vacío"}), 400

    target = data.get("target", "es")

    # 1. Rule Engine — resolución local sin caché ni API
    rule_result = rule_engine.match(text)
    if rule_result:
        return jsonify({"translated": rule_result["translated"], "engine": rule_result["engine"]})

    # 2. Caché SQLite
    cached = _cache.get(text)
    if cached:
        return jsonify({"translated": cached["translated"], "engine": cached["engine"]})

    # 3. API de traducción
    try:
        translated = _translator.translate(text, target_lang=target)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    _cache.set(text, translated, _translator.name)
    return jsonify({"translated": translated, "engine": _translator.name})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "engine": _translator.name})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5100))
    print(f"[Translation Service] Escuchando en http://localhost:{port}  (motor: {_translator.name})")
    app.run(host="0.0.0.0", port=port)
