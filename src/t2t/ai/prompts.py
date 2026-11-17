"""Prompt template loader for versioned text prompts."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a versioned prompt template from disk.

    Raises:
        FileNotFoundError: If prompt template does not exist.
    """
    filename = f"{name}.txt" if not name.endswith(".txt") else name
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt template '{name}' not found at {path}")

    return path.read_text(encoding="utf-8").strip()
