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

# Caché a nivel de módulo: guarda la única instancia de spotipy.Spotify
# ya creada, para no reconstruirla en cada llamada a get_spotify_client().
# Empieza en None porque todavía no se ha creado ningún cliente.
_cached_client: spotipy.Spotify | None = None


def _build_spotify_client() -> spotipy.Spotify:
    """Construye una instancia nueva de spotipy.Spotify desde cero.

    Esta función hace el trabajo "caro": leer variables de entorno,
    validar que existan, y montar el auth_manager con el token cacheado
    en disco (.spotify_cache). Solo debe llamarse una vez por proceso;
    get_spotify_client() es quien decide cuándo llamarla.

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


def get_spotify_client() -> spotipy.Spotify:
    """Devuelve un cliente autenticado de Spotify, reutilizando el mismo.

    La primera vez que se llama, construye el cliente y lo guarda en
    _cached_client. Las siguientes llamadas devuelven ese mismo objeto
    en vez de crear uno nuevo — evita releer el .env y el .spotify_cache
    en cada tool call.

    El refresco automático del access token (que expira cada ~1 hora)
    NO se ve afectado por este caché: spotipy lo maneja internamente
    dentro del propio auth_manager en cada petición HTTP, sin importar
    si el objeto Spotify es nuevo o reutilizado.

    Returns:
        Una instancia de spotipy.Spotify lista para hacer llamadas
        a la Web API de Spotify (búsquedas, historial, playlists, etc.).

    Raises:
        RuntimeError: si falta alguna variable de entorno requerida.
    """
    global _cached_client

    if _cached_client is None:
        _cached_client = _build_spotify_client()

    return _cached_client