"""
deploy.py — Conecta mod/scripts/ con la carpeta de scripts de DFHack.

Uso: python deploy.py [--copy]

Sin argumentos: crea un enlace simbólico (recomendado, los cambios son instantáneos).
Con --copy:      copia los archivos manualmente (útil si los enlaces simbólicos no están disponibles).
"""

import os
import sys
import shutil
import yaml
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_ROOT, ".env"))

_CONFIG_PATH = os.path.join(_ROOT, "backend", "config.yaml")
_MOD_SCRIPTS = os.path.join(_ROOT, "mod", "scripts")


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_df_path(cfg: dict) -> str:
    """Lee la ruta de DF: primero env, luego config.yaml."""
    return os.environ.get("DF_INSTALL_PATH", "") or cfg.get("df_install_path", "")


def _dfhack_scripts_path(df_install_path: str) -> str:
    return os.path.join(df_install_path, "dfhack-config", "scripts")


def deploy_symlink(target: str) -> None:
    if os.path.islink(target):
        print(f"[deploy] El enlace ya existe: {target}")
        return
    if os.path.exists(target):
        print(f"[deploy] ERROR: {target} ya existe y no es un enlace simbólico.")
        print("         Renómbralo o elimínalo manualmente antes de continuar.")
        sys.exit(1)

    # En Windows se necesita ejecutar como Administrador o tener Developer Mode activo
    os.makedirs(os.path.dirname(target), exist_ok=True)
    os.symlink(_MOD_SCRIPTS, target, target_is_directory=True)
    print(f"[deploy] Enlace simbólico creado:")
    print(f"         {target}  →  {_MOD_SCRIPTS}")


def deploy_copy(target: str) -> None:
    os.makedirs(target, exist_ok=True)
    copied = 0
    for name in os.listdir(_MOD_SCRIPTS):
        if name.startswith(".") or name.startswith("_"):
            continue
        src = os.path.join(_MOD_SCRIPTS, name)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(target, name)
        shutil.copy2(src, dst)
        copied += 1
    print(f"[deploy] {copied} archivo(s) copiado(s) a {target}")


if __name__ == "__main__":
    cfg = _load_config()
    df_path = _get_df_path(cfg)
    if not df_path:
        print("[deploy] ERROR: 'DF_INSTALL_PATH' no está configurado en .env ni 'df_install_path' en config.yaml")
        sys.exit(1)

    dfhack_target = _dfhack_scripts_path(df_path)

    if "--copy" in sys.argv:
        deploy_copy(dfhack_target)
    else:
        try:
            deploy_symlink(dfhack_target)
        except OSError as e:
            print(f"[deploy] No se pudo crear el enlace simbólico: {e}")
            print("[deploy] Prueba con --copy o ejecuta el script como Administrador.")
            sys.exit(1)
