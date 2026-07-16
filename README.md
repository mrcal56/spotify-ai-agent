# Spotify AI Agent

Agente local de terminal para interactuar con Spotify usando lenguaje natural.

El proyecto combina:

- `smolagents` para construir el agente.
- `LiteLLM` para conectar el agente con un modelo local en Ollama.
- `spotipy` para hablar con la Web API de Spotify.
- `python-dotenv` para cargar credenciales desde `.env`.

## Requisitos

- Python 3.10 o superior.
- Una cuenta de Spotify.
- Una app creada en el Spotify Developer Dashboard.
- Ollama instalado y corriendo localmente.
- El modelo `qwen2.5-coder:7b` disponible en Ollama.

Para descargar el modelo usado por defecto:

```bash
ollama pull qwen2.5-coder:7b
```

Para verificar que Ollama esta corriendo:

```bash
ollama list
```

## Instalacion

Crear y activar un entorno virtual:

```bash
python -m venv env
```

En Windows PowerShell:

```powershell
.\env\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Configuracion de Spotify

1. Entra a `https://developer.spotify.com/dashboard`.
2. Crea una app nueva.
3. Copia el Client ID y Client Secret.
4. Configura el Redirect URI exactamente como lo usaras en `.env`.

Ejemplo recomendado para desarrollo local:

```text
http://127.0.0.1:8888/callback
```

Copia la plantilla de variables:

```bash
copy .env.example .env
```

Edita `.env` con tus valores reales:

```env
SPOTIPY_CLIENT_ID=tu_client_id_aqui
SPOTIPY_CLIENT_SECRET=tu_client_secret_aqui
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

El archivo `.env` no debe subirse a Git.

## Uso

Ejecuta el agente:

```bash
python main.py
```

Luego escribe instrucciones en la terminal, por ejemplo:

```text
revisa mi login de Spotify
```

```text
busca 5 canciones de Bad Bunny
```

```text
lista mis playlists
```

```text
muestrame mis ultimas 20 canciones escuchadas
```

Para salir:

```text
salir
```

## Acciones Sobre Playlists

El agente puede crear playlists o agregar canciones, pero esas acciones modifican tu cuenta de Spotify.

Por seguridad, las tools internas requieren confirmaciones explicitas:

- Crear playlist: `SI_CREAR`
- Agregar canciones a playlist existente: `SI_AGREGAR`

Si el agente no tiene una confirmacion clara, no deberia ejecutar acciones destructivas o de escritura.

## Archivos Principales

- `main.py`: punto de entrada del CLI interactivo.
- `agent.py`: configura el modelo local y el agente de `smolagents`.
- `tools.py`: contiene las tools que consultan o modifican Spotify.
- `spotify_client.py`: crea y reutiliza el cliente autenticado de Spotify.
- `prompts.py`: construye las reglas que se envian al agente junto con cada tarea.
- `logging_config.py`: configura logs en consola y en `agent.log`.
- `requirements.txt`: dependencias del proyecto.
- `.env.example`: plantilla de configuracion local.

## Archivos Locales Ignorados

Estos archivos pueden existir en tu maquina, pero no deben versionarse:

- `.env`: credenciales reales de Spotify.
- `.spotify_cache`: token OAuth cacheado por Spotipy.
- `env/`: entorno virtual.
- `__pycache__/`: cache de Python.
- `agent.log`: logs de ejecucion.

## Logs

La aplicacion escribe logs en:

```text
agent.log
```

Ese archivo sirve para revisar errores con mas detalle si algo falla durante el uso del agente.
