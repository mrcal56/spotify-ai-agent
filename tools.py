"""
Módulo con las herramientas (tools) que el agente de IA puede usar.

Responsabilidad única de este archivo: definir las funciones decoradas
con @tool que smolagents expone al modelo. Cada tool sabe cómo hablar
con la Web API de Spotify (a través de spotify_client.py) y devuelve
siempre un string ya formateado en español, listo para final_answer().

Cada tool atrapa sus propios errores y siempre devuelve un string
entendible en español — nunca deja que una excepción se propague sin
control, porque eso tumbaría el proceso completo del agente.
"""

import json
import logging
import time
from pathlib import Path
from typing import List

from smolagents import tool
from spotipy.exceptions import SpotifyException

from spotify_client import get_spotify_client

logger = logging.getLogger(__name__)


def _read_spotify_cache_summary() -> tuple[str, str]:
    """Devuelve scope y expiracion del cache sin exponer tokens."""
    cache_path = Path(".spotify_cache")

    if not cache_path.exists():
        return "No encontrado", "No disponible"

    try:
        cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "No se pudo leer", "No disponible"

    scope = cache_data.get("scope") or "No disponible"
    expires_at = cache_data.get("expires_at")

    if not expires_at:
        return scope, "No disponible"

    seconds_left = int(expires_at - time.time())
    if seconds_left <= 0:
        expiration = "Expirado"
    else:
        minutes_left = max(1, seconds_left // 60)
        expiration = f"Expira en aproximadamente {minutes_left} minuto(s)"

    return scope, expiration


def format_track(track: dict) -> str:
    """Formatea un track de Spotify (dict crudo de la API) a texto legible."""
    name = track.get("name", "Unknown track")
    artists = ", ".join(artist["name"] for artist in track.get("artists", []))
    album = track.get("album", {}).get("name", "Unknown album")
    url = track.get("external_urls", {}).get("spotify", "No URL")
    popularity = track.get("popularity", "N/A")

    return (
        f"Canción: {name}\n"
        f"Artista(s): {artists}\n"
        f"Álbum: {album}\n"
        f"Popularidad: {popularity}\n"
        f"Spotify: {url}"
    )


def _format_playback_item(item: dict) -> str:
    """Formatea el item que Spotify reporta como reproduccion actual."""
    item_type = item.get("type", "contenido")
    name = item.get("name", "Sin nombre")
    url = item.get("external_urls", {}).get("spotify", "No URL")

    if item_type == "track":
        artists = ", ".join(artist["name"] for artist in item.get("artists", []))
        album = item.get("album", {}).get("name", "Album no disponible")
        return (
            f"Cancion: {name}\n"
            f"Artista(s): {artists}\n"
            f"Album: {album}\n"
            f"Spotify: {url}"
        )

    show_name = item.get("show", {}).get("name", "Show no disponible")
    return (
        f"Contenido: {name}\n"
        f"Tipo: {item_type}\n"
        f"Show: {show_name}\n"
        f"Spotify: {url}"
    )


def _handle_spotify_error(error: SpotifyException) -> str:
    """Traduce un SpotifyException de la API a un mensaje claro en español.

    spotipy adjunta el código HTTP que devolvió Spotify en `error.http_status`.
    Usamos ese código para dar una explicación distinta según el problema,
    en vez de mostrarle al usuario el texto crudo de la excepción.
    """
    status = getattr(error, "http_status", None)

    if status == 401:
        return (
            "Tu sesión de Spotify expiró o no es válida. "
            "Vuelve a autorizar la aplicación e inténtalo de nuevo."
        )
    if status == 403:
        return (
            "Spotify rechazo la solicitud por falta de permisos, cuenta Premium "
            "o dispositivo activo. Si acabas de agregar permisos nuevos, borra "
            ".spotify_cache y vuelve a autorizar la aplicacion. Tambien revisa "
            "que tu cuenta este agregada en Users and Access para esta app."
        )
    if status == 429:
        return (
            "Spotify está limitando las solicitudes por exceso de peticiones "
            "(rate limit). Espera unos segundos e inténtalo de nuevo."
        )

    return f"Spotify devolvió un error (código {status}): {error.msg}"


@tool
def spotify_check_auth() -> str:
    """Checks the current Spotify authentication status without exposing secrets.

    Use this tool when the user asks to:
    - check if Spotify login/authentication is working
    - verify the current Spotify account
    - debug OAuth, scopes, token cache or permission problems
    - confirm whether playlist permissions are available

    Important usage rules:
    - This tool does not create, update or delete anything in Spotify.
    - This tool returns a formatted string, not a dictionary.
    - Do not expose access tokens or refresh tokens.
    - After calling this tool, pass the returned text directly to final_answer.
    - Correct usage example:
      result = spotify_check_auth()
      final_answer(result)
    """
    logger.info("spotify_check_auth llamada")

    try:
        sp = get_spotify_client()
        user = sp.current_user()
        scope, expiration = _read_spotify_cache_summary()

        display_name = user.get("display_name") or "Sin nombre visible"
        user_id = user.get("id", "No disponible")
        country = user.get("country", "No disponible")
        product = user.get("product", "No disponible")
        url = user.get("external_urls", {}).get("spotify", "No URL")

        required_playlist_scopes = [
            "playlist-modify-private",
            "playlist-modify-public",
            "playlist-read-private",
            "playlist-read-collaborative",
            "user-read-currently-playing",
            "user-read-playback-state",
            "user-modify-playback-state",
        ]
        missing_scopes = [
            item for item in required_playlist_scopes if item not in scope
        ]

        output = [
            "Autenticacion de Spotify funcionando correctamente.",
            "",
            f"Usuario: {display_name}",
            f"ID: {user_id}",
            f"Pais: {country}",
            f"Plan: {product}",
            f"Perfil: {url}",
            "",
            f"Scopes cacheados: {scope}",
            f"Estado del token: {expiration}",
        ]

        if missing_scopes:
            output.append("")
            output.append("Scopes recomendados faltantes:")
            output.extend(f"- {item}" for item in missing_scopes)
            output.append("Borra .spotify_cache y vuelve a iniciar sesion.")
        else:
            output.append("")
            output.append("Permisos de playlist y reproduccion detectados correctamente.")

        return "\n".join(output)

    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_check_auth: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_check_auth: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_check_auth: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al revisar la autenticacion: {error}"


@tool
def spotify_current_playback() -> str:
    """Gets the current Spotify playback state.

    Use this tool when the user asks to:
    - know what is currently playing
    - check if Spotify is playing or paused
    - see the active Spotify device

    Important usage rules:
    - This tool only reads playback data. It does not modify Spotify.
    - This tool returns a formatted string, not a dictionary.
    - After calling this tool, pass the returned text directly to final_answer.
    - Correct usage example:
      result = spotify_current_playback()
      final_answer(result)
    """
    logger.info("spotify_current_playback llamada")

    try:
        sp = get_spotify_client()
        playback = sp.current_playback()

        if not playback:
            return (
                "No hay reproduccion activa en Spotify. "
                "Abre Spotify en algun dispositivo e intentalo de nuevo."
            )

        device = playback.get("device") or {}
        item = playback.get("item") or {}
        is_playing = playback.get("is_playing", False)
        shuffle_state = playback.get("shuffle_state", False)
        repeat_state = playback.get("repeat_state", "off")

        output = [
            "Reproduccion actual de Spotify:",
            "",
            _format_playback_item(item) if item else "No hay cancion o episodio activo.",
            "",
            f"Estado: {'Reproduciendo' if is_playing else 'Pausado'}",
            f"Dispositivo: {device.get('name', 'No disponible')}",
            f"Tipo de dispositivo: {device.get('type', 'No disponible')}",
            f"Volumen: {device.get('volume_percent', 'No disponible')}",
            f"Shuffle: {'Activado' if shuffle_state else 'Desactivado'}",
            f"Repeat: {repeat_state}",
        ]

        return "\n".join(output)

    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_current_playback: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_current_playback: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_current_playback: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al revisar la reproduccion: {error}"


@tool
def spotify_pause_playback(confirm: str) -> str:
    """Pauses the current Spotify playback.

    Use this tool only when the user explicitly asks to pause Spotify.

    Important usage rules:
    - This tool modifies playback state.
    - The user must provide confirmation with the exact value 'SI_PAUSAR'.
    - If confirm is not exactly 'SI_PAUSAR', playback will not be changed.
    - After calling this tool, pass the returned text directly to final_answer.

    Args:
        confirm: Safety confirmation. Must be exactly 'SI_PAUSAR' to pause playback.
    """
    if confirm != "SI_PAUSAR":
        return "No pause la musica. Para confirmar, usa confirm='SI_PAUSAR'."

    logger.info("spotify_pause_playback llamada")

    try:
        sp = get_spotify_client()
        sp.pause_playback()
        return "Musica pausada correctamente."
    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_pause_playback: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_pause_playback: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_pause_playback: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al pausar Spotify: {error}"


@tool
def spotify_resume_playback(confirm: str) -> str:
    """Resumes the current Spotify playback.

    Use this tool only when the user explicitly asks to resume Spotify.

    Important usage rules:
    - This tool modifies playback state.
    - The user must provide confirmation with the exact value 'SI_REANUDAR'.
    - If confirm is not exactly 'SI_REANUDAR', playback will not be changed.
    - After calling this tool, pass the returned text directly to final_answer.

    Args:
        confirm: Safety confirmation. Must be exactly 'SI_REANUDAR' to resume playback.
    """
    if confirm != "SI_REANUDAR":
        return "No reanude la musica. Para confirmar, usa confirm='SI_REANUDAR'."

    logger.info("spotify_resume_playback llamada")

    try:
        sp = get_spotify_client()
        sp.start_playback()
        return "Musica reanudada correctamente."
    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_resume_playback: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_resume_playback: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_resume_playback: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al reanudar Spotify: {error}"


@tool
def spotify_next_track(confirm: str) -> str:
    """Skips to the next Spotify track.

    Use this tool only when the user explicitly asks to skip to the next song.

    Important usage rules:
    - This tool modifies playback state.
    - The user must provide confirmation with the exact value 'SI_SIGUIENTE'.
    - If confirm is not exactly 'SI_SIGUIENTE', playback will not be changed.
    - After calling this tool, pass the returned text directly to final_answer.

    Args:
        confirm: Safety confirmation. Must be exactly 'SI_SIGUIENTE' to skip.
    """
    if confirm != "SI_SIGUIENTE":
        return "No cambie de cancion. Para confirmar, usa confirm='SI_SIGUIENTE'."

    logger.info("spotify_next_track llamada")

    try:
        sp = get_spotify_client()
        sp.next_track()
        return "Salté a la siguiente cancion correctamente."
    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_next_track: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_next_track: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_next_track: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al cambiar a la siguiente cancion: {error}"


@tool
def spotify_previous_track(confirm: str) -> str:
    """Skips to the previous Spotify track.

    Use this tool only when the user explicitly asks to go to the previous song.

    Important usage rules:
    - This tool modifies playback state.
    - The user must provide confirmation with the exact value 'SI_ANTERIOR'.
    - If confirm is not exactly 'SI_ANTERIOR', playback will not be changed.
    - After calling this tool, pass the returned text directly to final_answer.

    Args:
        confirm: Safety confirmation. Must be exactly 'SI_ANTERIOR' to go back.
    """
    if confirm != "SI_ANTERIOR":
        return "No cambie de cancion. Para confirmar, usa confirm='SI_ANTERIOR'."

    logger.info("spotify_previous_track llamada")

    try:
        sp = get_spotify_client()
        sp.previous_track()
        return "Volvi a la cancion anterior correctamente."
    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_previous_track: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_previous_track: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_previous_track: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al volver a la cancion anterior: {error}"


@tool
def spotify_add_track_to_queue_from_search(query: str, confirm: str) -> str:
    """Adds the first Spotify track found for a search query to the playback queue.

    Use this tool when the user asks to:
    - add a song to the queue
    - play something after the current song
    - put a specific song next without interrupting current playback

    Important usage rules:
    - This tool modifies playback queue.
    - The user must provide confirmation with the exact value 'SI_COLA'.
    - If confirm is not exactly 'SI_COLA', nothing will be added.
    - Use a concise search query with the song, artist or both.
    - After calling this tool, pass the returned text directly to final_answer.

    Args:
        query: Song search query. Example: 'FEIN Travis Scott'.
        confirm: Safety confirmation. Must be exactly 'SI_COLA' to add to queue.
    """
    if confirm != "SI_COLA":
        return "No agregue nada a la cola. Para confirmar, usa confirm='SI_COLA'."

    logger.info("spotify_add_track_to_queue_from_search llamada: query=%r", query)

    try:
        sp = get_spotify_client()
        query = query.strip()

        if not query:
            return "Debes indicar que cancion quieres agregar a la cola."

        results = sp.search(q=query, type="track", limit=1, market="MX")
        tracks = results.get("tracks", {}).get("items", [])

        if not tracks:
            return f"No encontre canciones en Spotify para agregar a la cola: {query}"

        track = tracks[0]
        uri = track.get("uri")

        if not uri:
            return "Encontre una cancion, pero Spotify no devolvio un URI valido."

        sp.add_to_queue(uri)

        return "Cancion agregada a la cola correctamente:\n\n" + format_track(track)

    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_add_track_to_queue_from_search: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_add_track_to_queue_from_search: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_add_track_to_queue_from_search: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al agregar la cancion a la cola: {error}"


@tool
def spotify_list_devices() -> str:
    """Lists Spotify playback devices available for the current account.

    Use this tool when the user asks to:
    - see available Spotify devices
    - transfer playback but has not provided a device_id yet
    - know where Spotify can play music

    Important usage rules:
    - This tool only reads device data. It does not modify Spotify.
    - If the user asks to transfer without a device_id, call this tool first.
    - After calling this tool, pass the returned text directly to final_answer.
    """
    logger.info("spotify_list_devices llamada")

    try:
        sp = get_spotify_client()
        results = sp.devices()
        devices = results.get("devices", [])

        if not devices:
            return (
                "No encontre dispositivos disponibles. "
                "Abre Spotify en tu telefono, computadora o navegador e intentalo de nuevo."
            )

        output = ["Dispositivos disponibles para Spotify:\n"]

        for index, device in enumerate(devices, start=1):
            output.append(
                f"[{index}] {device.get('name', 'Dispositivo sin nombre')}\n"
                f"ID: {device.get('id', 'No disponible')}\n"
                f"Tipo: {device.get('type', 'No disponible')}\n"
                f"Activo: {'Si' if device.get('is_active') else 'No'}\n"
                f"Restringido: {'Si' if device.get('is_restricted') else 'No'}\n"
                f"Volumen: {device.get('volume_percent', 'No disponible')}"
            )

        output.append(
            "\nPara transferir, dime: transfiere al device_id <ID>."
        )

        return "\n\n".join(output)

    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_list_devices: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_list_devices: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_list_devices: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al listar dispositivos: {error}"


@tool
def spotify_transfer_playback(device_id: str, confirm: str) -> str:
    """Transfers Spotify playback to a specific device_id.

    Use this tool only when the user explicitly asks to transfer playback and provides a device_id.

    Important usage rules:
    - This tool modifies playback state.
    - Do not guess the device_id. If the user did not provide one, use spotify_list_devices first.
    - The user must provide confirmation with the exact value 'SI_TRANSFERIR'.
    - If confirm is not exactly 'SI_TRANSFERIR', playback will not be transferred.
    - After calling this tool, pass the returned text directly to final_answer.

    Args:
        device_id: Spotify device ID returned by spotify_list_devices.
        confirm: Safety confirmation. Must be exactly 'SI_TRANSFERIR' to transfer playback.
    """
    if confirm != "SI_TRANSFERIR":
        return "No transferi la reproduccion. Para confirmar, usa confirm='SI_TRANSFERIR'."

    logger.info("spotify_transfer_playback llamada: device_id=%r", device_id)

    try:
        sp = get_spotify_client()
        device_id = device_id.strip()

        if not device_id:
            return "Debes proporcionar un device_id valido. Pide primero la lista de dispositivos."

        devices = sp.devices().get("devices", [])
        target_device = next(
            (device for device in devices if device.get("id") == device_id),
            None,
        )

        if target_device is None:
            return (
                "No encontre ese device_id entre tus dispositivos disponibles. "
                "Pide la lista de dispositivos y copia el ID exacto."
            )

        if target_device.get("is_restricted"):
            return "Ese dispositivo aparece como restringido y Spotify no permite transferirle reproduccion."

        sp.transfer_playback(device_id=device_id, force_play=False)

        return (
            "Reproduccion transferida correctamente.\n\n"
            f"Dispositivo: {target_device.get('name', 'No disponible')}\n"
            f"Tipo: {target_device.get('type', 'No disponible')}"
        )

    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_transfer_playback: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_transfer_playback: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_transfer_playback: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al transferir la reproduccion: {error}"


def _track_artist_names(track: dict) -> list[str]:
    """Extrae nombres de artistas de un track de Spotify."""
    return [artist.get("name", "") for artist in track.get("artists", []) if artist.get("name")]


def _get_current_track_context(sp) -> dict | None:
    """Devuelve contexto del track actual o None si no hay cancion activa."""
    playback = sp.current_playback()
    if not playback:
        return None

    track = playback.get("item") or {}
    if track.get("type") != "track":
        return None

    artists = _track_artist_names(track)
    if not artists:
        return None

    return {
        "id": track.get("id"),
        "uri": track.get("uri"),
        "name": track.get("name", ""),
        "artists": artists,
        "primary_artist": artists[0],
        "track": track,
    }


def _get_recent_track_context(sp, limit: int = 20) -> dict:
    """Resume historial reciente para evitar repetidos y puntuar candidatos."""
    recent_track_ids = set()
    recent_artist_counts = {}

    try:
        results = sp.current_user_recently_played(limit=limit)
    except SpotifyException:
        logger.warning("No se pudo leer historial reciente para DJ", exc_info=True)
        return {"track_ids": recent_track_ids, "artist_counts": recent_artist_counts}

    for item in results.get("items", []):
        track = item.get("track") or {}
        track_id = track.get("id")
        if track_id:
            recent_track_ids.add(track_id)

        for artist_name in _track_artist_names(track):
            recent_artist_counts[artist_name] = recent_artist_counts.get(artist_name, 0) + 1

    return {"track_ids": recent_track_ids, "artist_counts": recent_artist_counts}


def _build_dj_search_queries(current: dict, recent: dict, mode: str) -> list[tuple[str, int]]:
    """Construye queries DJ con peso: mayor peso significa mayor confianza."""
    primary_artist = current["primary_artist"]
    current_name = current["name"]
    recent_artists = sorted(
        recent["artist_counts"].items(),
        key=lambda item: item[1],
        reverse=True,
    )

    weighted_queries = [
        (primary_artist, 50),
        (f"{primary_artist} {current_name}", 45),
    ]

    for artist in current["artists"][1:3]:
        weighted_queries.append((artist, 35))

    for artist, count in recent_artists[:4]:
        if artist != primary_artist:
            weighted_queries.append((artist, 30 + min(count * 5, 20)))

    if mode == "popular":
        weighted_queries.extend([
            (f"{primary_artist} popular", 40),
            (f"{primary_artist} hits", 38),
        ])
    elif mode == "discover":
        weighted_queries.extend([
            (f"{primary_artist} radio", 34),
            (f"{primary_artist} similar", 34),
        ])
        for artist, _count in recent_artists[4:8]:
            weighted_queries.append((artist, 28))
    else:
        weighted_queries.extend([
            (f"{primary_artist} similar", 36),
            (f"{primary_artist} radio", 32),
        ])

    seen_queries = set()
    unique_queries = []
    for query, weight in weighted_queries:
        normalized_query = query.lower().strip()
        if normalized_query and normalized_query not in seen_queries:
            seen_queries.add(normalized_query)
            unique_queries.append((query, weight))

    return unique_queries[:10]


def _score_dj_candidate(track: dict, current: dict, recent: dict, query_weight: int, mode: str) -> int:
    """Puntua un candidato DJ usando similitud, historial y popularidad."""
    track_id = track.get("id")
    if not track_id or not track.get("uri"):
        return -1000
    if track_id == current.get("id"):
        return -1000
    if track_id in recent["track_ids"]:
        return -400

    artist_names = _track_artist_names(track)
    if not artist_names:
        return -1000

    current_artists = set(current["artists"])
    recent_artist_counts = recent["artist_counts"]
    popularity = int(track.get("popularity") or 0)
    score = query_weight + min(popularity, 100) // 3

    shared_current_artists = current_artists.intersection(artist_names)
    if shared_current_artists:
        score += 45

    recent_overlap = sum(recent_artist_counts.get(artist, 0) for artist in artist_names)
    if recent_overlap:
        score += min(35, recent_overlap * 8)

    if mode == "popular":
        score += popularity // 2
        if popularity < 45:
            score -= 25
    elif mode == "discover":
        if shared_current_artists:
            score -= 25
        if recent_overlap:
            score -= min(30, recent_overlap * 6)
        if 35 <= popularity <= 80:
            score += 25
        elif popularity > 90:
            score -= 10
    else:
        if popularity < 25:
            score -= 15

    return score


def _collect_dj_candidates(sp, current: dict, recent: dict, mode: str) -> list[tuple[int, dict]]:
    """Busca y puntua candidatos para el DJ."""
    candidates_by_id = {}

    for query, query_weight in _build_dj_search_queries(current, recent, mode):
        results = sp.search(q=query, type="track", limit=8, market="MX")
        for track in results.get("tracks", {}).get("items", []):
            track_id = track.get("id")
            if not track_id:
                continue

            score = _score_dj_candidate(track, current, recent, query_weight, mode)
            previous = candidates_by_id.get(track_id)
            if previous is None or score > previous[0]:
                candidates_by_id[track_id] = (score, track)

    candidates = [candidate for candidate in candidates_by_id.values() if candidate[0] > 0]
    return sorted(candidates, key=lambda item: item[0], reverse=True)


def _format_dj_track(track: dict, score: int) -> str:
    """Formatea un track agregado por el DJ."""
    name = track.get("name", "Unknown track")
    artists = ", ".join(_track_artist_names(track)) or "Artista no disponible"
    album = track.get("album", {}).get("name", "Album no disponible")
    url = track.get("external_urls", {}).get("spotify", "No URL")

    return (
        f"- {name} - {artists}\n"
        f"  Album: {album}\n"
        f"  Score DJ: {score}\n"
        f"  Link: {url}"
    )


@tool
def spotify_dj_queue_similar_to_current(queue_count: int, mode: str, confirm: str) -> str:
    """Queues DJ-style recommendations based on current playback and recent history.

    Use this tool when the user asks to:
    - enable DJ mode
    - queue music similar to what is currently playing
    - surprise them with related songs
    - add several recommended songs to the queue

    Important usage rules:
    - This tool modifies playback queue.
    - The user must provide confirmation with the exact value 'SI_DJ'.
    - If confirm is not exactly 'SI_DJ', nothing will be added.
    - queue_count should normally be 3, and must be between 1 and 5.
    - mode must be 'similar', 'popular' or 'discover'. Use 'similar' by default.
    - After calling this tool, pass the returned text directly to final_answer.

    Args:
        queue_count: Number of songs to add to the queue. Default should be 3.
        mode: Recommendation mode: 'similar', 'popular' or 'discover'.
        confirm: Safety confirmation. Must be exactly 'SI_DJ' to add songs.
    """
    if confirm != "SI_DJ":
        return "No active el modo DJ. Para confirmar, usa confirm='SI_DJ'."

    logger.info("spotify_dj_queue_similar_to_current llamada: queue_count=%s, mode=%r", queue_count, mode)

    try:
        sp = get_spotify_client()
        queue_count = max(1, min(int(queue_count), 5))
        mode = mode.lower().strip()

        if mode not in ["similar", "popular", "discover"]:
            mode = "similar"

        current = _get_current_track_context(sp)
        if current is None:
            return (
                "No puedo activar el DJ porque no hay una cancion activa. "
                "Reproduce una cancion en Spotify e intentalo de nuevo."
            )

        recent = _get_recent_track_context(sp)
        candidates = _collect_dj_candidates(sp, current, recent, mode)

        if not candidates:
            return (
                "No encontre suficientes canciones buenas para agregar a la cola. "
                "Prueba cuando tengas una cancion activa distinta o mas historial reciente."
            )

        selected = candidates[:queue_count]
        for _score, track in selected:
            sp.add_to_queue(track["uri"])

        output = [
            "Modo DJ activo.",
            f"Modo: {mode}",
            f"Base: {current['name']} - {', '.join(current['artists'])}",
            f"Canciones agregadas a la cola: {len(selected)}",
            "",
            "Seleccion DJ:",
        ]
        output.extend(_format_dj_track(track, score) for score, track in selected)

        if len(selected) < queue_count:
            output.extend([
                "",
                f"Solo agregue {len(selected)} de {queue_count} canciones porque filtre duplicados o canciones recientes.",
            ])

        return "\n".join(output)

    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_dj_queue_similar_to_current: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_dj_queue_similar_to_current: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_dj_queue_similar_to_current: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al activar el modo DJ: {error}"


@tool
def spotify_list_user_playlists(limit: int) -> str:
    """Lists the current user's Spotify playlists.

    Use this tool when the user asks to:
    - list their Spotify playlists
    - see existing playlists before adding songs
    - find playlist names, IDs, owners, visibility or Spotify links

    Important usage rules:
    - This tool only reads playlist data. It does not modify Spotify.
    - This tool returns a formatted string, not a list or dictionary.
    - Do not iterate over the returned result.
    - After calling this tool, pass the returned text directly to final_answer.
    - Correct usage example:
      result = spotify_list_user_playlists(limit=20)
      final_answer(result)

    Args:
        limit: Number of playlists to retrieve. Use an integer from 1 to 50. If the user does not specify a number, use 20.
    """
    logger.info("spotify_list_user_playlists llamada: limit=%s", limit)

    try:
        sp = get_spotify_client()
        limit = max(1, min(limit, 50))

        results = sp.current_user_playlists(limit=limit)
        playlists = results.get("items", [])

        if not playlists:
            return "No encontre playlists en tu cuenta de Spotify."

        output = [f"Playlists encontradas: {len(playlists)}\n"]

        for index, playlist in enumerate(playlists, start=1):
            name = playlist.get("name", "Playlist sin nombre")
            playlist_id = playlist.get("id", "No disponible")
            owner = playlist.get("owner", {}).get("display_name") or playlist.get("owner", {}).get("id", "No disponible")
            tracks_total = playlist.get("tracks", {}).get("total", "N/A")
            is_public = playlist.get("public")
            collaborative = playlist.get("collaborative", False)
            url = playlist.get("external_urls", {}).get("spotify", "No URL")

            if is_public is True:
                visibility = "Publica"
            elif is_public is False:
                visibility = "Privada"
            else:
                visibility = "No disponible"

            output.append(
                f"[{index}] {name}\n"
                f"ID: {playlist_id}\n"
                f"Owner: {owner}\n"
                f"Visibilidad: {visibility}\n"
                f"Colaborativa: {'Si' if collaborative else 'No'}\n"
                f"Tracks: {tracks_total}\n"
                f"Spotify: {url}"
            )

        return "\n\n".join(output)

    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_list_user_playlists: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_list_user_playlists: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_list_user_playlists: %s", error, exc_info=True)
        return f"Ocurrio un error inesperado al listar tus playlists: {error}"


@tool
def spotify_search_songs(query: str, limit: int) -> str:
    """Searches Spotify ONLY for songs (tracks) using the Spotify Web API.

    Use this tool when the user asks to:
    - search songs by artist name (e.g. "3 canciones de Bad Bunny")
    - search songs by song title
    - find tracks related to a music query
    - get song names, albums, popularity or Spotify links for songs

    Do NOT use this tool when the user asks about an artist's profile,
    genres, or artist popularity — use spotify_search_artists instead.

    Important usage rules:
    - This tool already returns a complete formatted text report.
    - This tool returns a string, not a list and not a dictionary.
    - Do not iterate over the result using a for loop.
    - Do not try to access result['title'], result['album'] or result['link'].
    - Do not use web_search, google_search, browser_search or any other search function.
    - After calling this tool, pass the returned text directly to final_answer.
    - Correct usage example:
      result = spotify_search_songs(query="21 Savage", limit=5)
      final_answer(result)

    Args:
        query: The Spotify search query. It can be an artist, song, album or keyword. Examples: '21 Savage', 'Bad Bunny', 'Linkin Park Numb', 'corridos tumbados'.
        limit: Maximum number of songs to return. Use an integer from 1 to 10. If the user asks for 3 songs, use 3.
    """
    logger.info("spotify_search_songs llamada: query=%r, limit=%s", query, limit)

    try:
        sp = get_spotify_client()
        limit = max(1, min(limit, 10))

        results = sp.search(
            q=query,
            type="track",
            limit=limit,
            market="MX",
        )

        tracks = results.get("tracks", {}).get("items", [])

        if not tracks:
            return f"No encontré canciones en Spotify para: {query}"

        output = [f"Canciones encontradas para: {query}\n"]
        for index, track in enumerate(tracks, start=1):
            output.append(f"\n[{index}]\n{format_track(track)}")

        return "\n".join(output)

    except RuntimeError as error:
        logger.error("Error de configuración en spotify_search_songs: %s", error)
        return f"Error de configuración: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_search_songs: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_search_songs: %s", error, exc_info=True)
        return f"Ocurrió un error inesperado al buscar canciones en Spotify: {error}"


@tool
def spotify_search_artists(query: str, limit: int) -> str:
    """Searches Spotify ONLY for artists using the Spotify Web API.

    Use this tool when the user asks to:
    - search for an artist's profile
    - get an artist's genres or popularity
    - get an artist's Spotify link
    - find artists related to a name or genre keyword

    Do NOT use this tool when the user asks for songs or tracks —
    use spotify_search_songs instead.

    Important usage rules:
    - This tool already returns a complete formatted text report.
    - This tool returns a string, not a list and not a dictionary.
    - Do not iterate over the result using a for loop.
    - Do not try to access result['artist'] or result['genres'].
    - Do not use web_search, google_search, browser_search or any other search function.
    - After calling this tool, pass the returned text directly to final_answer.
    - Correct usage example:
      result = spotify_search_artists(query="21 Savage", limit=5)
      final_answer(result)

    Args:
        query: The Spotify search query. It can be an artist name or genre keyword. Examples: '21 Savage', 'Bad Bunny', 'corridos tumbados'.
        limit: Maximum number of artists to return. Use an integer from 1 to 10. If the user asks for 3 artists, use 3.
    """
    logger.info("spotify_search_artists llamada: query=%r, limit=%s", query, limit)

    try:
        sp = get_spotify_client()
        limit = max(1, min(limit, 10))

        results = sp.search(
            q=query,
            type="artist",
            limit=limit,
            market="MX",
        )

        artists = results.get("artists", {}).get("items", [])

        if not artists:
            return f"No encontré artistas en Spotify para: {query}"

        output = [f"Artistas encontrados para: {query}\n"]
        for index, artist in enumerate(artists, start=1):
            name = artist.get("name", "Unknown artist")
            genres = ", ".join(artist.get("genres", [])) or "Sin géneros disponibles"
            popularity = artist.get("popularity", "N/A")
            url = artist.get("external_urls", {}).get("spotify", "No URL")

            output.append(
                f"\n[{index}]\n"
                f"Artista: {name}\n"
                f"Géneros: {genres}\n"
                f"Popularidad: {popularity}\n"
                f"Spotify: {url}"
            )

        return "\n".join(output)

    except RuntimeError as error:
        logger.error("Error de configuración en spotify_search_artists: %s", error)
        return f"Error de configuración: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_search_artists: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_search_artists: %s", error, exc_info=True)
        return f"Ocurrió un error inesperado al buscar artistas en Spotify: {error}"


@tool
def spotify_recently_played(limit: int) -> str:
    """Gets the current user's recently played songs from Spotify and summarizes them.

    Use this tool when the user asks to:
    - analyze recently played songs
    - see listening history
    - know what artists they have listened to recently
    - identify repeated artists or albums
    - summarize recent Spotify activity

    Important usage rules:
    - This tool requires the user to authorize Spotify access.
    - This tool returns a complete formatted text report.
    - This tool returns a string, not a list and not a dictionary.
    - Do not iterate over the returned result.
    - Do not try to access result['track'], result['artist'] or result['album'].
    - Do not invent listening data.
    - Only use the data returned by this tool.
    - After calling this tool, pass the returned text directly to final_answer.
    - Correct usage example:
      result = spotify_recently_played(limit=20)
      final_answer(result)

    Args:
        limit: Number of recently played tracks to retrieve. Use an integer from 1 to 50. If the user asks for recent songs without specifying a number, use 20.
    """
    logger.info("spotify_recently_played llamada: limit=%s", limit)

    try:
        sp = get_spotify_client()
        limit = max(1, min(limit, 50))

        results = sp.current_user_recently_played(limit=limit)
        items = results.get("items", [])

        if not items:
            return "No se encontraron canciones reproducidas recientemente."

        output = [f"Últimas {len(items)} canciones reproducidas:\n"]

        artist_counter = {}
        album_counter = {}

        for index, item in enumerate(items, start=1):
            track = item.get("track", {})
            played_at = item.get("played_at", "Fecha no disponible")

            name = track.get("name", "Unknown track")
            artists = [artist["name"] for artist in track.get("artists", [])]
            artists_text = ", ".join(artists)
            album = track.get("album", {}).get("name", "Unknown album")
            url = track.get("external_urls", {}).get("spotify", "No URL")

            for artist in artists:
                artist_counter[artist] = artist_counter.get(artist, 0) + 1

            album_counter[album] = album_counter.get(album, 0) + 1

            output.append(
                f"{index}. {name} — {artists_text}\n"
                f"   Álbum: {album}\n"
                f"   Reproducida: {played_at}\n"
                f"   Link: {url}"
            )

        top_artists = sorted(
            artist_counter.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        top_albums = sorted(
            album_counter.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        output.append("\nARTISTAS MÁS REPETIDOS:")
        for artist, count in top_artists:
            output.append(f"- {artist}: {count} aparición(es)")

        output.append("\nÁLBUMES MÁS REPETIDOS:")
        for album, count in top_albums:
            output.append(f"- {album}: {count} aparición(es)")

        return "\n".join(output)

    except RuntimeError as error:
        logger.error("Error de configuración en spotify_recently_played: %s", error)
        return f"Error de configuración: {error}"
    except SpotifyException as error:
        logger.error("SpotifyException en spotify_recently_played: %s", error, exc_info=True)
        return _handle_spotify_error(error)
    except Exception as error:
        logger.error("Error inesperado en spotify_recently_played: %s", error, exc_info=True)
        return f"Ocurrió un error inesperado al leer tu historial de Spotify: {error}"


def _chunks(items: list[str], size: int) -> list[list[str]]:
    """Divide una lista en bloques de tamano fijo."""
    return [items[index:index + size] for index in range(0, len(items), size)]


def _split_search_queries(search_queries: str) -> list[str]:
    """Normaliza busquedas separadas por punto y coma."""
    return [query.strip() for query in search_queries.split(";") if query.strip()]


def _format_added_track(track: dict) -> str:
    """Formatea una cancion agregada a playlist."""
    name = track.get("name", "Unknown track")
    artists = ", ".join(artist["name"] for artist in track.get("artists", []))
    album = track.get("album", {}).get("name", "Unknown album")
    url = track.get("external_urls", {}).get("spotify", "No URL")

    return (
        f"- {name} - {artists}\n"
        f"  Album: {album}\n"
        f"  Link: {url}"
    )

def _search_tracks_for_queries(sp, search_queries: str, tracks_per_query: int) -> tuple[list[str], list[str], list[str]]:
    """Busca tracks por query y devuelve URIs, descripciones y queries sin resultado."""
    tracks_per_query = max(1, min(tracks_per_query, 5))
    queries = _split_search_queries(search_queries)
    added_uris = []
    added_descriptions = []
    missing_queries = []
    seen_uris = set()

    for query in queries:
        results = sp.search(
            q=query,
            type="track",
            limit=tracks_per_query,
            market="MX",
        )
        tracks = results.get("tracks", {}).get("items", [])

        if not tracks:
            missing_queries.append(query)
            continue

        for track in tracks:
            uri = track.get("uri")
            if not uri or uri in seen_uris:
                continue

            seen_uris.add(uri)
            added_uris.append(uri)
            added_descriptions.append(_format_added_track(track))

    return added_uris, added_descriptions, missing_queries


@tool
def spotify_add_tracks_to_playlist_from_search(
    playlist_id: str,
    search_queries: str,
    tracks_per_query: int,
    confirm: str,
) -> str:
    """Adds Spotify tracks from search queries to an existing playlist.

    Use this tool only when the user explicitly asks to add songs to an existing playlist.

    Important usage rules:
    - This tool modifies an existing Spotify playlist.
    - Do not use this tool unless the user clearly asks to add songs.
    - The user must provide a playlist ID, usually obtained from spotify_list_user_playlists.
    - The user must provide confirmation with the exact value 'SI_AGREGAR'.
    - If confirm is not exactly 'SI_AGREGAR', no songs will be added.
    - search_queries must be a single string with searches separated by semicolons.
    - tracks_per_query must be an integer from 1 to 5.
    - This tool returns a formatted string with added songs.
    - Do not iterate over the returned result.
    - After calling this tool, pass the returned text directly to final_answer.
    - Correct usage example:
      result = spotify_add_tracks_to_playlist_from_search(
          playlist_id="37i9dQZF1DX0XUsuxWHRQd",
          search_queries="Travis Scott; 21 Savage",
          tracks_per_query=2,
          confirm="SI_AGREGAR"
      )
      final_answer(result)

    Args:
        playlist_id: Spotify playlist ID where songs will be added.
        search_queries: Multiple Spotify search queries separated by semicolons.
        tracks_per_query: Number of songs to add from each search query. Use an integer from 1 to 5.
        confirm: Safety confirmation. Must be exactly 'SI_AGREGAR' to add songs.
    """
    if confirm != "SI_AGREGAR":
        logger.warning(
            "Intento de agregar canciones a playlist '%s' sin confirmacion valida (confirm=%r)",
            playlist_id,
            confirm,
        )
        return (
            "No se agrego ninguna cancion. "
            "Para confirmar, usa confirm='SI_AGREGAR'."
        )

    logger.info(
        "Agregando canciones a playlist '%s' (tracks_per_query=%s)",
        playlist_id,
        tracks_per_query,
    )

    try:
        sp = get_spotify_client()
        playlist_id = playlist_id.strip()

        if not playlist_id:
            return "Debes proporcionar un playlist_id valido."

        if not _split_search_queries(search_queries):
            return "No se recibieron busquedas validas para agregar canciones."

        playlist = sp.playlist(playlist_id, fields="id,name,external_urls")
        playlist_name = playlist.get("name", "Playlist sin nombre")
        playlist_url = playlist.get("external_urls", {}).get("spotify", "No URL")

        added_uris, added_descriptions, missing_queries = _search_tracks_for_queries(
            sp=sp,
            search_queries=search_queries,
            tracks_per_query=tracks_per_query,
        )

        if not added_uris:
            return "No se encontraron canciones para agregar a la playlist."

        for uri_chunk in _chunks(added_uris, 100):
            sp.playlist_add_items(
                playlist_id=playlist_id,
                items=uri_chunk,
            )

        output = [
            f"Canciones agregadas correctamente a: {playlist_name}",
            f"Playlist: {playlist_url}",
            f"Canciones agregadas: {len(added_uris)}",
            "",
            "Detalle:",
            chr(10).join(added_descriptions),
        ]

        if missing_queries:
            output.extend([
                "",
                "Busquedas sin resultado:",
                chr(10).join(f"- {query}" for query in missing_queries),
            ])

        return chr(10).join(output)

    except RuntimeError as error:
        logger.error("Error de configuracion en spotify_add_tracks_to_playlist_from_search: %s", error)
        return f"Error de configuracion: {error}"
    except SpotifyException as error:
        logger.error(
            "SpotifyException en spotify_add_tracks_to_playlist_from_search: %s",
            error,
            exc_info=True,
        )
        return (
            "No se pudieron agregar canciones a la playlist. Detalle: "
            + _handle_spotify_error(error)
        )
    except Exception as error:
        logger.error(
            "Error inesperado en spotify_add_tracks_to_playlist_from_search: %s",
            error,
            exc_info=True,
        )
        return f"Ocurrio un error inesperado al agregar canciones: {error}"


@tool
def spotify_create_playlist_from_search(
    playlist_name: str,
    search_queries: str,
    tracks_per_query: int,
    visibility: str,
    confirm: str,
) -> str:
    """Creates a Spotify playlist from multiple Spotify search queries.

    Use this tool only when the user explicitly asks to create a Spotify playlist.

    This tool can:
    - create a new playlist in the user's Spotify account
    - search songs from artists, genres or keywords
    - add matching songs to the new playlist

    Important usage rules:
    - This tool modifies the user's Spotify account by creating a playlist.
    - Do not use this tool unless the user clearly asks to create a playlist.
    - The user must provide confirmation with the exact value 'SI_CREAR'.
    - If confirm is not exactly 'SI_CREAR', the playlist will not be created.
    - search_queries must be a single string with searches separated by semicolons.
    - Correct search_queries example: '21 Savage; Drake; Metro Boomin; Travis Scott'
    - visibility must be either 'private' or 'public'.
    - tracks_per_query must be an integer from 1 to 5.
    - This tool returns a formatted string with the playlist link and added songs.
    - Do not iterate over the returned result.
    - Do not try to access result['playlist'] or result['tracks'].
    - After calling this tool, pass the returned text directly to final_answer.
    - Correct usage example:
      result = spotify_create_playlist_from_search(
          playlist_name="Rap para entrenar",
          search_queries="21 Savage; Drake; Metro Boomin",
          tracks_per_query=2,
          visibility="private",
          confirm="SI_CREAR"
      )
      final_answer(result)

    Args:
        playlist_name: Name of the Spotify playlist to create.
        search_queries: Multiple Spotify search queries separated by semicolons. Example: '21 Savage; Drake; Metro Boomin'.
        tracks_per_query: Number of songs to add from each search query. Use an integer from 1 to 5.
        visibility: Playlist visibility. Use exactly 'private' or 'public'.
        confirm: Safety confirmation. Must be exactly 'SI_CREAR' to create the playlist.
    """
    if confirm != "SI_CREAR":
        logger.warning(
            "Intento de crear playlist '%s' sin confirmación válida (confirm=%r)",
            playlist_name,
            confirm,
        )
        return (
            "No se creó ninguna playlist. "
            "Para confirmar la creación, usa confirm='SI_CREAR'."
        )

    logger.info(
        "Creando playlist '%s' (visibility=%s, tracks_per_query=%s)",
        playlist_name,
        visibility,
        tracks_per_query,
    )

    try:
        sp = get_spotify_client()
        tracks_per_query = max(1, min(tracks_per_query, 5))
        visibility = visibility.lower().strip()

        if visibility not in ["private", "public"]:
            return "La visibilidad debe ser exactamente 'private' o 'public'."

        is_public = visibility == "public"

        queries: List[str] = [
            query.strip()
            for query in search_queries.split(";")
            if query.strip()
        ]

        if not queries:
            return "No se recibieron búsquedas válidas para crear la playlist."

        playlist = sp.current_user_playlist_create(
            name=playlist_name,
            public=is_public,
            description="Playlist creada con un agente local usando smolagents y Spotify API.",
        )

        playlist_id = playlist["id"]
        playlist_url = playlist.get("external_urls", {}).get("spotify", "No URL")

        added_uris = []
        added_descriptions = []
        seen_uris = set()

        for query in queries:
            results = sp.search(
                q=query,
                type="track",
                limit=tracks_per_query,
                market="MX",
            )

            tracks = results.get("tracks", {}).get("items", [])

            for track in tracks:
                uri = track.get("uri")

                if not uri or uri in seen_uris:
                    continue

                seen_uris.add(uri)
                added_uris.append(uri)

                name = track.get("name", "Unknown track")
                artists = ", ".join(
                    artist["name"]
                    for artist in track.get("artists", [])
                )

                album = track.get("album", {}).get("name", "Unknown album")
                url = track.get("external_urls", {}).get("spotify", "No URL")

                added_descriptions.append(
                    f"- {name} — {artists}\n"
                    f"  Álbum: {album}\n"
                    f"  Link: {url}"
                )

        if not added_uris:
            return (
                f"Se creó la playlist '{playlist_name}', "
                "pero no se encontraron canciones para agregar."
            )

        for uri_chunk in _chunks(added_uris, 100):
            sp.playlist_add_items(
                playlist_id=playlist_id,
                items=uri_chunk,
            )

        return (
            f"Playlist creada correctamente: {playlist_name}\n"
            f"Visibilidad: {'Pública' if is_public else 'Privada'}\n"
            f"Canciones agregadas: {len(added_uris)}\n"
            f"Link: {playlist_url}\n\n"
            f"Canciones agregadas:\n" + "\n".join(added_descriptions)
        )

    except RuntimeError as error:
        logger.error("Error de configuración en spotify_create_playlist_from_search: %s", error)
        return f"Error de configuración: {error}"
    except SpotifyException as error:
        logger.error(
            "SpotifyException en spotify_create_playlist_from_search: %s",
            error,
            exc_info=True,
        )
        return (
            "La playlist pudo haberse creado parcialmente antes del error. "
            "Revisa tu cuenta de Spotify. Detalle: " + _handle_spotify_error(error)
        )
    except Exception as error:
        logger.error(
            "Error inesperado en spotify_create_playlist_from_search: %s",
            error,
            exc_info=True,
        )
        return f"Ocurrió un error inesperado al crear la playlist: {error}"
