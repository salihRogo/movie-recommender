import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
import threading

from app.main import app, get_recommender_service, get_omdb_service, RecommenderService, OmdbService


@pytest.fixture
def mock_recommender_service():
    """Provides a mock RecommenderService that signals when load_model is called."""
    service = MagicMock(autospec=RecommenderService)
    load_model_called_event = threading.Event()

    def side_effect(*args, **kwargs):
        load_model_called_event.set()

    service.load_model = MagicMock(side_effect=side_effect)
    service._load_model_called_event = load_model_called_event
    return service


@pytest.fixture
def client(mock_recommender_service):
    """Provides a TestClient with isolated dependencies and lifecycle management."""
    app.dependency_overrides[get_recommender_service] = lambda: mock_recommender_service
    with TestClient(app) as test_client:
        success = mock_recommender_service._load_model_called_event.wait(timeout=5)
        if not success:
            pytest.fail("The load_model method was not called within the timeout.")
        yield test_client
    app.dependency_overrides.clear()


def test_root_endpoint(client):
    """Tests the root endpoint for a successful response."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Movie Recommender API!"}


def test_lifespan_loads_model(client, mock_recommender_service):
    """Tests that the model is loaded on startup via the lifespan event."""
    mock_recommender_service.load_model.assert_called_once()


def test_get_profile_recommendations_success(client):
    """Tests the /recommendations/by_profile endpoint for a successful response."""
    recommender_service = app.dependency_overrides[get_recommender_service]()
    recommender_service.get_recommendations_for_profile.return_value = (
        ['tt0088763', 'tt0099685'], "Generated recommendations."
    )
    mock_omdb = MagicMock(autospec=OmdbService)
    mock_omdb.get_movie_details_by_ids = AsyncMock(return_value=[
        {"imdb_id": "tt0088763", "title": "Back to the Future", "year": "1985"},
        {"imdb_id": "tt0099685", "title": "Goodfellas", "year": "1990"},
    ])
    app.dependency_overrides[get_omdb_service] = lambda: mock_omdb

    response = client.post("/recommendations/by_profile", json={"imdb_ids": ["tt0111161"]})

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Generated recommendations."
    assert len(data["recommendations"]) == 2


def test_search_movies_success(client):
    """Tests the /search endpoint for a successful response."""
    mock_omdb = MagicMock(autospec=OmdbService)
    mock_omdb.search_movies_by_title = AsyncMock(return_value=[
        {"imdb_id": "tt0076759", "title": "Star Wars", "year": "1977"}
    ])
    app.dependency_overrides[get_omdb_service] = lambda: mock_omdb

    response = client.get("/search?movie_title=Star+Wars")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_profile_recommendations_service_error(client):
    """Tests a 500 error if the recommender service fails."""
    recommender_service = app.dependency_overrides[get_recommender_service]()
    recommender_service.get_recommendations_for_profile.side_effect = Exception("Service Failure")

    response = client.post("/recommendations/by_profile", json={"imdb_ids": ["tt0111161"]})

    assert response.status_code == 500


def test_search_movies_internal_error(client):
    """Tests a 500 error if the search service fails."""
    mock_omdb = MagicMock(autospec=OmdbService)
    mock_omdb.search_movies_by_title = AsyncMock(side_effect=Exception("Search Failure"))
    app.dependency_overrides[get_omdb_service] = lambda: mock_omdb

    response = client.get("/search?movie_title=fail")

    assert response.status_code == 500


def test_get_profile_recommendations_no_ids_returned(client):
    """Tests when no recommendation IDs are returned."""
    recommender_service = app.dependency_overrides[get_recommender_service]()
    recommender_service.get_recommendations_for_profile.return_value = ([], "No IDs found.")

    response = client.post("/recommendations/by_profile", json={"imdb_ids": ["tt0111161"]})

    assert response.status_code == 200
    assert response.json()["recommendations"] == []
