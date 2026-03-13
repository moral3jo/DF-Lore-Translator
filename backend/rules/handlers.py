"""
Handlers del Rule Engine.

Cada función recibe:
  text  — el texto original completo
  match — el objeto re.Match ya calculado por engine.py

Y devuelve el texto procesado listo para mostrar.
El nombre de la función debe coincidir exactamente con el campo 'handler' en rules.yaml.
"""

import re


def job_completed(text: str, match: re.Match) -> str:
    """
    Patrón: ^(.+?) \\((\\d+)\\) has been completed\\.$
    Ejemplos:
      "Make Wooden Bed (3) has been completed."   → "Make Wooden Bed (3) Completado"
      "Brew drink from plant (1) has been completed." → "Brew drink from plant (1) Completado"

    El nombre del trabajo se mantiene en inglés para que el jugador
    pueda identificarlo tal como aparece en los menús del juego.
    """
    item = match.group(1)
    count = match.group(2)
    return f"{item} ({count}) Completado"
