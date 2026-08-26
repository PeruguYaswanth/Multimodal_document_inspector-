import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Universal Multimodal Document Analyzer"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # LLM Settings (OpenRouter / OpenAI API)
    OPENROUTER_API_KEY: str = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OR_API_KEY")
        or ""
    )
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini"))
    OPENROUTER_FALLBACK_MODEL: str = "openai/gpt-4o"
    OPENROUTER_MAX_RETRIES: int = 3
    OPENROUTER_RETRY_DELAY: float = 2.0

    # Backwards compatibility aliases
    OPENAI_API_KEY: str = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OR_API_KEY")
        or ""
    )
    OPENAI_MODEL: str = OPENROUTER_MODEL
    OPENAI_FALLBACK_MODEL: str = OPENROUTER_FALLBACK_MODEL
    OPENAI_MAX_RETRIES: int = OPENROUTER_MAX_RETRIES
    OPENAI_RETRY_DELAY: float = OPENROUTER_RETRY_DELAY
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/doc_analyzer.db"
    
    # File Storage
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    SAMPLE_DIR: Path = BASE_DIR / "sample_images"
    MAX_FILE_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: set = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
