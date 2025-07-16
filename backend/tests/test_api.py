import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

from app.main import app
from app.services.recommender_service import get_recommender_service
from app.services.omdb_service import get_omdb_service


@pytest.fixture
def client():
    """Provides a TestClient for making API requests."""
    yield TestClient(app)
    # Clean up the dependency overrides after the test
    app.dependency_overrides.clear()


def test_get_profile_recommendations_success(client):
    """Tests the /recommendations/by_profile endpoint for a successful response."""
    # Arrange
    # 1. Mock the RecommenderService
    mock_recommender = MagicMock()
    mock_recommender.get_recommendations_for_profile.return_value = (
        ['tt0088763', 'tt0099685'], "Generated recommendations."
    )

    # 2. Mock the OmdbService
    mock_omdb = MagicMock()
    mock_omdb.get_movie_details_by_ids = AsyncMock(return_value=[
        {"imdb_id": "tt0088763", "title": "Back to the Future", "year": "1985"},
        {"imdb_id": "tt0099685", "title": "Goodfellas", "year": "1990"}
    ])

    # 3. Override dependencies in the FastAPI app
    app.dependency_overrides[get_recommender_service] = lambda: mock_recommender
    app.dependency_overrides[get_omdb_service] = lambda: mock_omdb

    # Act
    response = client.post("/recommendations/by_profile", json={"imdb_ids": ["tt0111161"]})

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Generated recommendations."
    assert len(data["recommendations"]) == 2
    assert data["recommendations"][0]["title"] == "Back to the Future"


def test_search_movies_success(client):
    """Tests the /search endpoint for a successful response."""
    # Arrange
    mock_omdb = MagicMock()
    mock_omdb.search_movies_by_title = AsyncMock(return_value=[
        {"imdb_id": "tt0076759", "title": "Star Wars: Episode IV - A New Hope", "year": "1977"}
    ])

    app.dependency_overrides[get_omdb_service] = lambda: mock_omdb

    # Act
    response = client.get("/search?movie_title=Star+Wars")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Star Wars: Episode IV - A New Hope"


def test_get_profile_recommendations_service_error(client):
    """Tests that a 500 error is returned if the recommender service fails."""
    # Arrange
    mock_recommender = MagicMock()
    mock_recommender.get_recommendations_for_profile.side_effect = Exception("Service Failure")

    app.dependency_overrides[get_recommender_service] = lambda: mock_recommender

    # Act
    response = client.post("/recommendations/by_profile", json={"imdb_ids": ["tt0111161"]})

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to generate recommendations."}

