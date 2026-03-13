"""
Gestión del glosario DeepL.

El archivo glossary.txt (en backend/) define las entradas en formato:
    source = target
    # líneas que empiezan con # son comentarios

Al arrancar el servidor se compara el contenido local con el glosario
activo en DeepL. Si hay diferencias se borra el antiguo y se crea uno nuevo.
Todo ocurre de forma automática; no es necesaria intervención manual.
"""

import json
import os

import deepl

_GLOSSARY_NAME = "df-lore-translator-en-es"
_STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "glossary_state.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_local(glossary_path: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    if not os.path.exists(glossary_path):
        return entries
    with open(glossary_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            src, _, tgt = line.partition("=")
            src, tgt = src.strip(), tgt.strip()
            if src and tgt:
                entries[src] = tgt
    return entries


def _load_state() -> dict:
    if os.path.exists(_STATE_PATH):
        with open(_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(glossary_id: str, entry_count: int) -> None:
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"glossary_id": glossary_id, "entry_count": entry_count}, f)


# ---------------------------------------------------------------------------
# Sincronización principal
# ---------------------------------------------------------------------------

def sync(client: deepl.Translator, glossary_path: str) -> str | None:
    """
    Sincroniza el glosario local con DeepL y devuelve el glossary_id activo.
    Devuelve None si glossary.txt está vacío o no existe.
    """
    local = _load_local(glossary_path)
    if not local:
        print("[Glosario] glossary.txt vacío o no encontrado — se usará DeepL sin glosario.", flush=True)
        return None

    state = _load_state()
    current_id: str | None = state.get("glossary_id")

    # Compara con el glosario remoto actual
    remote: dict[str, str] = {}
    if current_id:
        try:
            remote = client.get_glossary_entries(current_id)
        except deepl.DeepLException:
            print(f"[Glosario] Glosario anterior ({current_id}) no encontrado en DeepL.", flush=True)
            current_id = None

    if local == remote:
        print(f"[Glosario] Glosario sincronizado ({len(local)} entradas, ID: {current_id})", flush=True)
        return current_id

    # Hay diferencias: borrar el antiguo y crear uno nuevo
    print(f"[Glosario] Cambios detectados en glossary.txt ({len(local)} entradas locales vs {len(remote)} remotas).", flush=True)

    if current_id:
        try:
            client.delete_glossary(current_id)
            print(f"[Glosario] Glosario anterior eliminado (ID: {current_id}).", flush=True)
        except deepl.DeepLException as exc:
            print(f"[Glosario] Warning: no se pudo eliminar el glosario anterior: {exc}", flush=True)

    new = client.create_glossary(
        _GLOSSARY_NAME,
        source_lang="en",
        target_lang="es",
        entries=local,
    )
    _save_state(new.glossary_id, len(local))
    print(f"[Glosario] Nuevo glosario creado con {len(local)} entradas (ID: {new.glossary_id})", flush=True)
    return new.glossary_id
