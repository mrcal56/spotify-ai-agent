# Project Context

## Resumen

Este proyecto es un agente local de terminal para interactuar con Spotify usando lenguaje natural.

El agente puede consultar datos de Spotify, crear/modificar playlists y controlar reproduccion activa en dispositivos Spotify disponibles.

## Stack

- Python 3.10+
- `smolagents` como framework de agente
- `LiteLLM` para conectar el agente con Ollama
- Ollama como runtime local del modelo
- Modelo actual: `llama3.2:3b`
- `spotipy` para Spotify Web API
- `python-dotenv` para cargar credenciales desde `.env`

## Archivos Principales

- `main.py`: CLI interactivo, router rapido para comandos simples y fallback al agente.
- `agent.py`: configura el modelo, registra tools y crea el `CodeAgent`.
- `tools.py`: contiene todas las tools de Spotify usadas por el agente.
- `spotify_client.py`: configura OAuth, scopes y cliente autenticado de Spotify.
- `prompts.py`: reglas que envuelven cada instruccion del usuario.
- `logging_config.py`: logging a consola y archivo `agent.log`.
- `requirements.txt`: dependencias del proyecto.
- `.env.example`: plantilla de credenciales Spotify.
- `README.md`: guia de instalacion y uso.

## Configuracion Local

Archivos locales esperados, no versionados:

- `.env`: credenciales reales de Spotify.
- `.spotify_cache`: cache OAuth de Spotipy.
- `env/`: entorno virtual local.
- `agent.log`: logs de ejecucion.
- `__pycache__/`: cache Python.

## Scopes De Spotify

El proyecto usa scopes para:

- Leer historial reciente.
- Leer playlists privadas/colaborativas.
- Crear y modificar playlists publicas/privadas.
- Leer reproduccion actual.
- Modificar reproduccion: pausar, reanudar, siguiente, anterior, transferir y agregar a cola.

Scopes relevantes:

```text
user-read-recently-played
user-read-currently-playing
user-read-playback-state
user-modify-playback-state
playlist-modify-private
playlist-modify-public
playlist-read-private
playlist-read-collaborative
```

Si se agregan o cambian scopes, normalmente hay que borrar `.spotify_cache` y volver a autorizar.

## Funcionalidades Actuales

### Autenticacion

- Revisar estado de autenticacion de Spotify.
- Mostrar usuario, plan, pais, scopes cacheados y expiracion aproximada del token.

### Busqueda

- Buscar canciones por query.
- Buscar artistas por query.

### Historial

- Leer canciones reproducidas recientemente.
- Resumir artistas y albumes repetidos.

### Playlists

- Listar playlists del usuario.
- Recomendar canciones basadas en una playlist existente sin modificarla.
- Crear playlist desde busquedas separadas por punto y coma.
- Agregar canciones a una playlist existente desde busquedas.

### Reproductor

- Ver reproduccion actual.
- Pausar musica.
- Reanudar musica.
- Saltar a siguiente cancion.
- Volver a cancion anterior.
- Agregar cancion a la cola desde busqueda.
- Listar dispositivos disponibles.
- Transferir reproduccion a un `device_id` explicito.
- Modo DJ: agrega 3 canciones a la cola usando cancion actual, historial reciente y scoring por modo.

### Modos DJ

- `similar`: modo por defecto; balancea artista actual, historial reciente y popularidad.
- `popular`: prioriza canciones conocidas o con mayor popularidad en Spotify.
- `discover`: busca musica relacionada menos obvia y penaliza repetir demasiado artistas recientes.

## Router Rapido

`main.py` tiene un router rapido para evitar pasar por Ollama en comandos simples.

Ejemplos de comandos directos:

- `que esta sonando`
- `pausa la musica`
- `continua la musica`
- `siguiente cancion`
- `cancion anterior`
- `lista mis playlists`
- `lista mis dispositivos`
- `revisa mi playlist Mix Rap y recomiendame 3 canciones`
- `agrega FEIN a la cola`
- `pon Bohemian Rhapsody despues`
- `transfiere al device_id <ID>`
- `modo dj`
- `modo dj popular`
- `sorprendeme`

Si el router no detecta un comando simple, el flujo cae al agente en `agent.py`.

## Reglas De Seguridad

- Las acciones que modifican Spotify requieren confirmaciones internas explicitas.
- Crear playlist usa `SI_CREAR`.
- Agregar canciones a playlist usa `SI_AGREGAR`.
- Recomendar desde playlist solo lee datos y no requiere confirmacion.
- Pausar usa `SI_PAUSAR`.
- Reanudar usa `SI_REANUDAR`.
- Siguiente cancion usa `SI_SIGUIENTE`.
- Cancion anterior usa `SI_ANTERIOR`.
- Agregar a cola usa `SI_COLA`.
- Transferir reproduccion usa `SI_TRANSFERIR`.
- Modo DJ usa `SI_DJ`.

El agente no debe inventar datos de Spotify. Debe usar tools y responder con el resultado devuelto.

## Limitaciones Importantes

- Controlar reproduccion suele requerir Spotify Premium.
- Debe existir un dispositivo Spotify activo o disponible.
- La API controla clientes Spotify existentes; no reproduce audio por si sola.
- Algunos dispositivos pueden aparecer como restringidos.
- Transferir reproduccion requiere `device_id`; si el usuario no lo da, primero se deben listar dispositivos.

## Verificacion Recomendada

Comandos utiles:

```powershell
.\env\Scripts\python.exe -m compileall main.py agent.py prompts.py spotify_client.py tools.py logging_config.py
```

```powershell
.\env\Scripts\python.exe -c "from agent import agent; print('agent import ok')"
```

## Flujo Git Para El Asistente

Cuando el usuario pida subir cambios a Git:

1. Revisar `git status`.
2. Revisar `git diff`.
3. Resumir los archivos modificados.
4. Proponer un mensaje de commit.
5. Esperar confirmacion explicita del usuario antes de hacer commit.
6. Despues del commit, preguntar antes de hacer push.
7. Nunca hacer push sin confirmacion explicita.

Reglas adicionales:

- No hacer `git add`, `git commit` ni `git push` sin confirmacion del usuario.
- No usar comandos destructivos como `git reset --hard` o `git checkout --` salvo pedido explicito.
- Si hay cambios no relacionados, no revertirlos ni modificarlos.
- Antes de commitear, revisar que no se incluyan secretos como `.env` o `.spotify_cache`.

## Proximas Ideas

- Control de volumen.
- Shuffle y repeat.
- Guardar cancion actual en favoritos o en una playlist.
- Transferencia por nombre de dispositivo con manejo de ambiguedad.
