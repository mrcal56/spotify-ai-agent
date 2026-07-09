"""
Módulo encargado de la conexión con la API de Spotify.

Responsabilidad única de este archivo: crear un cliente de Spotify
autenticado (spotipy.Spotify) usando las credenciales del archivo .env.

No contiene lógica de negocio (búsquedas, playlists, etc.) — eso vive
en tools.py. Este archivo solo resuelve "¿cómo me conecto a Spotify?".
"""

import os

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


# Carga las variables definidas en tu archivo .env (SPOTIPY_CLIENT_ID, etc.)
# hacia las variables de entorno del proceso, para que os.getenv() las encuentre.
load_dotenv()

# Permisos (scopes) que el agente necesita pedirle al usuario en Spotify:
# - user-read-recently-played: para leer el historial de reproducción.
# - playlist-modify-private / playlist-modify-public: para crear y llenar playlists.
SPOTIFY_SCOPES = (
    "user-read-recently-played "
    "playlist-modify-private "
    "playlist-modify-public"
)


def get_spotify_client() -> spotipy.Spotify:
    """Crea y devuelve un cliente autenticado de Spotify.

    Verifica primero que las variables de entorno necesarias existan;
    si falta alguna, lanza un error claro en vez de dejar que spotipy
    falle más adelante con un mensaje confuso.

    Returns:
        Una instancia de spotipy.Spotify lista para hacer llamadas
        a la Web API de Spotify (búsquedas, historial, playlists, etc.).

    Raises:
        RuntimeError: si falta alguna variable de entorno requerida.
    """
    required_vars = [
        "SPOTIPY_CLIENT_ID",
        "SPOTIPY_CLIENT_SECRET",
        "SPOTIPY_REDIRECT_URI",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        raise RuntimeError(
            "Faltan variables de entorno en tu archivo .env: "
            + ", ".join(missing)
        )

    auth_manager = SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=SPOTIFY_SCOPES,
        cache_path=".spotify_cache",
        open_browser=True,
    )

    return spotipy.Spotify(auth_manager=auth_manager)