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

def stands_up(text: str, match: re.Match) -> str:
    """
    Patrón: ^(.+?) stands up\\.$
    Ejemplos:
      "Puc stands up."             → "Puc se levanta."
      "Standing Stone stands up."  → "Standing Stone se levanta."
    """
    name = match.group(1)
    return f"{name} se levanta."


def pets_action(text: str, match: re.Match) -> str:
    """
    Patrón: ^(.+?) pets (.+?)\\.$
    Ejemplos:
      "Tul pets Puc."               → "Tul acaricia a Puc."
      "Urist McPet pets Doggo."     → "Urist McPet acaricia a Doggo."
    """
    actor  = match.group(1)
    target = match.group(2)
    return f"{actor} acaricia a {target}."


def feel_so_good(text: str, match: re.Match) -> str:
    """
    Patrón: ^(.+?): I feel so good!$
    Ejemplos:
      "Pik: I feel so good!"          → "Pik: ¡Me siento tan bien!"
      "Urist McHappy: I feel so good!" → "Urist McHappy: ¡Me siento tan bien!"
    """
    name = match.group(1)
    return f"{name}: ¡Me siento tan bien!"


def ignore_line(text: str, match: re.Match) -> str:
    """
    Ignora la línea intencionalmente, devolviendo una cadena vacía.
    Al devolver una cadena vacía, el watcher la ignorará y no la imprimirá en la consola.
    """
    return ""
