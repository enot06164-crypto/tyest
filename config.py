"""Configuration for Iskra"""
import os

# Use current working directory for database (where main.py is run from)
DATABASE_FILE = os.path.join(os.getcwd(), "iskra.db")

try:
    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        APP_NAME: str = "Iskra"
        APP_VERSION: str = "1.0.0"
        DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

        # Database - explicitly in current working directory
        DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_FILE}")

        # Security
        SECRET_KEY: str = os.getenv("SECRET_KEY", "iskra-super-secret-key-change-in-production-2026")
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_DAYS: int = 30

        # File uploads
        UPLOAD_DIR: str = os.path.join(os.getcwd(), "app", "static", "uploads")
        MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
        ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/png", "image/gif", "image/webp"]

        # Rate limiting
        RATE_LIMIT_REQUESTS: int = 100
        RATE_LIMIT_WINDOW: int = 60  # seconds

        class Config:
            env_file = ".env"

    settings = Settings()

except ImportError:
    # Fallback without pydantic-settings
    class Settings:
        APP_NAME: str = "Iskra"
        APP_VERSION: str = "1.0.0"
        DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
        DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_FILE}")
        SECRET_KEY: str = os.getenv("SECRET_KEY", "iskra-super-secret-key-change-in-production-2026")
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_DAYS: int = 30
        UPLOAD_DIR: str = os.path.join(os.getcwd(), "app", "static", "uploads")
        MAX_FILE_SIZE: int = 10 * 1024 * 1024
        ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        RATE_LIMIT_REQUESTS: int = 100
        RATE_LIMIT_WINDOW: int = 60

    settings = Settings()
