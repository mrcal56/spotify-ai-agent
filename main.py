"""
Punto de entrada de la aplicación.

Responsabilidad única de este archivo: correr el loop interactivo de
terminal — leer lo que escribe el usuario, envolverlo con build_safe_task,
pasárselo al agente, y mostrar la respuesta (o el error).

Este archivo no sabe nada de Spotify ni de cómo está armado el agente
por dentro; solo orquesta: entrada del usuario -> prompt -> agente -> salida.
"""

import logging
import re
import unicodedata
from collections.abc import Callable

from logging_config import configure_logging
from prompts import build_safe_task
from tools import (
    spotify_add_track_to_queue_from_search,
    spotify_current_playback,
    spotify_dj_queue_similar_to_current,
    spotify_list_devices,
    spotify_next_track,
    spotify_pause_playback,
    spotify_previous_track,
    spotify_resume_playback,
    spotify_transfer_playback,
)

logger = logging.getLogger(__name__)


FAST_PLAYBACK_COMMANDS: tuple[tuple[tuple[str, ...], Callable[[], str]], ...] = (
    (
        (
            "lista mis dispositivos",
            "que dispositivos tengo",
            "dispositivos disponibles",
            "muestra dispositivos spotify",
            "donde puedo reproducir spotify",
        ),
        spotify_list_devices,
    ),
    (
        (
            "que esta sonando",
            "que suena ahora",
            "cual cancion esta sonando",
            "spotify esta reproduciendo",
            "que estoy escuchando",
        ),
        spotify_current_playback,
    ),
    (
        (
            "pausa la musica",
            "pausar musica",
            "pausa spotify",
            "deten la musica",
            "para la musica",
        ),
        lambda: spotify_pause_playback(confirm="SI_PAUSAR"),
    ),
    (
        (
            "continua la musica",
            "reanuda la musica",
            "sigue reproduciendo",
            "continua spotify",
            "resume spotify",
        ),
        lambda: spotify_resume_playback(confirm="SI_REANUDAR"),
    ),
    (
        (
            "siguiente cancion",
            "pasa la cancion",
            "salta a la siguiente",
            "pon la siguiente",
            "next track",
        ),
        lambda: spotify_next_track(confirm="SI_SIGUIENTE"),
    ),
    (
        (
            "cancion anterior",
            "vuelve a la anterior",
            "regresa la cancion",
            "pon la anterior",
            "previous track",
        ),
        lambda: spotify_previous_track(confirm="SI_ANTERIOR"),
    ),
)

QUEUE_COMMAND_PREFIXES = (
    "agrega",
    "anade",
    "pon",
    "mete",
    "queue",
)

QUEUE_COMMAND_SUFFIXES = (
    "a la cola",
    "en la cola",
    "a cola",
    "despues",
    "despues de esta",
)

DJ_COMMAND_PHRASES = (
    "modo dj",
    "pon algo parecido",
    "agrega algo similar a la cola",
    "sorprendeme",
    "dj pon musica parecida",
)

DJ_POPULAR_HINTS = (
    "popular",
    "hits",
    "conocidas",
    "famosas",
)

DJ_DISCOVER_HINTS = (
    "descubre",
    "discovery",
    "sorprendeme",
    "nuevo",
    "nueva",
)


def _normalize_text(text: str) -> str:
    """Normaliza texto del usuario para detectar comandos rápidos."""
    without_accents = unicodedata.normalize("NFKD", text)
    ascii_text = without_accents.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().split())


def _extract_queue_query(normalized_task: str) -> str | None:
    """Extrae la busqueda de frases simples para agregar a cola."""
    is_queue_request = (
        " cola" in f" {normalized_task} "
        or " despues" in f" {normalized_task} "
        or normalized_task.startswith("queue ")
    )

    if not is_queue_request:
        return None

    for prefix in QUEUE_COMMAND_PREFIXES:
        prefix_with_space = f"{prefix} "
        if not normalized_task.startswith(prefix_with_space):
            continue

        query = normalized_task.removeprefix(prefix_with_space).strip()
        for suffix in QUEUE_COMMAND_SUFFIXES:
            if query.endswith(f" {suffix}"):
                query = query.removesuffix(f" {suffix}").strip()
            elif query.endswith(suffix):
                query = query.removesuffix(suffix).strip()

        return query or None

    return None


def _extract_device_id(normalized_task: str) -> str | None:
    """Extrae device_id de frases como 'transfiere al device_id abc123'."""
    match = re.search(r"\bdevice[_ ]?id\s+([^\s]+)", normalized_task)
    if match:
        return match.group(1).strip()

    return None


def _detect_dj_mode(normalized_task: str) -> str | None:
    """Detecta comandos DJ y devuelve el modo solicitado."""
    if not any(phrase in normalized_task for phrase in DJ_COMMAND_PHRASES):
        return None

    if any(hint in normalized_task for hint in DJ_POPULAR_HINTS):
        return "popular"
    if any(hint in normalized_task for hint in DJ_DISCOVER_HINTS):
        return "discover"

    return "similar"


def try_fast_playback_command(user_task: str) -> str | None:
    """Ejecuta controles simples de Spotify sin pasar por el LLM."""
    normalized_task = _normalize_text(user_task)

    dj_mode = _detect_dj_mode(normalized_task)
    if dj_mode:
        logger.info("Comando rapido DJ detectado: %s (mode=%s)", user_task, dj_mode)
        return spotify_dj_queue_similar_to_current(
            queue_count=3,
            mode=dj_mode,
            confirm="SI_DJ",
        )

    queue_query = _extract_queue_query(normalized_task)
    if queue_query:
        logger.info("Comando rapido de cola detectado: %s", user_task)
        return spotify_add_track_to_queue_from_search(
            query=queue_query,
            confirm="SI_COLA",
        )

    if "transfer" in normalized_task or "transfiere" in normalized_task:
        device_id = _extract_device_id(normalized_task)
        logger.info("Comando rapido de transferencia detectado: %s", user_task)

        if device_id:
            return spotify_transfer_playback(
                device_id=device_id,
                confirm="SI_TRANSFERIR",
            )

        return spotify_list_devices()

    for phrases, action in FAST_PLAYBACK_COMMANDS:
        if any(phrase in normalized_task for phrase in phrases):
            logger.info("Comando rapido de reproduccion detectado: %s", user_task)
            return action()

    return None


def run_agent_task(user_task: str) -> str:
    """Carga el agente solo cuando el comando no se puede resolver directo."""
    from agent import agent

    safe_task = build_safe_task(user_task)
    return agent.run(safe_task)


def main() -> None:
    """Corre el loop interactivo de terminal hasta que el usuario salga."""
    configure_logging()
    logger.info("Agente Spotify iniciado.")

    print("Agente Spotify listo.")
    print("Escribe 'salir' para terminar.\n")

    while True:
        user_task = input("Tú: ").strip()
        if not user_task:
            print("Escribe una instrucción válida.\n")
            continue

        if user_task.lower() in ["salir", "exit", "quit"]:
            logger.info("Usuario finalizó la sesión.")
            print("Agente finalizado.")
            break

        try:
            response = try_fast_playback_command(user_task)
            if response is None:
                response = run_agent_task(user_task)

            print("\nRespuesta del agente:\n")
            print(response)
            print("\n" + "-" * 80 + "\n")
        except Exception as error:
            # exc_info=True guarda el traceback completo en agent.log,
            # para que puedas revisar después exactamente dónde falló.
            # Al usuario en consola le mostramos solo el mensaje simple.
            logger.error("Error al ejecutar la tarea del agente: %s", error, exc_info=True)
            print("\nOcurrió un error:")
            print(error)
            print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    main()
