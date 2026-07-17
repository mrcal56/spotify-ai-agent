"""
Módulo que configura el modelo de lenguaje y el agente.

Responsabilidad única de este archivo: construir el objeto `agent` ya
listo para usarse (con su modelo y sus tools conectadas). main.py solo
necesita importar `agent` de aquí y llamar a `agent.run(...)`.

Si algún día cambias de modelo (por ejemplo, de Ollama local a un modelo
en la nube vía LiteLLM), este es el único archivo que necesitas tocar.
"""

import os

# LiteLLM tiene su propio logger interno ("LiteLLM"), separado del logging
# de nuestra app (logging_config.py) — configurar el logger raíz de Python
# no lo silencia. La única forma confiable, según la documentación oficial
# de LiteLLM, es esta variable de entorno, y debe asignarse ANTES de que
# litellm se importe (por eso va antes del import de smolagents).
os.environ.setdefault("LITELLM_LOG", "ERROR")

from smolagents import CodeAgent, LiteLLMModel
import litellm

# Respaldo adicional a LITELLM_LOG (documentado en la guía de "Best
# Practices" de LiteLLM): apaga explícitamente sus banderas de debug,
# por si alguna versión de la librería no respeta solo la variable
# de entorno.
litellm.suppress_debug_info = True
litellm.set_verbose = False

from tools import (
    spotify_check_auth,
    spotify_list_user_playlists,
    spotify_search_songs,
    spotify_search_artists,
    spotify_recently_played,
    spotify_current_playback,
    spotify_pause_playback,
    spotify_resume_playback,
    spotify_next_track,
    spotify_previous_track,
    spotify_add_track_to_queue_from_search,
    spotify_list_devices,
    spotify_transfer_playback,
    spotify_dj_queue_similar_to_current,
    spotify_recommend_from_playlist,
    spotify_add_tracks_to_playlist_from_search,
    spotify_create_playlist_from_search,
)


# Modelo local corriendo en Ollama (http://localhost:11434), usando
# LiteLLM como capa de compatibilidad para que smolagents pueda hablarle
# con la misma interfaz que usaría para OpenAI, Anthropic, etc.
model = LiteLLMModel(
    model_id="ollama_chat/llama3.2:3b",
    api_base="http://localhost:11434",
    api_key="ollama",
    temperature=0.2,
)

def reject_bad_final_answer(final_answer, agent_memory=None, agent=None) -> bool:
    """Evita respuestas finales con código o instrucciones internas."""
    answer = str(final_answer)

    forbidden_fragments = [
        "```python",
        "final_answer(",
        "spotify_check_auth(",
        "spotify_list_user_playlists(",
        "spotify_search_songs(",
        "spotify_search_artists(",
        "spotify_recently_played(",
        "spotify_current_playback(",
        "spotify_pause_playback(",
        "spotify_resume_playback(",
        "spotify_next_track(",
        "spotify_previous_track(",
        "spotify_add_track_to_queue_from_search(",
        "spotify_list_devices(",
        "spotify_transfer_playback(",
        "spotify_dj_queue_similar_to_current(",
        "spotify_recommend_from_playlist(",
        "spotify_add_tracks_to_playlist_from_search(",
        "spotify_create_playlist_from_search(",
        "print(",
        "for ",
        "song['",
        'song["',
    ]

    return not any(fragment in answer for fragment in forbidden_fragments)

# El CodeAgent es el tipo de agente de smolagents que escribe y ejecuta
# código Python para decidir qué tool llamar (en vez de, por ejemplo,
# responder solo con JSON). max_steps=3 limita cuántas "vueltas" de
# razonamiento/acción puede dar antes de forzar una respuesta final,
# lo cual evita loops infinitos si el modelo se confunde.
agent = CodeAgent(
    model=model,
    tools=[
        spotify_check_auth,
        spotify_list_user_playlists,
        spotify_search_songs,
        spotify_search_artists,
        spotify_recently_played,
        spotify_current_playback,
        spotify_pause_playback,
        spotify_resume_playback,
        spotify_next_track,
        spotify_previous_track,
        spotify_add_track_to_queue_from_search,
        spotify_list_devices,
        spotify_transfer_playback,
        spotify_dj_queue_similar_to_current,
        spotify_recommend_from_playlist,
        spotify_add_tracks_to_playlist_from_search,
        spotify_create_playlist_from_search,
    ],
    max_steps=3,
    verbosity_level=1,
    final_answer_checks=[reject_bad_final_answer],
)
