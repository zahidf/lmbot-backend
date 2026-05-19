from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Lanemark Bot API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lmbot_db"
    DATABASE_ECHO: bool = True
    DB_USER: str
    DB_PASSWORD:str
    DB_HOST:str
    DB_PORT:str
    DB_NAME:str
    
    # Security
    SECRET_KEY: str = "secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5-nano"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_TEMPERATURE: float = 0.7
    
    # RAG Settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_DOCUMENTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    VECTOR_DIMENSION: int = 1536
    SEMANTIC_CHUNKING_BREAKPOINT_THRESHOLD_TYPE: str = "percentile"
    SEMANTIC_CHUNKING_BREAKPOINT_THRESHOLD: float = 80.0
    SEMANTIC_CHUNKING_MIN_CHUNK_SIZE: int = 500
    SEMANTIC_CHUNKING_MAX_CHUNK_SIZE: int = 1500
    SEMANTIC_CHUNKING_CHUNK_OVERLAP: int = 200
    
    # Supabase Storage
    USE_SUPABASE_STORAGE: bool = False
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "documents"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings