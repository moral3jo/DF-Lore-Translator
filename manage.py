#!/usr/bin/env python3
"""
manage.py — Herramienta de administración del proyecto DF-Lore-Translator.

Uso:
  python manage.py clean [--min-uses N] [--older-than-days N] [--dry-run]

Ejemplos:
  python manage.py clean --min-uses 2
  python manage.py clean --older-than-days 30
  python manage.py clean --min-uses 2 --older-than-days 30 --dry-run

Las entradas con is_edited=1 nunca se eliminan.
Si se combinan --min-uses y --older-than-days, se elimina lo que cumpla
AMBAS condiciones (lógica AND: poco usada Y antigua).
"""

import argparse
import os
import sqlite3
import sys
import yaml
from datetime import datetime, timedelta, timezone

_BACKEND = os.path.join(os.path.dirname(__file__), "backend")
_CONFIG_PATH = os.path.join(_BACKEND, "config.yaml")


def _load_db_path() -> str:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    rel = cfg.get("cache", {}).get("path", "cache/translations.db")
    return os.path.join(_BACKEND, rel)


# ---------------------------------------------------------------------------
# Comando: clean
# ---------------------------------------------------------------------------

def cmd_clean(args: argparse.Namespace) -> None:
    if args.min_uses is None and args.older_than_days is None:
        print("Debes especificar al menos --min-uses o --older-than-days.")
        sys.exit(1)

    db_path = _load_db_path()
    if not os.path.exists(db_path):
        print(f"Base de datos no encontrada: {db_path}")
        sys.exit(1)

    # Construye la cláusula WHERE dinámicamente
    conditions = ["is_edited = 0"]
    params: list = []

    if args.min_uses is not None:
        conditions.append("use_count < ?")
        params.append(args.min_uses)

    if args.older_than_days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=args.older_than_days)).isoformat()
        conditions.append("last_used < ?")
        params.append(cutoff)

    where = " AND ".join(conditions)
    select_sql = f"SELECT original, use_count, last_used FROM translations WHERE {where}"
    delete_sql = f"DELETE FROM translations WHERE {where}"

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(select_sql, params).fetchall()
        count = len(rows)

        if count == 0:
            print("No hay entradas que eliminar con los criterios indicados.")
            return

        if args.dry_run:
            print(f"[dry-run] Se eliminarían {count} entradas:")
            for original, use_count, last_used in rows:
                preview = original[:80] + ("…" if len(original) > 80 else "")
                print(f"  uses={use_count:>4}  last={last_used[:10]}  {preview!r}")
        else:
            conn.execute(delete_sql, params)
            conn.commit()
            print(f"Eliminadas {count} entradas de la caché.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="Herramienta de administración de DF-Lore-Translator",
    )
    sub = parser.add_subparsers(dest="command", metavar="comando")

    clean_p = sub.add_parser("clean", help="Limpia entradas de caché por umbral de uso o antigüedad")
    clean_p.add_argument(
        "--min-uses", type=int, metavar="N",
        help="Elimina entradas con use_count < N",
    )
    clean_p.add_argument(
        "--older-than-days", type=int, metavar="N",
        help="Elimina entradas cuyo last_used sea anterior a N días",
    )
    clean_p.add_argument(
        "--dry-run", action="store_true",
        help="Muestra lo que se eliminaría sin borrar nada",
    )

    args = parser.parse_args()
    if args.command == "clean":
        cmd_clean(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
