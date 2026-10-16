"""Shared exception type (kept separate so model.py and rules.py can both raise it)."""


class ModelLoadError(RuntimeError):
    """The artifact failed verification; the model must not be used."""
