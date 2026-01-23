"""Model backend layer for OpenAI-compatible APIs.

Provides adapters for local model servers that expose OpenAI-compatible APIs:

Supported Backends:
    - Ollama: create_ollama_backend("llama3.2")
    - vLLM: create_vllm_backend("meta-llama/Llama-3.2-3B-Instruct")
    - LM Studio: create_lmstudio_backend()
    - Custom: OpenAICompatibleBackend(model, base_url, api_key)

Usage:
    >>> from mamba_agents.backends import create_ollama_backend
    >>> backend = create_ollama_backend("llama3.2")
    >>> # Use with Agent via settings.model_backend

Model Profiles:
    >>> from mamba_agents.backends import get_profile
    >>> profile = get_profile("gpt-4o")
    >>> print(f"Context window: {profile.context_window}")
    >>> print(f"Supports tools: {profile.supports_tools}")

See Also:
    - examples/advanced/local_models.py for runnable example
    - docs/user-guide/model-backends.md for detailed guide
"""

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
    "ModelBackend",
    "ModelProfile",
    "ModelResponse",
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
