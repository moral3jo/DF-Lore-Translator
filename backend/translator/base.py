from abc import ABC, abstractmethod


class BaseTranslator(ABC):
    """Contrato común para todos los motores de traducción."""

    @abstractmethod
    def translate(self, text: str, target_lang: str = "es") -> str:
        """Traduce text al idioma target_lang y devuelve el texto traducido."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador del motor, devuelto en la respuesta de la API."""
        ...
