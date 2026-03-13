"""Clase base abstracta para todos los visualizadores."""

from abc import ABC, abstractmethod


class BaseVisualizer(ABC):
    """Contrato que todo visualizador debe cumplir."""

    @abstractmethod
    def display(self, text: str) -> None:
        """Muestra un texto traducido (puede contener markup DFHack)."""
        ...

    def close(self) -> None:
        """Limpieza opcional al cerrar el visualizador."""
