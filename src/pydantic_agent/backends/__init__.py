"""Model backend layer for OpenAI-compatible APIs."""

from pydantic_agent.backends.base import ModelBackend, ModelResponse, StreamChunk
from pydantic_agent.backends.openai_compat import (
    OpenAICompatibleBackend,
    create_lmstudio_backend,
    create_ollama_backend,
    create_vllm_backend,
)
from pydantic_agent.backends.profiles import (
    ModelProfile,
    get_profile,
    get_profiles_by_provider,
    list_profiles,
    register_profile,
)

__all__ = [
    # Base classes
    "ModelBackend",
    "ModelResponse",
    "StreamChunk",
    # OpenAI compatible
    "OpenAICompatibleBackend",
    "create_ollama_backend",
    "create_vllm_backend",
    "create_lmstudio_backend",
    # Profiles
    "ModelProfile",
    "get_profile",
    "register_profile",
    "list_profiles",
    "get_profiles_by_provider",
]
