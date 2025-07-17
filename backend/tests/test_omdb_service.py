import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.omdb_service import OmdbService


@pytest.fixture
def service():
    """Provides an instance of the OmdbService."""
    return OmdbService()


@pytest.mark.asyncio
async def test_search_movies_by_title_success(mocker, service):
    """Tests successful movie search by mocking the underlying HTTP calls."""
    # Arrange
    search_query = "Inception"
    mock_search_response_json = {
        "Search": [{"imdbID": "tt1375666"}],
        "Response": "True"
    }
    mock_details_result = [{
        "imdb_id": "tt1375666",
        "title": "Inception",
        "year": "2010",
        "imdbRating": "8.8"
    }]

    # Mock the initial search call
    mock_response = MagicMock()
    mock_response.json.return_value = mock_search_response_json
    mock_async_client = mocker.patch('httpx.AsyncClient').return_value
    mock_async_client.__aenter__.return_value.get.return_value = mock_response

    # Mock the subsequent call to get details
    mocker.patch.object(service, 'get_movie_details_by_ids', new_callable=AsyncMock, return_value=mock_details_result)

    # Act
    results = await service.search_movies_by_title(search_query)

    # Assert
    assert len(results) == 1
    assert results[0]['title'] == "Inception"
    service.get_movie_details_by_ids.assert_awaited_once_with(['tt1375666'])


@pytest.mark.asyncio
async def test_get_movie_details_by_ids(mocker, service):
    """Tests fetching details for multiple IMDb IDs by mocking the helper method."""
    # Arrange
    imdb_ids = ["tt0111161", "tt0068646"]
    mock_shawshank = {"imdb_id": "tt0111161", "title": "Shawshank"}
    mock_godfather = {"imdb_id": "tt0068646", "title": "Godfather"}

    async def side_effect(client, imdb_id):
        if imdb_id == "tt0111161":
            return mock_shawshank
        if imdb_id == "tt0068646":
            return mock_godfather
        return None

    mocker.patch.object(service, '_get_movie_details_by_imdb_id', side_effect=side_effect)

    # Act
    results = await service.get_movie_details_by_ids(imdb_ids)

    # Assert
    assert len(results) == 2
    assert service._get_movie_details_by_imdb_id.call_count == 2
    # Ensure results match mock data, order doesn't matter
    result_titles = {r['title'] for r in results}
    assert result_titles == {"Shawshank", "Godfather"}


@pytest.mark.asyncio
async def test_search_movies_no_api_key(monkeypatch, service):
    """Tests that search returns an empty list if API key is not set."""
    # Arrange
    monkeypatch.setattr("app.core.config.settings.OMDB_API_KEY", None)

    # Act
    results = await service.search_movies_by_title("any title")

    # Assert
    assert results == []


@pytest.mark.asyncio
async def test_get_details_no_api_key(monkeypatch, service):
    """Tests that get_details returns an empty list if API key is not set."""
    # Arrange
    monkeypatch.setattr("app.core.config.settings.OMDB_API_KEY", None)

    # Act
    results = await service.get_movie_details_by_ids(["tt0111161"])

    # Assert
    assert results == []


@pytest.mark.asyncio
async def test_get_movie_details_by_imdb_id_success(mocker, service):
    """Tests successful detail fetching for a single IMDb ID."""
    # Arrange
    imdb_id = "tt0111161"
    mock_api_response = {
        "Title": "The Shawshank Redemption",
        "Year": "1994",
        "imdbRating": "9.3",
        "imdbID": imdb_id,
        "Response": "True"
    }
    expected_result = {
        'title': 'The Shawshank Redemption',
        'year': '1994',
        'imdbRating': '9.3',
        'imdb_id': imdb_id,
        'poster_url': None,
        'genres': None,
        'plot': None,
        'actors': None,
        'imdbVotes': None
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response

    mock_get = AsyncMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.get = mock_get

    # Act
    result = await service._get_movie_details_by_imdb_id(mock_client, imdb_id)

    # Assert
    assert result == expected_result
    mock_get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_movie_details_by_imdb_id_not_found(mocker, service):
    """Tests detail fetching when the movie is not found by the API."""
    # Arrange
    imdb_id = "tt9999999"
    mock_api_response = {"Response": "False", "Error": "Movie not found!"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response
    mock_get = AsyncMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.get = mock_get

    # Act
    result = await service._get_movie_details_by_imdb_id(mock_client, imdb_id)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_movie_details_by_imdb_id_http_error(mocker, service):
    """Tests detail fetching when the API returns an HTTP error."""
    # Arrange
    imdb_id = "tt0111161"
    mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=MagicMock(status_code=500)
    ))
    mock_client = MagicMock()
    mock_client.get = mock_get

    # Act
    result = await service._get_movie_details_by_imdb_id(mock_client, imdb_id)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_movie_details_by_imdb_id_json_error(mocker, service):
    """Tests detail fetching when the API returns invalid JSON."""
    # Arrange
    imdb_id = "tt0111161"
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_get = AsyncMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.get = mock_get

    # Act
    result = await service._get_movie_details_by_imdb_id(mock_client, imdb_id)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_search_movies_by_title_api_error(mocker, service):
    """Tests movie search when the API returns an error message."""
    # Arrange
    mock_api_response = {"Response": "False", "Error": "Too many results."}
    mock_response = MagicMock()
    mock_response.json.return_value = mock_api_response
    mock_async_client = mocker.patch('httpx.AsyncClient').return_value
    mock_async_client.__aenter__.return_value.get.return_value = mock_response

    # Act
    results = await service.search_movies_by_title("Star Wars")

    # Assert
    assert results == []


@pytest.mark.asyncio
async def test_search_movies_by_title_request_error(mocker, service):
    """Tests movie search when an httpx.RequestError occurs."""
    # Arrange
    mocker.patch(
        'httpx.AsyncClient.__aenter__',
        side_effect=httpx.RequestError("Network error", request=MagicMock())
    )

    # Act
    results = await service.search_movies_by_title("any")

    # Assert
    assert results == []


@pytest.mark.asyncio
async def test_search_movies_by_title_unexpected_error(mocker, service):
    """Tests movie search when a generic Exception occurs."""
    # Arrange
    mocker.patch(
        'httpx.AsyncClient.__aenter__',
        side_effect=Exception("Something broke")
    )

    # Act
    results = await service.search_movies_by_title("any")

    # Assert
    assert results == []
