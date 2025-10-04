"""Configuration management for Watch2 Media Server."""

from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, PostgresDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Watch2 Media Server"
    VERSION: str = "3.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database - 
    DATABASE_URL: str = "postgresql://watch2:watch2password@localhost:5432/watch2"
    SQLALCHEMY_DATABASE_URI: str = DATABASE_URL
    DATABASE_ECHO: bool = False

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8000",
        "http://192.168.254.21:3000",  # Lexicon IP
        "http://192.168.254.21:8000",  # Lexicon IP
        "http://Lexicon:3000",         # Hostname
        "http://Lexicon:8000",         # Hostname
    ]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Media settings
    MEDIA_ROOT: str = "/app/media"
    THUMBNAILS_ROOT: str = "/app/thumbnails"
    DATA_ROOT: str = "/app/data"
    MAX_UPLOAD_SIZE: int = 1024 * 1024 * 1024 * 5  # 5GB
    
    # Redis (for caching and background tasks)
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings
