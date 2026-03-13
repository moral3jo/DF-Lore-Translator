import requests
from .base import BaseTranslator

_URL = "https://api.cognitive.microsofttranslator.com/translate"


class AzureTranslator(BaseTranslator):
    def __init__(self, api_key: str, region: str):
        self.api_key = api_key
        self.region = region

    @property
    def name(self) -> str:
        return "azure"

    def translate(self, text: str, target_lang: str = "es") -> str:
        response = requests.post(
            _URL,
            params={"api-version": "3.0", "to": target_lang},
            headers={
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Ocp-Apim-Subscription-Region": self.region,
                "Content-Type": "application/json",
            },
            json=[{"Text": text}],
            timeout=30,
        )
        response.raise_for_status()
        return response.json()[0]["translations"][0]["text"]
