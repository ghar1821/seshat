"""
Integration tests for digest/llm.py — provider connectivity.

These tests verify that both LLM providers are reachable and credentials are
valid. They make real network or local service calls but consume no tokens and
generate no LLM output.

Requirements
------------
  Anthropic : a valid API key in ANTHROPIC_API_KEY env var or ~/.seshat/config.toml
  Ollama    : a running Ollama server at the default address (http://localhost:11434)

Running
-------
    uv run pytest -m integration          # integration tests only
    uv run pytest -m "not integration"    # unit tests only (default CI run)
    uv run pytest                         # all tests

Cost
----
  Anthropic tests call GET /v1/models — validates the API key with no token usage.
  Ollama tests call the local list endpoint — no inference, no cost.
"""

import pytest


@pytest.mark.integration
def test_anthropic_client_initialises():
    """
    AnthropicProvider._get_client() returns a client when a valid API key is
    available. Raises AuthenticationError if no key is found in the env var or
    config file.

    Input:  API key from ANTHROPIC_API_KEY env var or ~/.seshat/config.toml [auth]
    Expected output: client object is not None
    """
    from digest.config import get_config
    from digest.llm import AnthropicProvider

    cfg = get_config()
    provider = AnthropicProvider(model=cfg.anthropic_model)
    client = provider._get_client()
    assert client is not None


@pytest.mark.integration
def test_anthropic_models_list_confirms_auth():
    """
    client.models.list() makes a real API call (GET /v1/models) that validates
    the API key without generating any output or consuming tokens. A non-empty
    response confirms the key is accepted.

    Input:  valid API key
    Expected output: at least one model returned
    """
    from digest.config import get_config
    from digest.llm import AnthropicProvider

    cfg = get_config()
    provider = AnthropicProvider(model=cfg.anthropic_model)
    client = provider._get_client()
    models = list(client.models.list())
    assert len(models) > 0


@pytest.mark.integration
def test_ollama_server_is_reachable():
    """
    ollama.list() queries the local Ollama server for installed models. A
    successful response confirms the server is running at the default address.
    The models list may be empty if nothing has been pulled yet.

    Input:  running Ollama server (http://localhost:11434)
    Expected output: response dict contains a "models" key
    """
    import ollama

    response = ollama.list()
    assert "models" in response
