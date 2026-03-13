import os

from .base import BaseTranslator

_VALID_ENGINES = ("deepl", "google", "azure")
_PLACEHOLDER = "TU_CLAVE_AQUI"


def _get_key(env_var: str, cfg: dict, yaml_key: str) -> str:
    """Lee una clave: primero variable de entorno, luego config.yaml."""
    return os.environ.get(env_var, "") or cfg.get(yaml_key, "")


def get_translator(config: dict) -> BaseTranslator:
    """Lee config y devuelve la instancia del motor de traducción activo."""
    engine = os.environ.get("TRANSLATION_ENGINE", "") or config.get("engine", "deepl")

    if engine == "deepl":
        from .deepl_translator import DeepLTranslator
        cfg = config.get("deepl", {})
        api_key = _get_key("DEEPL_API_KEY", cfg, "api_key")
        if not api_key or api_key == _PLACEHOLDER:
            raise ValueError(
                "Debes configurar DEEPL_API_KEY en .env (o deepl.api_key en config.yaml)"
            )
        return DeepLTranslator(api_key=api_key)

    if engine == "google":
        from .google_translator import GoogleTranslator
        cfg = config.get("google", {})
        api_key = _get_key("GOOGLE_API_KEY", cfg, "api_key")
        if not api_key or api_key == _PLACEHOLDER:
            raise ValueError(
                "Debes configurar GOOGLE_API_KEY en .env (o google.api_key en config.yaml)"
            )
        return GoogleTranslator(api_key=api_key)

    if engine == "azure":
        from .azure_translator import AzureTranslator
        cfg = config.get("azure", {})
        api_key = _get_key("AZURE_API_KEY", cfg, "api_key")
        region = os.environ.get("AZURE_REGION", "") or cfg.get("region", "")
        if not api_key or api_key == _PLACEHOLDER:
            raise ValueError(
                "Debes configurar AZURE_API_KEY en .env (o azure.api_key en config.yaml)"
            )
        if not region:
            raise ValueError(
                "Debes configurar AZURE_REGION en .env (o azure.region en config.yaml)"
            )
        return AzureTranslator(api_key=api_key, region=region)

    raise ValueError(
        f"Motor desconocido: '{engine}'. Valores válidos: {', '.join(_VALID_ENGINES)}"
    )

