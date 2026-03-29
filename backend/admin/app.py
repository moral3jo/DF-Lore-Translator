"""
Panel de gestión del DF-Traductor.
Puerto por defecto: 5200  (configurable con env ADMIN_PORT)

Arrancar:   python admin/app.py          (desde backend/)
            o con start-admin.bat en la raíz del proyecto
"""

import os
import re
import sqlite3
import yaml
import csv
import io
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request, Response

# ─── Rutas ────────────────────────────────────────────────────────────────────

ADMIN_DIR     = Path(__file__).parent
BACKEND_DIR   = ADMIN_DIR.parent
DB_PATH       = BACKEND_DIR / "cache" / "translations.db"
RULES_PATH    = BACKEND_DIR / "rules" / "rules.yaml"
GLOSSARY_PATH = BACKEND_DIR / "glossary.txt"

_RULES_HEADER = """\
# Reglas declarativas del Rule Engine.
# Cada regla tiene:
#   pattern     — regex Python que se aplica con re.match() al texto original
#   handler     — nombre de la función en handlers.py que procesa el match
#   description — (opcional) descripción legible
#
# Para añadir una regla nueva:
#   1. Añade la entrada aquí con su pattern y handler
#   2. Si el handler no existe todavía, créalo en handlers.py
#   3. Reinicia el servidor
#
# El orden importa: se evalúan de arriba a abajo y se usa la primera coincidencia.

"""

_GLOSSARY_HEADER = """\
# Glosario DeepL para Dwarf Fortress
# Formato: término en inglés = traducción en español
# Las líneas que empiezan con # son comentarios y se ignoran.
# Cada vez que modifiques este archivo, reinicia el servidor para que
# el cambio se sincronice automáticamente con DeepL.

"""

app = Flask(__name__)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def load_rules() -> list:
    with open(RULES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def save_rules(rules: list) -> None:
    body = yaml.dump(rules, allow_unicode=True, default_flow_style=False, sort_keys=True)
    with open(RULES_PATH, "w", encoding="utf-8") as f:
        f.write(_RULES_HEADER + body)


def load_glossary() -> list:
    entries = []
    with open(GLOSSARY_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                en, es = line.split("=", 1)
                entries.append({"en": en.strip(), "es": es.strip()})
    return entries


def save_glossary(entries: list) -> None:
    with open(GLOSSARY_PATH, "w", encoding="utf-8") as f:
        f.write(_GLOSSARY_HEADER)
        for e in entries:
            f.write(f"{e['en']} = {e['es']}\n")


def _build_where(args: dict):
    """Construye la cláusula WHERE y la lista de parámetros a partir de filtros comunes."""
    where, params = [], []
    search = (args.get("search") or "").strip()
    engine = (args.get("engine") or "").strip()
    min_uses = (args.get("min_uses") or "").strip()
    max_days = (args.get("max_days") or "").strip()
    only_edited = (args.get("edited") or "").strip()

    if search:
        where.append("(original LIKE ? OR translated LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    if engine:
        where.append("engine LIKE ?")
        params.append(f"%{engine}%")
    if min_uses:
        where.append("use_count <= ?")
        params.append(int(min_uses))
    if max_days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=int(max_days))).isoformat()
        where.append("last_used < ?")
        params.append(cutoff)
    if only_edited == "1":
        where.append("is_edited = 1")

    ws = f"WHERE {' AND '.join(where)}" if where else ""
    return ws, params

# ─── Páginas ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ─── Stats ───────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    with db() as conn:
        total_unique   = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
        total_requests = conn.execute("SELECT COALESCE(SUM(use_count), 0) FROM translations").fetchone()[0]
        # Cada entrada se creó 1 vez vía API; el resto de usos son hits de caché
        cache_hits_all = total_requests - total_unique
        hit_rate = round(cache_hits_all / total_requests * 100, 1) if total_requests > 0 else 0.0

        edited  = conn.execute("SELECT COUNT(*) FROM translations WHERE is_edited=1").fetchone()[0]
        by_engine = conn.execute(
            "SELECT engine, COUNT(*) n FROM translations GROUP BY engine ORDER BY n DESC"
        ).fetchall()
        top10 = conn.execute(
            "SELECT original, translated, use_count "
            "FROM translations ORDER BY use_count DESC LIMIT 10"
        ).fetchall()

        # Totales históricos desde daily_stats (disponible desde el primer reinicio con tracking)
        rule_hits_all = conn.execute(
            "SELECT COALESCE(SUM(count),0) FROM daily_stats WHERE source='rule'"
        ).fetchone()[0]

        # Desglose diario real (últimos 30 días)
        daily_api = conn.execute(
            "SELECT date day, count n FROM daily_stats "
            "WHERE source='api' AND date >= date('now','-30 days') ORDER BY date"
        ).fetchall()
        daily_rules = conn.execute(
            "SELECT date day, count n FROM daily_stats "
            "WHERE source='rule' AND date >= date('now','-30 days') ORDER BY date"
        ).fetchall()
        daily_cache = conn.execute(
            "SELECT date day, count n FROM daily_stats "
            "WHERE source='cache' AND date >= date('now','-30 days') ORDER BY date"
        ).fetchall()

        stale_30 = conn.execute(
            "SELECT COUNT(*) FROM translations WHERE last_used < date('now','-30 days') AND is_edited=0"
        ).fetchone()[0]

        # Caracteres enviados a DeepL (= LENGTH(original) de cada entrada creada vía API)
        chars_total = conn.execute(
            "SELECT COALESCE(SUM(LENGTH(original)), 0) FROM translations"
        ).fetchone()[0]
        chars_month = conn.execute(
            "SELECT COALESCE(SUM(LENGTH(original)), 0) FROM translations "
            "WHERE substr(created_at,1,7) = strftime('%Y-%m','now')"
        ).fetchone()[0]
        chars_today = conn.execute(
            "SELECT COALESCE(SUM(LENGTH(original)), 0) FROM translations "
            "WHERE substr(created_at,1,10) = date('now')"
        ).fetchone()[0]
        # Caracteres por día (últimos 30) para la gráfica
        chars_daily = conn.execute(
            "SELECT substr(created_at,1,10) day, SUM(LENGTH(original)) n "
            "FROM translations WHERE created_at >= date('now','-30 days') "
            "GROUP BY day ORDER BY day"
        ).fetchall()

    return jsonify({
        "total_unique":    total_unique,
        "total_requests":  total_requests,
        "cache_hits_all":  cache_hits_all,
        "rule_hits_all":   rule_hits_all,
        "hit_rate":        hit_rate,
        "edited":          edited,
        "stale_30d":       stale_30,
        "chars_total":     chars_total,
        "chars_month":     chars_month,
        "chars_today":     chars_today,
        "chars_daily":     [{"day": r["day"], "n": r["n"]} for r in chars_daily],
        "by_engine": [{"engine": r["engine"], "count": r["n"]} for r in by_engine],
        "top10": [
            {"original": r["original"][:80], "translated": r["translated"][:80], "use_count": r["use_count"]}
            for r in top10
        ],
        "daily_api":   [{"day": r["day"], "n": r["n"]} for r in daily_api],
        "daily_rules": [{"day": r["day"], "n": r["n"]} for r in daily_rules],
        "daily_cache": [{"day": r["day"], "n": r["n"]} for r in daily_cache],
    })

# ─── Traducciones ─────────────────────────────────────────────────────────────

@app.route("/api/translations")
def api_translations():
    page     = max(1, int(request.args.get("page", 1)))
    per_page = min(200, max(10, int(request.args.get("per_page", 50))))
    sort     = request.args.get("sort", "last_used")
    order    = request.args.get("order", "desc")

    valid_sorts = {"use_count", "last_used", "created_at", "original"}
    sc = sort if sort in valid_sorts else "last_used"
    od = "DESC" if order.lower() != "asc" else "ASC"

    ws, params = _build_where(request.args)

    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM translations {ws}", params).fetchone()[0]
        rows  = conn.execute(
            f"SELECT rowid, original, translated, engine, use_count, "
            f"       substr(created_at,1,10) created_at, substr(last_used,1,10) last_used, is_edited "
            f"FROM translations {ws} ORDER BY {sc} {od} LIMIT ? OFFSET ?",
            params + [per_page, (page - 1) * per_page]
        ).fetchall()

    return jsonify({
        "total": total, "page": page, "per_page": per_page,
        "rows": [dict(r) for r in rows],
    })


@app.route("/api/translations/preview-delete", methods=["POST"])
def api_preview_delete():
    """Devuelve cuántas entradas se eliminarían con los filtros dados."""
    data = request.get_json(force=True) or {}
    data["edited"] = ""  # la limpieza masiva nunca toca is_edited=1
    where, params = _build_where(data)
    if where:
        where = where + " AND is_edited = 0"
    else:
        where = "WHERE is_edited = 0"
    with db() as conn:
        n = conn.execute(f"SELECT COUNT(*) FROM translations {where}", params).fetchone()[0]
    return jsonify({"count": n})


@app.route("/api/translations/bulk-delete", methods=["POST"])
def api_bulk_delete():
    """Elimina entradas que cumplan los filtros. Nunca borra is_edited=1."""
    data = request.get_json(force=True) or {}
    data["edited"] = ""
    where, params = _build_where(data)
    if where:
        where = where + " AND is_edited = 0"
    else:
        where = "WHERE is_edited = 0"
    with db() as conn:
        n = conn.execute(f"SELECT COUNT(*) FROM translations {where}", params).fetchone()[0]
        conn.execute(f"DELETE FROM translations {where}", params)
    return jsonify({"deleted": n})


@app.route("/api/translations/export")
def api_export():
    """Exporta todas las traducciones como CSV."""
    ws, params = _build_where(request.args)
    with db() as conn:
        rows = conn.execute(
            f"SELECT original, translated, engine, use_count, created_at, last_used, is_edited "
            f"FROM translations {ws} ORDER BY last_used DESC",
            params
        ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["original", "translated", "engine", "use_count", "created_at", "last_used", "is_edited"])
    for r in rows:
        writer.writerow(list(r))
    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=translations.csv"}
    )


@app.route("/api/translations/<int:rowid>", methods=["PUT"])
def api_update_translation(rowid):
    data = request.get_json(force=True) or {}
    translated = (data.get("translated") or "").strip()
    if not translated:
        return jsonify({"error": "translated no puede estar vacío"}), 400
    with db() as conn:
        result = conn.execute(
            "UPDATE translations SET translated=?, is_edited=1 WHERE rowid=?",
            (translated, rowid)
        )
        if result.rowcount == 0:
            return jsonify({"error": "No encontrado"}), 404
    return jsonify({"ok": True})


@app.route("/api/translations/<int:rowid>", methods=["DELETE"])
def api_delete_translation(rowid):
    force = request.args.get("force") == "1"
    with db() as conn:
        row = conn.execute(
            "SELECT is_edited FROM translations WHERE rowid=?", (rowid,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "No encontrado"}), 404
        if row["is_edited"] == 1 and not force:
            return jsonify({"error": "edited",
                            "msg": "Esta entrada fue editada manualmente. ¿Eliminar igualmente?"}), 409
        conn.execute("DELETE FROM translations WHERE rowid=?", (rowid,))
    return jsonify({"ok": True})

# ─── Reglas ───────────────────────────────────────────────────────────────────

@app.route("/api/rules", methods=["GET"])
def api_get_rules():
    return jsonify(load_rules())


@app.route("/api/rules", methods=["POST"])
def api_add_rule():
    data = request.get_json(force=True) or {}
    pattern     = (data.get("pattern") or "").strip()
    handler     = (data.get("handler") or "ignore_line").strip()
    description = (data.get("description") or "").strip()

    if not pattern:
        return jsonify({"error": "pattern es obligatorio"}), 400
    if not handler:
        return jsonify({"error": "handler es obligatorio"}), 400
    try:
        re.compile(pattern)
    except re.error as e:
        return jsonify({"error": f"Regex inválida: {e}"}), 400

    rules = load_rules()
    entry: dict = {"pattern": pattern, "handler": handler}
    if description:
        entry["description"] = description
    rules.append(entry)
    save_rules(rules)
    return jsonify({"ok": True, "index": len(rules) - 1})


@app.route("/api/rules/<int:idx>", methods=["DELETE"])
def api_delete_rule(idx):
    rules = load_rules()
    if idx < 0 or idx >= len(rules):
        return jsonify({"error": "Índice fuera de rango"}), 404
    deleted = rules.pop(idx)
    save_rules(rules)
    return jsonify({"ok": True, "deleted": deleted})


@app.route("/api/rules/test", methods=["POST"])
def api_test_rule():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text es obligatorio"}), 400
    rules = load_rules()
    for i, rule in enumerate(rules):
        try:
            m = re.match(rule["pattern"], text)
            if m:
                return jsonify({
                    "matched": True,
                    "index": i,
                    "rule": rule,
                    "groups": list(m.groups()),
                })
        except re.error:
            pass
    return jsonify({"matched": False})

# ─── Glosario ─────────────────────────────────────────────────────────────────

@app.route("/api/glossary", methods=["GET"])
def api_get_glossary():
    return jsonify(load_glossary())


@app.route("/api/glossary", methods=["POST"])
def api_add_glossary():
    data = request.get_json(force=True) or {}
    en = (data.get("en") or "").strip()
    es = (data.get("es") or "").strip()
    if not en or not es:
        return jsonify({"error": "Los campos 'en' y 'es' son obligatorios"}), 400
    entries = load_glossary()
    if any(e["en"] == en for e in entries):
        return jsonify({"error": f"'{en}' ya existe en el glosario"}), 409
    entries.append({"en": en, "es": es})
    save_glossary(entries)
    return jsonify({"ok": True})


@app.route("/api/glossary/<path:term>", methods=["PUT"])
def api_update_glossary(term):
    data = request.get_json(force=True) or {}
    es_new = (data.get("es") or "").strip()
    if not es_new:
        return jsonify({"error": "es no puede estar vacío"}), 400
    entries = load_glossary()
    for e in entries:
        if e["en"] == term:
            e["es"] = es_new
            save_glossary(entries)
            return jsonify({"ok": True})
    return jsonify({"error": "No encontrado"}), 404


@app.route("/api/glossary/<path:term>", methods=["DELETE"])
def api_delete_glossary(term):
    entries = load_glossary()
    new_entries = [e for e in entries if e["en"] != term]
    if len(new_entries) == len(entries):
        return jsonify({"error": "No encontrado"}), 404
    save_glossary(new_entries)
    return jsonify({"ok": True})

# ─── Arranque ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("ADMIN_PORT", 5200))
    print(f"[Admin Panel] Abriendo en http://localhost:{port}")
    print(f"[Admin Panel] BD:      {DB_PATH}")
    print(f"[Admin Panel] Reglas:  {RULES_PATH}")
    print(f"[Admin Panel] Glosario:{GLOSSARY_PATH}")
    app.run(host="0.0.0.0", port=port, debug=False)
