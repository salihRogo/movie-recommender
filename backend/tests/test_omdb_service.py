import pytest
import httpx
from unittest.mock import AsyncMock

from app.services.omdb_service import OmdbService

@pytest.mark.asyncio
async def test_search_movies_by_title_success(mocker):
    """Tests successful movie search and detail fetching using the OmdbService class."""
    search_query = "Inception"
    
    # Mock response for the initial search by title
    mock_search_response = {
        "Search": [
            {"imdbID": "tt1375666", "Title": "Inception", "Year": "2010", "Type": "movie"},
        ],
        "totalResults": "1",
        "Response": "True"
    }
    
    # Mock response for the detailed fetch by IMDb ID
    mock_detail_response = {
        "Title": "Inception",
        "Year": "2010",
        "imdbID": "tt1375666",
        "imdbRating": "8.8",
        "Plot": "A thief who steals corporate secrets...",
        "Actors": "Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page",
        "Poster": "http://example.com/poster.jpg",
        "Genre": "Action, Adventure, Sci-Fi",
        "Response": "True"
    }

    # We patch httpx.AsyncClient to control its behavior within the 'async with' block.
    # The mock for the client instance itself is what needs the 'get' method.
    mock_client_instance = mocker.patch('httpx.AsyncClient').return_value
    # Create a mock response that includes a request object to satisfy 'raise_for_status()'
    mock_response = httpx.Response(
        200, 
        json=mock_search_response, 
        request=httpx.Request("GET", "http://example.com")
    )
    mock_client_instance.__aenter__.return_value.get.return_value = mock_response

    # Mock the internal call to get_movie_details_by_ids to isolate the test
    mock_get_details = mocker.patch.object(
        OmdbService, 
        'get_movie_details_by_ids', 
        new_callable=AsyncMock,
        return_value=[mock_detail_response] # Return the detailed movie dict
    )

    # Instantiate the service and call the method
    service = OmdbService()
    results = await service.search_movies_by_title(search_query)

    # Assertions
    assert len(results) == 1
    movie = results[0]
    assert movie['Title'] == "Inception"
    assert movie['imdbID'] == "tt1375666"
    assert movie['imdbRating'] == "8.8"

    # Verify that the initial search call was made
    mock_client_instance.__aenter__.return_value.get.assert_called_once()
    search_call_params = mock_client_instance.__aenter__.return_value.get.call_args.kwargs['params']
    assert search_call_params['s'] == search_query

    # Verify that the internal get_movie_details_by_ids method was called
    mock_get_details.assert_awaited_once_with(['tt1375666'])


@pytest.mark.asyncio
async def test_get_movie_details_by_ids(mocker):
    """Tests fetching details for multiple IMDb IDs by mocking httpx.AsyncClient."""
    # 1. Arrange
    service = OmdbService()
    imdb_ids = ["tt0111161", "tt0068646"]

    mock_shawshank_data = {
        "Title": "The Shawshank Redemption",
        "Year": "1994",
        "imdbID": "tt0111161",
        "Genre": "Drama",
        "Actors": "Tim Robbins, Morgan Freeman",
        "Plot": "Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.",
        "Poster": "https://some-url/shawshank.jpg",
        "imdbRating": "9.3",
        "Response": "True",
    }
    mock_godfather_data = {
        "Title": "The Godfather",
        "Year": "1972",
        "imdbID": "tt0068646",
        "Genre": "Crime, Drama",
        "Actors": "Marlon Brando, Al Pacino",
        "Plot": "The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.",
        "Poster": "https://some-url/godfather.jpg",
        "imdbRating": "9.2",
        "Response": "True",
    }

    # This side effect inspects the call and returns the correct mock response
    def get_side_effect(url, params):
        mock_response = mocker.Mock()
        mock_response.raise_for_status = mocker.Mock()
        imdb_id = params.get("i")
        if imdb_id == "tt0111161":
            mock_response.json.return_value = mock_shawshank_data
        elif imdb_id == "tt0068646":
            mock_response.json.return_value = mock_godfather_data
        else:
            mock_response.json.return_value = {"Response": "False", "Error": "Not Found"}
        return mock_response

    # This mock will be returned by the 'async with' context manager
    mock_client_instance = mocker.AsyncMock()
    mock_client_instance.get.side_effect = get_side_effect

    # Patch the httpx.AsyncClient class
    mock_client_class = mocker.patch("httpx.AsyncClient")
    # Ensure the instance returned by the context manager is our mock
    mock_client_class.return_value.__aenter__.return_value = mock_client_instance

    # 2. Act
    results = await service.get_movie_details_by_ids(imdb_ids)

    # 3. Assert
    assert len(results) == 2

    # Sort results to have a predictable order for assertions
    results.sort(key=lambda x: x["imdb_id"])

    # Check Shawshank Redemption data
    assert results[1]["title"] == "The Shawshank Redemption"
    assert results[1]["imdb_id"] == "tt0111161"
    assert results[1]["year"] == "1994"
    assert results[1]["imdbRating"] == "9.3"

    # Check Godfather data
    assert results[0]["title"] == "The Godfather"
    assert results[0]["imdb_id"] == "tt0068646"
    assert results[0]["year"] == "1972"
    assert results[0]["imdbRating"] == "9.2"

    # Verify that the HTTP client was called for each ID
    assert mock_client_instance.get.call_count == 2

