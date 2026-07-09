"""
Punto de entrada de la aplicación.

Responsabilidad única de este archivo: correr el loop interactivo de
terminal — leer lo que escribe el usuario, envolverlo con build_safe_task,
pasárselo al agente, y mostrar la respuesta (o el error).

Este archivo no sabe nada de Spotify ni de cómo está armado el agente
por dentro; solo orquesta: entrada del usuario -> prompt -> agente -> salida.
"""

import logging

from agent import agent
from logging_config import configure_logging
from prompts import build_safe_task

logger = logging.getLogger(__name__)


def main() -> None:
    """Corre el loop interactivo de terminal hasta que el usuario salga."""
    configure_logging()
    logger.info("Agente Spotify iniciado.")

    print("Agente Spotify listo.")
    print("Escribe 'salir' para terminar.\n")

    while True:
        user_task = input("Tú: ").strip()

        if user_task.lower() in ["salir", "exit", "quit"]:
            logger.info("Usuario finalizó la sesión.")
            print("Agente finalizado.")
            break

        safe_task = build_safe_task(user_task)

        try:
            response = agent.run(safe_task)
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