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

from typing import List

from smolagents import tool
from spotipy.exceptions import SpotifyException

from spotify_client import get_spotify_client


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
            "Spotify rechazó la solicitud por falta de permisos. "
            "Verifica que tu cuenta tenga los scopes necesarios autorizados."
        )
    if status == 429:
        return (
            "Spotify está limitando las solicitudes por exceso de peticiones "
            "(rate limit). Espera unos segundos e inténtalo de nuevo."
        )

    return f"Spotify devolvió un error (código {status}): {error.msg}"


@tool
def spotify_search(query: str, limit: int) -> str:
    """Searches Spotify for songs and artists using the Spotify Web API.

    Use this tool when the user asks to:
    - search songs by artist name
    - search songs by song title
    - search artists
    - get album, artist and Spotify links
    - find tracks related to a music query

    Important usage rules:
    - This tool already returns a complete formatted text report.
    - This tool returns a string, not a list and not a dictionary.
    - Do not iterate over the result using a for loop.
    - Do not try to access result['title'], result['album'], result['artist'] or result['link'].
    - Do not use web_search, google_search, browser_search or any other search function.
    - After calling this tool, pass the returned text directly to final_answer.
    - Correct usage example:
      result = spotify_search(query="21 Savage", limit=5)
      final_answer(result)

    Args:
        query: The Spotify search query. It can be an artist, song, album or keyword. Examples: '21 Savage', 'Bad Bunny', 'Linkin Park Numb', 'corridos tumbados'.
        limit: Maximum number of results to return. Use an integer from 1 to 10. If the user asks for 5 songs, use 5.
    """
    try:
        sp = get_spotify_client()
        limit = max(1, min(limit, 10))

        results = sp.search(
            q=query,
            type="track,artist",
            limit=limit,
            market="MX",
        )

        tracks = results.get("tracks", {}).get("items", [])
        artists = results.get("artists", {}).get("items", [])

        output = [f"Resultados de Spotify para: {query}\n"]

        if tracks:
            output.append("CANCIONES ENCONTRADAS:")
            for index, track in enumerate(tracks, start=1):
                output.append(f"\n[{index}]\n{format_track(track)}")

        if artists:
            output.append("\nARTISTAS ENCONTRADOS:")
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

        if not tracks and not artists:
            return f"No encontré resultados en Spotify para: {query}"

        return "\n".join(output)

    except RuntimeError as error:
        return f"Error de configuración: {error}"
    except SpotifyException as error:
        return _handle_spotify_error(error)
    except Exception as error:
        return f"Ocurrió un error inesperado al buscar en Spotify: {error}"


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
        return f"Error de configuración: {error}"
    except SpotifyException as error:
        return _handle_spotify_error(error)
    except Exception as error:
        return f"Ocurrió un error inesperado al leer tu historial de Spotify: {error}"


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
        return (
            "No se creó ninguna playlist. "
            "Para confirmar la creación, usa confirm='SI_CREAR'."
        )

    try:
        sp = get_spotify_client()
        user = sp.current_user()
        user_id = user["id"]

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

        playlist = sp.user_playlist_create(
            user=user_id,
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

        sp.playlist_add_items(
            playlist_id=playlist_id,
            items=added_uris,
        )

        return (
            f"Playlist creada correctamente: {playlist_name}\n"
            f"Visibilidad: {'Pública' if is_public else 'Privada'}\n"
            f"Canciones agregadas: {len(added_uris)}\n"
            f"Link: {playlist_url}\n\n"
            f"Canciones agregadas:\n" + "\n".join(added_descriptions)
        )

    except RuntimeError as error:
        return f"Error de configuración: {error}"
    except SpotifyException as error:
        return (
            "La playlist pudo haberse creado parcialmente antes del error. "
            "Revisa tu cuenta de Spotify. Detalle: " + _handle_spotify_error(error)
        )
    except Exception as error:
        return f"Ocurrió un error inesperado al crear la playlist: {error}"