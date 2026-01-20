"""Model backend layer for OpenAI-compatible APIs."""

from mamba_agents.backends.base import ModelBackend, ModelResponse, StreamChunk
from mamba_agents.backends.openai_compat import (
    OpenAICompatibleBackend,
    create_lmstudio_backend,
    create_ollama_backend,
    create_vllm_backend,
)
from mamba_agents.backends.profiles import (
    ModelProfile,
    get_profile,
    get_profiles_by_provider,
    list_profiles,
    register_profile,
)

__all__ = [
    # Base classes
    "ModelBackend",
    # Profiles
    "ModelProfile",
    "ModelResponse",
    # OpenAI compatible
    "OpenAICompatibleBackend",
    "StreamChunk",
    "create_lmstudio_backend",
    "create_ollama_backend",
    "create_vllm_backend",
    "get_profile",
    "get_profiles_by_provider",
    "list_profiles",
    "register_profile",
]
