import requests
from .base import BaseTranslator


class LibreTranslator(BaseTranslator):
    def __init__(self, url: str, api_key: str = ""):
        self.url = url.rstrip("/")
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "libretranslate"

    def translate(self, text: str, target_lang: str = "es") -> str:
        payload = {
            "q": text,
            "source": "en",
            "target": target_lang,
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key

        response = requests.post(f"{self.url}/translate", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["translatedText"]
