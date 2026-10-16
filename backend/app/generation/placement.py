"""Where the model is resident: the one definition shared by the benchmark and the service.

`gpu_fraction` reads a parsed Ollama `GET /api/ps` body. `None` means "unknown" and is never a guess:
`0.0` means "fully on CPU", a different and actionable fact, so unknown must not look like it.
"""

from __future__ import annotations


def gpu_fraction(ps_body: dict, model: str) -> float | None:
    """size_vram / size of the entry named `model`, rounded to 3 places; None if it cannot be known
    (model not listed, size missing or 0, malformed body or values)."""
    try:
        for entry in ps_body["models"]:
            if entry.get("name") != model:
                continue
            size, vram = entry.get("size"), entry.get("size_vram")
            if isinstance(size, bool) or isinstance(vram, bool):
                return None
            if not isinstance(size, (int, float)) or not isinstance(vram, (int, float)) or size <= 0 or vram < 0:
                return None
            return round(vram / size, 3)
    except (KeyError, TypeError, AttributeError):
        return None
    return None
