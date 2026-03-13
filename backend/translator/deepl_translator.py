import deepl
from .base import BaseTranslator


class DeepLTranslator(BaseTranslator):
    def __init__(self, api_key: str):
        self.client = deepl.Translator(api_key)
        self.glossary_id: str | None = None

    @property
    def name(self) -> str:
        return "deepl"

    def translate(self, text: str, target_lang: str = "es") -> str:
        kwargs: dict = {"target_lang": target_lang.upper()}
        if self.glossary_id:
            # El glosario es en→es, por lo que hay que fijar source_lang explícitamente
            kwargs["source_lang"] = "EN"
            kwargs["glossary"] = self.glossary_id
        result = self.client.translate_text(text, **kwargs)
        return result.text
