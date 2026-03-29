"""
deploy.py — Despliega los scripts del mod a las carpetas de DFHack.

Uso: python deploy.py [--copy]

Sin argumentos: crea un enlace simbolico por cada .lua (cambios instantaneos).
Con --copy:     copia los archivos (util si los enlaces no estan disponibles).

Mappings (mod/ -> <DF>/):
  mod/dfhack-config/scripts/  ->  <DF>/dfhack-config/scripts/
  mod/hack/scripts/           ->  <DF>/hack/scripts/
"""

import os
import sys
import shutil
import yaml
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_ROOT, ".env"))

_CONFIG_PATH = os.path.join(_ROOT, "backend", "config.yaml")

# Pares (carpeta_origen, subcarpeta_destino_relativa_a_DF)
_MAPPINGS = [
    (os.path.join(_ROOT, "mod", "dfhack-config", "scripts"), os.path.join("dfhack-config", "scripts")),
    (os.path.join(_ROOT, "mod", "hack",          "scripts"), os.path.join("hack",          "scripts")),
]


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_df_path(cfg: dict) -> str:
    return os.environ.get("DF_INSTALL_PATH", "") or cfg.get("df_install_path", "")


def _lua_files(src_dir: str) -> list[str]:
    if not os.path.isdir(src_dir):
        return []
    return [
        name for name in os.listdir(src_dir)
        if name.endswith(".lua") and not name.startswith(".") and not name.startswith("_")
    ]


def _deploy_symlinks_for(src_dir: str, dst_dir: str) -> tuple[int, int]:
    """Crea enlaces simbolicos para cada .lua de src_dir en dst_dir.
    Devuelve (creados, omitidos)."""
    files = _lua_files(src_dir)
    if not files:
        return 0, 0

    os.makedirs(dst_dir, exist_ok=True)
    created = 0
    skipped = 0

    for name in files:
        src = os.path.join(src_dir, name)
        dst = os.path.join(dst_dir, name)

        if os.path.islink(dst):
            if os.readlink(dst) == src:
                skipped += 1
                continue
            os.remove(dst)  # apunta a otro sitio, actualizar

        if os.path.exists(dst):
            print(f"  AVISO: {name} ya existe como archivo real. Eliminalo manualmente.")
            continue

        os.symlink(src, dst)
        print(f"  {name}  ->  {src}")
        created += 1

    return created, skipped


def _deploy_symlinks_for_mods(src_dir: str, dst_dir: str) -> tuple[int, int]:
    """Crea enlaces simbolicos para cada carpeta de mods."""
    if not os.path.isdir(src_dir):
        return 0, 0

    os.makedirs(dst_dir, exist_ok=True)
    created = 0
    skipped = 0

    for name in os.listdir(src_dir):
        src = os.path.join(src_dir, name)
        if not os.path.isdir(src):
            continue

        dst = os.path.join(dst_dir, name)

        if os.path.islink(dst):
            try:
                if os.readlink(dst) == src:
                    skipped += 1
                    continue
                os.remove(dst)
            except OSError:
                try:
                    os.rmdir(dst)
                except OSError:
                    pass

        if os.path.exists(dst):
            print(f"  AVISO: {name} ya existe como carpeta real. Eliminala manualmente.")
            continue

        os.symlink(src, dst, target_is_directory=True)
        print(f"  {name}/  ->  {src}")
        created += 1

    return created, skipped


def _deploy_copy_for_mods(src_dir: str, dst_dir: str) -> int:
    """Copia cada carpeta de mods."""
    if not os.path.isdir(src_dir):
        return 0

    os.makedirs(dst_dir, exist_ok=True)
    copied = 0

    for name in os.listdir(src_dir):
        src = os.path.join(src_dir, name)
        if not os.path.isdir(src):
            continue

        dst = os.path.join(dst_dir, name)
        
        if os.path.exists(dst):
            if os.path.islink(dst) or os.path.isfile(dst):
                try:
                    os.remove(dst)
                except OSError:
                    os.rmdir(dst)
            else:
                shutil.rmtree(dst)
        
        shutil.copytree(src, dst)
        print(f"  {name}/  ->  {dst}")
        copied += 1

    return copied


def _deploy_copy_for(src_dir: str, dst_dir: str) -> int:
    """Copia cada .lua de src_dir a dst_dir. Devuelve numero de archivos copiados."""
    files = _lua_files(src_dir)
    if not files:
        return 0

    os.makedirs(dst_dir, exist_ok=True)
    copied = 0

    for name in files:
        src = os.path.join(src_dir, name)
        dst = os.path.join(dst_dir, name)
        shutil.copy2(src, dst)
        print(f"  {name}  ->  {dst}")
        copied += 1

    return copied


def deploy_symlink(df_path: str) -> None:
    total_created = 0
    total_skipped = 0

    for src_dir, dst_rel in _MAPPINGS:
        dst_dir = os.path.join(df_path, dst_rel)
        files = _lua_files(src_dir)
        if not files:
            continue

        print(f"\n[deploy] {dst_rel}/")
        try:
            created, skipped = _deploy_symlinks_for(src_dir, dst_dir)
            total_created += created
            total_skipped += skipped
        except OSError as e:
            print(f"  ERROR: {e}")
            print("  Prueba con --copy o ejecuta como Administrador.")
            sys.exit(1)

    # Despliegue de carpetas de mods a AppData
    mods_src = os.path.join(_ROOT, "mod", "mods")
    appdata = os.environ.get("APPDATA")
    if appdata and os.path.isdir(mods_src):
        mods_dst = os.path.join(appdata, "Bay 12 Games", "Dwarf Fortress", "mods")
        
        # Comprobar si hay carpetas que desplegar antes de imprimir
        folders = [f for f in os.listdir(mods_src) if os.path.isdir(os.path.join(mods_src, f))]
        if folders:
            print(f"\n[deploy] carpetas mods -> {mods_dst}")
            try:
                created, skipped = _deploy_symlinks_for_mods(mods_src, mods_dst)
                total_created += created
                total_skipped += skipped
            except OSError as e:
                print(f"  ERROR: {e}")
                print("  Prueba con --copy o ejecuta como Administrador.")
                sys.exit(1)

    print()
    if total_created:
        print(f"[deploy] {total_created} enlace(s) creado(s).")
    if total_skipped:
        print(f"[deploy] {total_skipped} enlace(s) ya estaban actualizados.")
    if not total_created and not total_skipped:
        print("[deploy] Nada que hacer.")


def deploy_copy(df_path: str) -> None:
    total_copied = 0

    for src_dir, dst_rel in _MAPPINGS:
        files = _lua_files(src_dir)
        if not files:
            continue

        dst_dir = os.path.join(df_path, dst_rel)
        print(f"\n[deploy] {dst_rel}/")
        total_copied += _deploy_copy_for(src_dir, dst_dir)

    # Despliegue de carpetas de mods a AppData
    mods_src = os.path.join(_ROOT, "mod", "mods")
    appdata = os.environ.get("APPDATA")
    if appdata and os.path.isdir(mods_src):
        mods_dst = os.path.join(appdata, "Bay 12 Games", "Dwarf Fortress", "mods")
        
        # Comprobar si hay carpetas que desplegar antes de imprimir
        folders = [f for f in os.listdir(mods_src) if os.path.isdir(os.path.join(mods_src, f))]
        if folders:
            print(f"\n[deploy] carpetas mods -> {mods_dst}")
            total_copied += _deploy_copy_for_mods(mods_src, mods_dst)

    print()
    print(f"[deploy] {total_copied} archivo(s)/carpeta(s) copiado(s).")


if __name__ == "__main__":
    cfg = _load_config()
    df_path = _get_df_path(cfg)
    if not df_path:
        print("[deploy] ERROR: 'DF_INSTALL_PATH' no esta configurado en .env ni en config.yaml")
        sys.exit(1)

    if "--copy" in sys.argv:
        deploy_copy(df_path)
    else:
        deploy_symlink(df_path)
