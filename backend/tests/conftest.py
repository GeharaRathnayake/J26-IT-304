"""Tests never touch a real Ollama, even when one is running on this machine (S8).

The service defaults to the `ollama` provider. Every test therefore runs with LLM_PROVIDER=template
and OLLAMA_URL pointing at a closed port, unless the test overrides the provider explicitly; a test
that needs ollama behaviour injects an OllamaAdapter on httpx.MockTransport (`ollama_transport=` in
`create_app`). The environment is also set at import time, because importing `app.main` builds a
module-level app (and its Settings) before any fixture runs.
"""

import os

import pytest

GUARD_ENV = {"LLM_PROVIDER": "template", "OLLAMA_URL": "http://127.0.0.1:9"}

os.environ.update(GUARD_ENV)


@pytest.fixture(autouse=True)
def no_real_ollama(monkeypatch):
    for key, value in GUARD_ENV.items():
        monkeypatch.setenv(key, value)
