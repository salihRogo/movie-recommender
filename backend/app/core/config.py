from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os # Ensure os module is imported

# Define the base directory of the backend application
# This helps in constructing absolute paths if needed
# __file__ is '.../backend/app/core/config.py'
# .parent is '.../backend/app/core/'
# .parent.parent is '.../backend/app/'
# .parent.parent.parent is '.../backend/'
BACKEND_APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT_DIR = BACKEND_APP_DIR.parent.parent # Assumes backend/app/core structure
BACKEND_DIR = BACKEND_APP_DIR.parent # .../movie-recommender-2/backend/

class Settings(BaseSettings):
    # --- Heroku Specific Settings ---
    # These are used when the ON_HEROKU environment variable is set to "true"
    ON_HEROKU: bool = os.getenv("ON_HEROKU", "False").lower() == "true"
    # --- General Settings ---

    # Database Configuration (PostgreSQL)
    # Example: postgresql://user:password@host:port/database
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # OMDb API Configuration (http://www.omdbapi.com/)
    OMDB_API_BASE_URL: str = os.getenv("OMDB_API_BASE_URL")
    OMDB_API_KEY: str = os.getenv("OMDB_API_KEY")

    # Recommender Service settings (can be adjusted via .env)
    API_RECOMMENDER_DATA_SAMPLE_N: int = 200000 # This is now effectively unused by RecommenderService __init__
    API_RECOMMENDER_FORCE_RETRAIN: bool = False # This is now effectively unused by RecommenderService __init__

    # Pydantic settings configuration
    # env_file should point to backend/.env
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),  # .env file is in the backend directory
        extra="allow"
    )

settings = Settings()

# To verify paths:
# print(f"Project Root Dir: {PROJECT_ROOT_DIR}")
# print(f"Backend App Dir: {BACKEND_APP_DIR}")
# print(f"Backend .env path: {BACKEND_APP_DIR.parent / '.env'}")
