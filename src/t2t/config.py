"""Configuration and inventory models using Pydantic."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr


class Router(BaseModel):
    """Router definition in inventory."""

    name: str
    host: str
    role: str
    device_type: str | None = None
    golden_path: str | None = None


class Inventory(BaseModel):
    """Lab inventory structure."""

    defaults: dict[str, Any] = Field(default_factory=dict)
    routers: list[Router] = Field(default_factory=list)
    interfaces: dict[str, dict[str, str]] = Field(default_factory=dict)


class Settings(BaseModel):
    """Application settings loaded from environment."""

    lab_username: str = "admin"
    lab_password: SecretStr = SecretStr("change-me")
    t2t_inventory: Path = Path("lab/inventory.yaml")
    t2t_db_path: Path = Path(".t2t/t2t.db")
    t2t_ai_provider: str = "none"
    t2t_ai_timeout: int = 60
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = ""
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = ""
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""


def load_settings(env_file: Path | None = None) -> Settings:
    """Load settings from environment and optional .env file."""
    if env_file and env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    return Settings(
        lab_username=os.getenv("LAB_USERNAME", "admin"),
        lab_password=SecretStr(os.getenv("LAB_PASSWORD", "change-me")),
        t2t_inventory=Path(os.getenv("T2T_INVENTORY", "lab/inventory.yaml")),
        t2t_db_path=Path(os.getenv("T2T_DB_PATH", ".t2t/t2t.db")),
        t2t_ai_provider=os.getenv("T2T_AI_PROVIDER", "none"),
        t2t_ai_timeout=int(os.getenv("T2T_AI_TIMEOUT", "60")),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", ""),
        gemini_api_key=SecretStr(os.getenv("GEMINI_API_KEY", "")),
        gemini_model=os.getenv("GEMINI_MODEL", ""),
        openai_api_key=SecretStr(os.getenv("OPENAI_API_KEY", "")),
        openai_model=os.getenv("OPENAI_MODEL", ""),
    )


def load_inventory(path: Path | None = None) -> Inventory:
    """Load and parse inventory YAML file."""
    inv_path = path or Path("lab/inventory.yaml")
    if not inv_path.exists():
        example_path = Path("lab/inventory.example.yaml")
        if example_path.exists():
            inv_path = example_path
        else:
            raise FileNotFoundError(f"Inventory file not found: {inv_path}")

    with inv_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML structure in {inv_path}")

    return Inventory.model_validate(data)
