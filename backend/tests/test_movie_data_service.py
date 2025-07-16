import pytest
from unittest.mock import MagicMock

from app.services.movie_data_service import MovieDataService


@pytest.fixture
def mock_db_engine(mocker):
    """Fixture to mock the database engine and its connection."""
    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    return mock_engine, mock_connection


def test_movie_data_service_initialization_success(mocker, mock_db_engine):
    """Tests that the MovieDataService initializes successfully with a DB engine."""
    # Arrange
    mock_engine, _ = mock_db_engine
    mocker.patch('app.services.movie_data_service.create_engine', return_value=mock_engine)
    mock_verify_table = mocker.patch('app.services.movie_data_service.MovieDataService._verify_enhanced_links_table')

    # Act
    service = MovieDataService()

    # Assert
    assert service._db_engine is not None
    mock_verify_table.assert_called_once()


def test_movie_data_service_initialization_failure(mocker):
    """Tests that the MovieDataService handles a DB engine creation failure."""
    # Arrange
    mocker.patch('app.services.movie_data_service.create_engine', side_effect=Exception("DB connection failed"))
    mock_logger_error = mocker.patch('app.services.movie_data_service.logger.error')

    # Act
    service = MovieDataService()

    # Assert
    assert service._db_engine is None
    mock_logger_error.assert_called_once()


def test_get_raw_movie_id_from_imdb_id_success(mocker, mock_db_engine):
    """Tests successful retrieval of a raw movie ID from an IMDb ID."""
    # Arrange
    mock_engine, mock_connection = mock_db_engine
    mock_connection.execute.return_value.fetchone.return_value = ('12345',)
    mocker.patch('app.services.movie_data_service.create_engine', return_value=mock_engine)
    mocker.patch('app.services.movie_data_service.MovieDataService._verify_enhanced_links_table')
    service = MovieDataService()

    # Act
    result = service.get_raw_movie_id_from_imdb_id('tt98765')

    # Assert
    assert result == '12345'
    assert service._mapping_stats['enhanced_hits'] == 1
    assert service._mapping_stats['total_requests'] == 1


def test_get_raw_movie_id_from_imdb_id_not_found(mocker, mock_db_engine):
    """Tests that the service returns None when an IMDb ID is not found."""
    # Arrange
    mock_engine, mock_connection = mock_db_engine
    mock_connection.execute.return_value.fetchone.return_value = None  # Simulate not found
    mocker.patch('app.services.movie_data_service.create_engine', return_value=mock_engine)
    mocker.patch('app.services.movie_data_service.MovieDataService._verify_enhanced_links_table')
    service = MovieDataService()

    # Act
    result = service.get_raw_movie_id_from_imdb_id('tt00000')

    # Assert
    assert result is None
    assert service._mapping_stats['misses'] == 1
    assert service._mapping_stats['total_requests'] == 1


def test_get_raw_movie_id_from_imdb_id_db_error(mocker, mock_db_engine):
    """Tests that the service handles a database error during lookup."""
    # Arrange
    mock_engine, mock_connection = mock_db_engine
    mock_connection.execute.side_effect = Exception("Database connection error")
    mocker.patch('app.services.movie_data_service.create_engine', return_value=mock_engine)
    mocker.patch('app.services.movie_data_service.MovieDataService._verify_enhanced_links_table')
    mock_logger_error = mocker.patch('app.services.movie_data_service.logger.error')
    service = MovieDataService()

    # Act
    result = service.get_raw_movie_id_from_imdb_id('tt12345')

    # Assert
    assert result is None
    assert service._mapping_stats['errors'] == 1
    assert service._mapping_stats['total_requests'] == 1
    mock_logger_error.assert_called_once()


def test_get_imdb_ids_from_raw_ids_success(mocker, mock_db_engine):
    """Tests successful conversion of raw IDs to IMDb IDs."""
    # Arrange
    mock_engine, mock_connection = mock_db_engine
    
    # Simulate different return values for different inputs
    def execute_side_effect(*args, **kwargs):
        mock_result = MagicMock()
        # The parameters are in the second argument of the execute call
        params = args[1]
        if params.get('movie_id') == '101':
            mock_result.fetchone.return_value = ('11111',)
        elif params.get('movie_id') == '103':
            mock_result.fetchone.return_value = ('33333',)
        else:
            mock_result.fetchone.return_value = None
        return mock_result

    mock_connection.execute.side_effect = execute_side_effect
    mocker.patch('app.services.movie_data_service.create_engine', return_value=mock_engine)
    mocker.patch('app.services.movie_data_service.MovieDataService._verify_enhanced_links_table')
    service = MovieDataService()

    # Act
    result = service.get_imdb_ids_from_raw_ids(['101', 'tt22222', '103'])

    # Assert
    assert result == ['tt11111', 'tt22222', 'tt33333']
