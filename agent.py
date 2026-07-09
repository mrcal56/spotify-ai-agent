"""
Módulo que configura el modelo de lenguaje y el agente.

Responsabilidad única de este archivo: construir el objeto `agent` ya
listo para usarse (con su modelo y sus tools conectadas). main.py solo
necesita importar `agent` de aquí y llamar a `agent.run(...)`.


"""

from smolagents import CodeAgent, LiteLLMModel

from tools import (
    spotify_search,
    spotify_recently_played,
    spotify_create_playlist_from_search,
)


# Modelo local corriendo en Ollama (http://localhost:11434), usando
# LiteLLM como capa de compatibilidad para que smolagents pueda hablarle
# con la misma interfaz que usaría para OpenAI, Anthropic, etc.
model = LiteLLMModel(
    model_id="ollama_chat/qwen2.5-coder:7b",
    api_base="http://localhost:11434",
    api_key="ollama",
    temperature=0.2,
)

# El CodeAgent es el tipo de agente de smolagents que escribe y ejecuta
# código Python para decidir qué tool llamar (en vez de, por ejemplo,
# responder solo con JSON). max_steps=3 limita cuántas "vueltas" de
# razonamiento/acción puede dar antes de forzar una respuesta final,
# lo cual evita loops infinitos si el modelo se confunde.
agent = CodeAgent(
    model=model,
    tools=[
        spotify_search,
        spotify_recently_played,
        spotify_create_playlist_from_search,
    ],
    max_steps=3,
    verbosity_level=1,
)