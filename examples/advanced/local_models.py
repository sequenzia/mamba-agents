#!/usr/bin/env python3
"""Local model backends example.

This example demonstrates:
- Using Ollama
- Using vLLM
- Using LM Studio
- Custom OpenAI-compatible backends

Prerequisites:
- One of: Ollama, vLLM, or LM Studio running locally
"""

from mamba_agents.backends import (
    get_profile,
)


def ollama_example():
    """Using Ollama."""
    print("--- Ollama Example ---\n")

    # Create Ollama backend
    # backend = create_ollama_backend("llama3.2")
    # print(f"Backend: {backend}")

    # Or configure via settings
    # Set these environment variables:
    #   MAMBA_MODEL_BACKEND__BASE_URL=http://localhost:11434/v1
    #   MAMBA_MODEL_BACKEND__MODEL=llama3.2

    print("To use Ollama:")
    print("  1. Start Ollama: ollama serve")
    print("  2. Pull a model: ollama pull llama3.2")
    print("  3. Set env vars:")
    print("     MAMBA_MODEL_BACKEND__BASE_URL=http://localhost:11434/v1")
    print("     MAMBA_MODEL_BACKEND__MODEL=llama3.2")
    print("  4. Create agent: Agent(settings=AgentSettings())")


def vllm_example():
    """Using vLLM."""
    print("\n--- vLLM Example ---\n")

    # Create vLLM backend
    # backend = create_vllm_backend("meta-llama/Llama-3.2-3B-Instruct")

    print("To use vLLM:")
    print("  1. Start vLLM server:")
    print("     vllm serve meta-llama/Llama-3.2-3B-Instruct")
    print("  2. Set env vars:")
    print("     MAMBA_MODEL_BACKEND__BASE_URL=http://localhost:8000/v1")
    print("     MAMBA_MODEL_BACKEND__MODEL=meta-llama/Llama-3.2-3B-Instruct")


def lmstudio_example():
    """Using LM Studio."""
    print("\n--- LM Studio Example ---\n")

    # Create LM Studio backend
    # backend = create_lmstudio_backend()

    print("To use LM Studio:")
    print("  1. Open LM Studio and load a model")
    print("  2. Start local server (default port: 1234)")
    print("  3. Set env vars:")
    print("     MAMBA_MODEL_BACKEND__BASE_URL=http://localhost:1234/v1")
    print("     MAMBA_MODEL_BACKEND__MODEL=local-model")


def custom_backend_example():
    """Custom OpenAI-compatible backend."""
    print("\n--- Custom Backend Example ---\n")

    # Create custom backend
    # backend = OpenAICompatibleBackend(
    #     model="my-model",
    #     base_url="http://localhost:8000/v1",
    #     api_key="optional-key",
    # )

    print("For any OpenAI-compatible API:")
    print("  backend = OpenAICompatibleBackend(")
    print('      model="my-model",')
    print('      base_url="http://localhost:8000/v1",')
    print('      api_key="optional-key",')
    print("  )")


def model_profiles_example():
    """Check model capabilities."""
    print("\n--- Model Profiles Example ---\n")

    # Get profile for a known model
    profile = get_profile("gpt-4o")
    print("Profile for gpt-4o:")
    print(f"  Context window: {profile.context_window}")
    print(f"  Supports tools: {profile.supports_tools}")
    print(f"  Provider: {profile.provider}")


def main():
    ollama_example()
    vllm_example()
    lmstudio_example()
    custom_backend_example()
    model_profiles_example()


if __name__ == "__main__":
    main()
