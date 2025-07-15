from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os
from typing import Optional

# Define the base directory of the backend application
# This helps in constructing absolute paths if needed
# __file__ is '.../backend/app/core/config.py'
# .parent is '.../backend/app/core/'
# .parent.parent is '.../backend/app/'
# .parent.parent.parent is '.../backend/'
BACKEND_APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT_DIR = BACKEND_APP_DIR.parent.parent # Assumes backend/app/core structure
BACKEND_DIR = BACKEND_APP_DIR.parent # .../movie-recommender-2/backend/

# --- Model Path --- 
MODELS_DIR = BACKEND_DIR / "models"
MODEL_PATH = MODELS_DIR / "svd_model.joblib"

class Settings(BaseSettings):
    # --- Heroku Specific Settings ---
    ON_HEROKU: bool = False

    # --- General Settings ---
    DATABASE_URL: str
    OMDB_API_BASE_URL: Optional[str] = None
    OMDB_API_KEY: str

    @field_validator("OMDB_API_KEY")
    @classmethod
    def validate_omdb_api_key(cls, v: str):
        if not v or not v.strip():
            raise ValueError("OMDB_API_KEY must be set and non-empty in your environment or .env file.")
        return v

    model_config = SettingsConfigDict(
        env_file=f"{BACKEND_DIR}/.env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()
