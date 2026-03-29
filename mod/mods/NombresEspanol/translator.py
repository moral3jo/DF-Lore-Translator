"""
NombresEspanol - Herramienta de traduccion para language_words.txt de Dwarf Fortress
Arranca con: python translator.py
"""
import os
import re
import json
import sqlite3
import unicodedata
import webbrowser
from pathlib import Path
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "translations.db"
DEFAULT_SOURCE = r"D:\SteamLibrary\steamapps\common\Dwarf Fortress\data\vanilla\vanilla_languages\objects\language_words.txt"
OUTPUT_PATH = BASE_DIR / "objects" / "language_words.txt"

FORM_TYPES = ["NOUN", "VERB", "ADJ", "PREFIX"]


def strip_accents(text):
    """Convierte caracteres acentuados a su equivalente ASCII: á→a, é→e, ñ→n..."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
FORM_LABELS = {
    "NOUN": ["singular", "plural"],
    "VERB": ["presente", "3a_persona", "pasado", "participio", "gerundio"],
    "ADJ": ["adjetivo"],
    "PREFIX": ["prefijo"],
}


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    def _has_non_ascii(s):
        if not s:
            return 0
        try:
            vals = json.loads(s)
            for v in vals:
                try:
                    str(v).encode("ascii")
                except UnicodeEncodeError:
                    return 1
        except Exception:
            pass
        return 0

    def _has_space(s):
        if not s:
            return 0
        try:
            vals = json.loads(s)
            return 1 if any(" " in str(v) for v in vals) else 0
        except Exception:
            return 0

    conn.create_function("has_non_ascii", 1, _has_non_ascii)
    conn.create_function("has_space", 1, _has_space)
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS word_forms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            word_key    TEXT NOT NULL,
            form_type   TEXT NOT NULL,
            original    TEXT NOT NULL,
            translated  TEXT,
            UNIQUE(word_key, form_type)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_language_file(filepath):
    """Devuelve lista de (word_key, form_type, [parts])"""
    entries = []
    current_word = None
    with open(filepath, "r", encoding="cp437", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            m = re.match(r"\[WORD:([A-Z0-9_]+)\]", stripped)
            if m:
                current_word = m.group(1)
                continue
            if current_word:
                for ft in FORM_TYPES:
                    m2 = re.match(rf"\[{ft}:([^\]]+)\]", stripped)
                    if m2:
                        parts = m2.group(1).split(":")
                        entries.append((current_word, ft, parts))
                        break
    return entries


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    conn = get_db()
    if request.method == "POST":
        data = request.json or {}
        for k, v in data.items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (k, v)
            )
        conn.commit()
        conn.close()
        return jsonify({"ok": True})
    else:
        rows = conn.execute("SELECT key,value FROM settings").fetchall()
        conn.close()
        result = {r["key"]: r["value"] for r in rows}
        result.setdefault("source_path", DEFAULT_SOURCE)
        return jsonify(result)


@app.route("/api/import", methods=["POST"])
def api_import():
    data = request.json or {}
    filepath = data.get("filepath", DEFAULT_SOURCE)
    try:
        entries = parse_language_file(filepath)
        conn = get_db()
        new_count = 0
        for word_key, form_type, parts in entries:
            cur = conn.execute(
                "INSERT OR IGNORE INTO word_forms (word_key,form_type,original,translated) VALUES (?,?,?,NULL)",
                (word_key, form_type, json.dumps(parts)),
            )
            new_count += cur.rowcount
        conn.commit()
        total = conn.execute("SELECT COUNT(DISTINCT word_key) FROM word_forms").fetchone()[0]
        conn.close()
        return jsonify({"ok": True, "imported": new_count, "total_words": total})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/stats")
def api_stats():
    conn = get_db()
    total_words = conn.execute(
        "SELECT COUNT(DISTINCT word_key) FROM word_forms"
    ).fetchone()[0]
    total_forms = conn.execute("SELECT COUNT(*) FROM word_forms").fetchone()[0]
    translated_forms = conn.execute(
        "SELECT COUNT(*) FROM word_forms WHERE translated IS NOT NULL"
    ).fetchone()[0]
    translated_words = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT word_key FROM word_forms
            GROUP BY word_key
            HAVING COUNT(*) = SUM(CASE WHEN translated IS NOT NULL THEN 1 ELSE 0 END)
        )
    """).fetchone()[0]
    conn.close()
    return jsonify(
        {
            "total_words": total_words,
            "total_forms": total_forms,
            "translated_forms": translated_forms,
            "untranslated_forms": total_forms - translated_forms,
            "translated_words": translated_words,
            "untranslated_words": total_words - translated_words,
        }
    )


@app.route("/api/words")
def api_words():
    filter_mode = request.args.get("filter", "all")  # all | translated | untranslated
    search = request.args.get("search", "").strip().upper()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    conn = get_db()

    # Build subquery: word_keys that match filter
    if filter_mode == "translated":
        word_filter_sql = """
            SELECT word_key FROM word_forms
            GROUP BY word_key
            HAVING COUNT(*) = SUM(CASE WHEN translated IS NOT NULL THEN 1 ELSE 0 END)
        """
    elif filter_mode == "untranslated":
        word_filter_sql = """
            SELECT word_key FROM word_forms
            GROUP BY word_key
            HAVING SUM(CASE WHEN translated IS NULL THEN 1 ELSE 0 END) > 0
        """
    elif filter_mode == "has_accents":
        word_filter_sql = """
            SELECT DISTINCT word_key FROM word_forms
            WHERE translated IS NOT NULL AND has_non_ascii(translated) = 1
        """
    elif filter_mode == "has_spaces":
        word_filter_sql = """
            SELECT DISTINCT word_key FROM word_forms
            WHERE translated IS NOT NULL AND has_space(translated) = 1
        """
    else:
        word_filter_sql = "SELECT DISTINCT word_key FROM word_forms"

    params = []
    search_cond = ""
    if search:
        search_cond = " WHERE wk.word_key LIKE ?"
        params.append(f"%{search}%")

    count_sql = f"""
        SELECT COUNT(DISTINCT wk.word_key)
        FROM ({word_filter_sql}) wk
        {search_cond}
    """
    total_keys = conn.execute(count_sql, params).fetchone()[0]

    offset = (page - 1) * per_page
    keys_sql = f"""
        SELECT wk.word_key
        FROM ({word_filter_sql}) wk
        {search_cond}
        ORDER BY wk.word_key
        LIMIT ? OFFSET ?
    """
    params_paginated = params + [per_page, offset]
    key_rows = conn.execute(keys_sql, params_paginated).fetchall()
    word_keys = [r[0] for r in key_rows]

    result = []
    if word_keys:
        placeholders = ",".join("?" * len(word_keys))
        form_rows = conn.execute(
            f"SELECT * FROM word_forms WHERE word_key IN ({placeholders}) ORDER BY word_key, form_type",
            word_keys,
        ).fetchall()

        words_map = {}
        for row in form_rows:
            wk = row["word_key"]
            if wk not in words_map:
                words_map[wk] = {"word_key": wk, "forms": []}
            words_map[wk]["forms"].append(
                {
                    "id": row["id"],
                    "form_type": row["form_type"],
                    "original": json.loads(row["original"]),
                    "translated": json.loads(row["translated"]) if row["translated"] else None,
                }
            )
        for wk in word_keys:
            if wk in words_map:
                result.append(words_map[wk])

    conn.close()
    return jsonify(
        {
            "words": result,
            "total": total_keys,
            "page": page,
            "per_page": per_page,
            "pages": (total_keys + per_page - 1) // per_page if per_page else 1,
        }
    )


@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.json or {}
    form_id = data.get("id")
    translated = data.get("translated")  # list of strings | null to clear

    conn = get_db()
    if translated is not None:
        # Store even if empty strings — clear only when explicitly null
        conn.execute(
            "UPDATE word_forms SET translated=? WHERE id=?",
            (json.dumps(translated), form_id),
        )
    else:
        conn.execute("UPDATE word_forms SET translated=NULL WHERE id=?", (form_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.json or {}
    source_path = data.get("source_path", DEFAULT_SOURCE)
    do_strip_accents = data.get("strip_accents", False)

    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT word_key, form_type, original, translated FROM word_forms"
        ).fetchall()
        conn.close()

        translations = {}
        for row in rows:
            key = (row["word_key"], row["form_type"])
            translations[key] = (
                json.loads(row["translated"]) if row["translated"] else None
            )

        output_lines = []
        current_word = None

        with open(source_path, "r", encoding="cp437", errors="replace") as f:
            for line in f:
                line_content = line.rstrip("\n\r")
                stripped = line_content.strip()

                m = re.match(r"\[WORD:([A-Z0-9_]+)\]", stripped)
                if m:
                    current_word = m.group(1)
                    output_lines.append(line_content)
                    continue

                replaced = False
                if current_word:
                    for ft in FORM_TYPES:
                        if re.match(rf"\[{ft}:([^\]]+)\]", stripped):
                            trans = translations.get((current_word, ft))
                            if trans:
                                indent = line_content[: len(line_content) - len(line_content.lstrip())]
                                values = [strip_accents(v) if do_strip_accents else v for v in trans]
                                new_tag = f"[{ft}:{':'.join(values)}]"
                                output_lines.append(indent + new_tag)
                            else:
                                output_lines.append(line_content)
                            replaced = True
                            break

                if not replaced:
                    output_lines.append(line_content)

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "wb") as f:
            content = "\r\n".join(output_lines)
            f.write(content.encode("cp437", errors="replace"))

        return jsonify({"ok": True, "path": str(OUTPUT_PATH)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    url = "http://localhost:5050"
    print(f"Abriendo {url} ...")
    webbrowser.open(url)
    app.run(port=5050, debug=False)
