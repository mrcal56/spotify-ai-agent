"""
Módulo con el prompt del sistema que envuelve cada tarea del usuario.

Responsabilidad única de este archivo: construir el texto completo que
se le manda al agente, combinando las reglas fijas (en español e inglés,
tal como las necesita el modelo) con la tarea puntual que escribió el
usuario en la terminal.

Por qué esto vive en su propio archivo y no como un string suelto en
main.py: es un bloque largo (~100 líneas) que probablemente vas a seguir
ajustando a medida que pruebes el agente (agregar reglas, quitar otras).
Tenerlo separado facilita editarlo sin tocar la lógica del loop principal,
y facilita escribir pruebas sobre el prompt en el futuro si quieres.
"""

def build_safe_task(user_task: str) -> str:
    """Construye una tarea segura y breve para el agente."""
    return f"""
Responde siempre en español.

Reglas obligatorias:
- Usa unicamente las tools disponibles.
- No inventes datos de Spotify.
- No expliques como usar las tools.
- Ejecuta la tool adecuada y entrega el resultado final al usuario.
- Si el usuario pregunta por login, OAuth, permisos, scopes o sesion de Spotify, usa spotify_check_auth.
- Si el usuario pregunta por sus playlists existentes, usa spotify_list_user_playlists.
- Si el usuario pregunta que esta sonando, si Spotify esta pausado/reproduciendo o cual es el dispositivo activo, usa spotify_current_playback.
- Si el usuario pide pausar musica, usa spotify_pause_playback con confirm="SI_PAUSAR" solo si la instruccion es clara.
- Si el usuario pide reanudar o continuar musica, usa spotify_resume_playback con confirm="SI_REANUDAR" solo si la instruccion es clara.
- Si el usuario pide siguiente cancion, usa spotify_next_track con confirm="SI_SIGUIENTE" solo si la instruccion es clara.
- Si el usuario pide cancion anterior, usa spotify_previous_track con confirm="SI_ANTERIOR" solo si la instruccion es clara.
- Si el usuario pide agregar una cancion a la cola o poner algo despues, usa spotify_add_track_to_queue_from_search con confirm="SI_COLA" solo si hay una busqueda clara.
- Si el usuario pide ver dispositivos disponibles, usa spotify_list_devices.
- Si el usuario pide transferir reproduccion pero no da device_id, usa spotify_list_devices y pide que elija un device_id.
- Si el usuario pide transferir reproduccion y da device_id, usa spotify_transfer_playback con confirm="SI_TRANSFERIR".
- Si el usuario pide modo DJ, algo parecido a lo actual, recomendaciones similares o sorprenderlo con musica relacionada, usa spotify_dj_queue_similar_to_current con queue_count=3 y confirm="SI_DJ". Usa mode="popular" si pide popular/hits/conocidas, mode="discover" si pide descubrir/sorprender/nuevo, si no usa mode="similar".
- Si la tarea pide crear una playlist, solo hazlo si hay una confirmacion clara del usuario.
- Si la tarea pide agregar canciones a una playlist existente, solo hazlo si hay una confirmacion clara del usuario y un playlist_id.
- Si usas cualquier tool de Spotify, guarda el resultado en una variable llamada result.
- Despues de llamar una tool, responde unicamente con final_answer(result).
- Esta prohibido usar print().
- Esta prohibido usar for sobre el resultado de una tool.
- Esta prohibido acceder al resultado como diccionario, lista o JSON.
- Si el usuario pide 3 canciones, usa limit=3. Si pide 5, usa limit=5. Respeta exactamente el numero solicitado.

Tarea del usuario:
{user_task}
"""
