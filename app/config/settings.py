"""
Application configuration.
Loads settings from environment variables / .env file.
No business logic lives here.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MedX AI Platform"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./medx.db"

    # Auth
    secret_key: str = "change-me-in-prod"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Model
    model_weights_path: str = "training/checkpoints/model.pth"
    device: str = "cpu"

    # Storage
    storage_dir: str = "storage"

    # LLM
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())


settings = Settings()
