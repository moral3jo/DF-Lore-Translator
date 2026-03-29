"""
Caché SQLite para traducciones.

Esquema de la tabla:
  original    TEXT UNIQUE  — texto original tal como llega a la API
  translated  TEXT         — traducción almacenada
  engine      TEXT         — motor que generó la traducción
  use_count   INTEGER      — veces que se ha servido desde caché
  created_at  TEXT         — ISO-8601 UTC
  last_used   TEXT         — ISO-8601 UTC
  is_edited   INTEGER      — 1 = editado manualmente, nunca sobreescribir ni limpiar
"""

import sqlite3
import threading
from datetime import datetime, timezone


_CREATE_TRANSLATIONS_SQL = """
CREATE TABLE IF NOT EXISTS translations (
    original   TEXT    NOT NULL UNIQUE,
    translated TEXT    NOT NULL,
    engine     TEXT    NOT NULL,
    use_count  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL,
    last_used  TEXT    NOT NULL,
    is_edited  INTEGER NOT NULL DEFAULT 0
)
"""

_CREATE_STATS_SQL = """
CREATE TABLE IF NOT EXISTS daily_stats (
    date   TEXT NOT NULL,
    source TEXT NOT NULL,
    count  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, source)
)
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TranslationCache:
    def __init__(self, db_path: str):
        import os
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(_CREATE_TRANSLATIONS_SQL)
            conn.execute(_CREATE_STATS_SQL)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def get(self, original: str) -> dict | None:
        """
        Busca una traducción en caché.
        Si existe, incrementa use_count y last_used y la devuelve.
        Devuelve None si no hay caché para ese texto.
        """
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT translated, engine FROM translations WHERE original = ?",
                (original,),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE translations SET use_count = use_count + 1, last_used = ? WHERE original = ?",
                (_now(), original),
            )
            translated, engine = row
            return {"translated": translated, "engine": f"{engine}+cache"}

    def set(self, original: str, translated: str, engine: str) -> None:
        """
        Guarda una nueva traducción. Si ya existe una entrada con is_edited=1
        no la sobreescribe.
        """
        now = _now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO translations (original, translated, engine, use_count, created_at, last_used, is_edited)
                VALUES (?, ?, ?, 1, ?, ?, 0)
                ON CONFLICT(original) DO UPDATE SET
                    translated = CASE WHEN is_edited = 0 THEN excluded.translated ELSE translated END,
                    engine     = CASE WHEN is_edited = 0 THEN excluded.engine     ELSE engine     END,
                    use_count  = use_count + 1,
                    last_used  = excluded.last_used
                """,
                (original, translated, engine, now, now),
            )

    def track(self, source: str) -> None:
        """
        Incrementa el contador diario para 'api', 'cache' o 'rule'.
        Llamar justo antes de devolver la respuesta en app.py.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO daily_stats (date, source, count) VALUES (?, ?, 1)
                ON CONFLICT(date, source) DO UPDATE SET count = count + 1
                """,
                (today, source),
            )
