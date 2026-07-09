"""
Módulo que configura el logging de toda la aplicación.

Responsabilidad única de este archivo: definir CÓMO se ven y A DÓNDE
van los logs (consola + archivo), en un solo lugar. El resto de los
módulos (tools.py, spotify_client.py, main.py) solo hacen:

    import logging
    logger = logging.getLogger(__name__)
    logger.info("...")

y no necesitan saber nada sobre formato ni destino de los logs.
"""

import logging


def configure_logging() -> None:
    """Configura el logging raíz de la aplicación.

    Debe llamarse una sola vez, al arrancar el programa (desde main.py),
    antes de que cualquier otro módulo empiece a loguear.

    Configura dos destinos (handlers) para cada mensaje de log:
    - Consola: solo mensajes de nivel INFO o superior, formato corto,
      pensado para que el usuario vea algo legible mientras usa el CLI.
    - Archivo (agent.log): TODO se guarda ahí (incluyendo DEBUG),
      con fecha/hora y nombre del módulo, útil para revisar después
      qué pasó exactamente si algo falló.
    """
    logger = logging.getLogger()  # logger raíz: afecta a toda la app
    logger.setLevel(logging.DEBUG)

    # Evita agregar handlers duplicados si configure_logging() se
    # llamara más de una vez por error (por ejemplo, en pruebas).
    if logger.handlers:
        return

    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")

    file_handler = logging.FileHandler("agent.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)