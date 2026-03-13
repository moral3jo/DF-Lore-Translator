import requests
from .base import BaseTranslator

_URL = "https://translation.googleapis.com/language/translate/v2"


class GoogleTranslator(BaseTranslator):
    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "google"

    def translate(self, text: str, target_lang: str = "es") -> str:
        response = requests.post(
            _URL,
            params={"key": self.api_key},
            json={"q": text, "target": target_lang, "format": "text"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["data"]["translations"][0]["translatedText"]
