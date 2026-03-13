#!/usr/bin/env python3
"""
build.py — Genera el ZIP de distribución de DF-Lore-Translator.

Incluye Python embebido + dependencias. El usuario final no necesita
tener Python instalado.

Uso:
    python build.py [--version X.X.X]

Resultado:
    dist/DF-Lore-Translator-vX.X.X.zip
"""

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

PYTHON_VERSION = "3.12.9"
PYTHON_EMBED_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}"
    f"/python-{PYTHON_VERSION}-embed-amd64.zip"
)
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

ROOT = Path(__file__).parent
DIST = ROOT / "dist"

# Ficheros sueltos que se copian a la raíz del ZIP
INCLUDE_FILES = [
    ".env.example",
    "README.md",
    "df-lore-translator.bat",
    "df-lore-translator.ps1",
    "start-server.bat",
    "start-watcher.bat",
    "deploy.py",
    "manage.py",
]

# Carpetas que se copian respetando su estructura
INCLUDE_DIRS = [
    "backend",
    "mod/scripts",
]

# Nombres de carpetas y ficheros a excluir dentro de las carpetas copiadas
EXCLUDE_DIRS  = {"__pycache__", "cache", "logs", ".git"}
EXCLUDE_FILES = {"glossary_state.json"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def download(url: str, dest: Path) -> None:
    filename = url.split("/")[-1]
    log(f"Descargando {filename}...")
    urllib.request.urlretrieve(url, dest)


def copy_dir(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in EXCLUDE_DIRS or item.name in EXCLUDE_FILES:
            continue
        if item.is_dir():
            copy_dir(item, dst / item.name)
        else:
            shutil.copy2(item, dst / item.name)


# ---------------------------------------------------------------------------
# Pasos del build
# ---------------------------------------------------------------------------

def setup_python(python_dir: Path) -> None:
    """Descarga Python embebido y activa site-packages + pip."""
    embed_zip = DIST / "_python-embed.zip"
    download(PYTHON_EMBED_URL, embed_zip)

    log("Extrayendo Python embebido...")
    with zipfile.ZipFile(embed_zip, "r") as z:
        z.extractall(python_dir)
    embed_zip.unlink()

    # Activar site-packages descomentando "import site" en el .pth
    pth_files = list(python_dir.glob("python*._pth"))
    if pth_files:
        pth = pth_files[0]
        pth.write_text(pth.read_text().replace("#import site", "import site"))
        log(f"site-packages activado ({pth.name})")

    # Instalar pip
    log("Instalando pip en Python embebido...")
    get_pip = DIST / "_get-pip.py"
    download(GET_PIP_URL, get_pip)
    subprocess.run(
        [str(python_dir / "python.exe"), str(get_pip), "--no-warn-script-location"],
        check=True,
    )
    get_pip.unlink()


def install_deps(python_dir: Path) -> None:
    req = ROOT / "backend" / "requirements.txt"
    log("Instalando dependencias (puede tardar unos minutos)...")
    subprocess.run(
        [
            str(python_dir / "python.exe"), "-m", "pip", "install",
            "-r", str(req), "--no-warn-script-location",
        ],
        check=True,
    )


def copy_project(target: Path) -> None:
    log("Copiando archivos del proyecto...")
    for f in INCLUDE_FILES:
        src = ROOT / f
        if src.exists():
            shutil.copy2(src, target / f)
    for d in INCLUDE_DIRS:
        src = ROOT / d
        if src.exists():
            copy_dir(src, target / d)


def make_zip(source_dir: Path, zip_name: str) -> Path:
    zip_path = DIST / zip_name
    log(f"Comprimiendo → {zip_name}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in source_dir.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(DIST))
    return zip_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="dev", help="Versión del release (ej: 1.0.0)")
    args = parser.parse_args()

    version   = args.version.lstrip("v")
    dist_name = f"DF-Lore-Translator-v{version}"
    target    = DIST / dist_name

    print(f"\n  DF-Lore-Translator - build v{version}")
    print(f"  {'=' * 40}\n")

    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    # 1. Python embebido
    python_dir = target / "python"
    python_dir.mkdir()
    setup_python(python_dir)

    # 2. Dependencias
    install_deps(python_dir)

    # 3. Código fuente y recursos
    copy_project(target)

    # 4. ZIP final
    zip_path = make_zip(target, f"{dist_name}.zip")
    mb = zip_path.stat().st_size / 1_048_576
    print(f"\n  OK  {zip_path.name}  ({mb:.1f} MB)")
    print(f"     {zip_path}\n")


if __name__ == "__main__":
    main()
