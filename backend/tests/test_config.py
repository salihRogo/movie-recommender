import pytest
from pydantic import ValidationError

from app.core.config import Settings

def test_settings_missing_omdb_api_key(monkeypatch):
    """Tests that a ValueError is raised if OMDB_API_KEY is missing."""
    # Arrange
    # Unset the environment variable to simulate it being missing
    monkeypatch.setenv("OMDB_API_KEY", "")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    
    assert "OMDB_API_KEY must be set and non-empty" in str(exc_info.value)
