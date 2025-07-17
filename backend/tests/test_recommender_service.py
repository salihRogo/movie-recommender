import pytest
import numpy as np
import logging
from app.services.recommender_service import RecommenderService

def test_recommender_service_initialization(mocker):
    """Tests that the RecommenderService can be initialized."""
    # Mock the service dependencies called in the constructor
    mocker.patch("app.services.recommender_service.OmdbService")
    mocker.patch("app.services.recommender_service.MovieDataService")

    # Act
    service = RecommenderService()

    # Assert
    assert service is not None
    assert service.model_loaded is False


def test_load_model_success(mocker):
    """Tests successful loading of all model components."""
    # Arrange
    mocker.patch("app.services.recommender_service.OmdbService")
    mocker.patch("app.services.recommender_service.MovieDataService")
    service = RecommenderService()

    # Mock file system and joblib dependencies
    mocker.patch("pathlib.Path.exists", return_value=True)

    mock_model_components = {'qi': np.array([[1, 2], [3, 4]])}
    mock_raw_to_inner = {'movie1': 1, 'movie2': 2}
    mock_popular_movies = ['imdb1', 'imdb2']

    mock_load = mocker.patch("joblib.load", side_effect=[
        mock_model_components,
        mock_raw_to_inner,
        mock_popular_movies
    ])

    # Act
    service.load_model()

    # Assert
    assert service.model_loaded is True
    assert np.array_equal(service.qi, mock_model_components['qi'])
    assert service.raw_to_inner_iid_map == mock_raw_to_inner
    assert service.inner_to_raw_iid_map == {1: 'movie1', 2: 'movie2'}
    assert service.popular_movie_ids_fallback == mock_popular_movies
    assert mock_load.call_count == 3


def test_load_model_file_not_found(mocker):
    """Tests that the service handles missing model files gracefully."""
    # Arrange
    mocker.patch("app.services.recommender_service.OmdbService")
    mocker.patch("app.services.recommender_service.MovieDataService")
    service = RecommenderService()

    # Mock file system to simulate files not existing
    mocker.patch("pathlib.Path.exists", return_value=False)
    mock_warning_logger = mocker.patch("app.services.recommender_service.logger.warning")

    # Act
    service.load_model()

    # Assert
    assert service.model_loaded is False
    assert service.qi is None
    assert service.raw_to_inner_iid_map == {}
    # Check that a warning was logged
    assert mock_warning_logger.call_count > 0


def test_get_recommendations_for_profile_success(mocker):
    """Tests successful recommendation generation for a user profile."""
    # Arrange
    mock_movie_data_service = mocker.patch("app.services.recommender_service.MovieDataService").return_value
    mocker.patch("app.services.recommender_service.OmdbService")
    service = RecommenderService()

    # Simulate a loaded model
    service.model_loaded = True
    service.qi = np.array([
        [0.1, 0.2, 0.3],  # item 0
        [0.4, 0.5, 0.6],  # item 1
        [0.7, 0.8, 0.9],  # item 2 (recommended)
        [0.2, 0.3, 0.1],  # item 3 (recommended)
    ])
    service.raw_to_inner_iid_map = {
        'liked_movie_1': 0,
        'liked_movie_2': 1,
        'rec_movie_1': 2,
        'rec_movie_2': 3,
    }
    service.inner_to_raw_iid_map = {v: k for k, v in service.raw_to_inner_iid_map.items()}

    # Mock the movie data service calls to align with the raw_to_inner_iid_map
    def get_raw_id_side_effect(imdb_id):
        if imdb_id == 'liked_imdb_1':
            return 'liked_movie_1'
        if imdb_id == 'liked_imdb_2':
            return 'liked_movie_2'
        return None
    mock_movie_data_service.get_raw_movie_id_from_imdb_id.side_effect = get_raw_id_side_effect
    mock_movie_data_service.get_imdb_ids_from_raw_ids.return_value = ['rec_imdb_1', 'rec_imdb_2']

    # Act
    recommendations, message = service.get_recommendations_for_profile(
        imdb_ids=['liked_imdb_1', 'liked_imdb_2'], n=2
    )

    # Assert
    assert len(recommendations) == 2
    assert recommendations == ['rec_imdb_1', 'rec_imdb_2']
    assert "Generated" in message


def test_get_recommendations_model_not_loaded_fallback(mocker):
    """Tests that the service returns popular movies when the model is not loaded."""
    # Arrange
    mocker.patch("app.services.recommender_service.MovieDataService")
    mocker.patch("app.services.recommender_service.OmdbService")
    service = RecommenderService()

    service.model_loaded = False
    service.popular_movie_ids_fallback = ['popular1', 'popular2']

    # Act
    recommendations, message = service.get_recommendations_for_profile(imdb_ids=['any_id'], n=2)

    # Assert
    assert recommendations == ['popular1', 'popular2']
    assert "model is loading" in message.lower()


def test_get_recommendations_no_movies_mapped_fallback(mocker):
    """Tests fallback when user's movies can't be mapped."""
    # Arrange
    mock_movie_data_service = mocker.patch("app.services.recommender_service.MovieDataService").return_value
    mocker.patch("app.services.recommender_service.OmdbService")
    service = RecommenderService()

    # Simulate a loaded model but no mappable movies
    service.model_loaded = True
    service.qi = np.array([[1, 2], [3, 4]]) # Model needs some data
    service.popular_movie_ids_fallback = ['popular1', 'popular2']
    mock_movie_data_service.get_raw_movie_id_from_imdb_id.return_value = None

    # Act
    recommendations, message = service.get_recommendations_for_profile(imdb_ids=['unknown_id'], n=2)

    # Assert
    assert recommendations == ['popular1', 'popular2']
    assert "none of your liked movies were found" in message.lower()


def test_load_model_critical_error(mocker):
    """Tests that a critical error during model loading is handled."""
    # Arrange
    mocker.patch("app.services.recommender_service.OmdbService")
    mocker.patch("app.services.recommender_service.MovieDataService")
    service = RecommenderService()

    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("joblib.load", side_effect=Exception("Critical load error"))
    mock_error_logger = mocker.patch("app.services.recommender_service.logger.error")

    # Act
    service.load_model()

    # Assert
    assert service.model_loaded is False
    mock_error_logger.assert_called_once()


def test_get_recommendations_no_valid_inner_ids_fallback(mocker):
    """Tests fallback when inner IDs are out of bounds."""
    # Arrange
    mock_movie_data_service = mocker.patch("app.services.recommender_service.MovieDataService").return_value
    mocker.patch("app.services.recommender_service.OmdbService")
    service = RecommenderService()

    service.model_loaded = True
    service.qi = np.array([[1, 2]]) # Only one item in model
    service.raw_to_inner_iid_map = {'movie1': 100} # Invalid inner ID
    service.popular_movie_ids_fallback = ['popular1']
    mock_movie_data_service.get_raw_movie_id_from_imdb_id.return_value = 'movie1'

    # Act
    recommendations, message = service.get_recommendations_for_profile(imdb_ids=['imdb1'], n=1)

    # Assert
    assert recommendations == ['popular1']
    assert "could not generate recommendations" in message.lower()


def test_get_recommendations_no_imdb_ids_found_fallback(mocker):
    """Tests fallback when no IMDb IDs are found for recommended raw IDs."""
    # Arrange
    mock_movie_data_service = mocker.patch("app.services.recommender_service.MovieDataService").return_value
    mocker.patch("app.services.recommender_service.OmdbService")
    service = RecommenderService()

    service.model_loaded = True
    service.qi = np.array([[0.1, 0.2], [0.3, 0.4]])
    service.raw_to_inner_iid_map = {'movie1': 0, 'rec_movie': 1}
    service.inner_to_raw_iid_map = {0: 'movie1', 1: 'rec_movie'}
    service.popular_movie_ids_fallback = ['popular1']
    mock_movie_data_service.get_raw_movie_id_from_imdb_id.return_value = 'movie1'
    mock_movie_data_service.get_imdb_ids_from_raw_ids.return_value = [] # No IDs found

    # Act
    recommendations, message = service.get_recommendations_for_profile(imdb_ids=['imdb1'], n=1)

    # Assert
    assert recommendations == ['popular1']
    assert "no recommendations found" in message.lower()


def test_get_recommender_service(mocker):
    """Tests the dependency injector for RecommenderService."""
    from app.services.recommender_service import get_recommender_service
    # Mock dependencies for initialization
    mocker.patch("app.services.recommender_service.OmdbService")
    mocker.patch("app.services.recommender_service.MovieDataService")

    service = get_recommender_service()
    assert isinstance(service, RecommenderService)
    # Clear cache for other tests
    get_recommender_service.cache_clear()
