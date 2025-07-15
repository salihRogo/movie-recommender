import logging
from typing import List, Dict, Any, Optional
import httpx
import asyncio

from ..core.config import settings

logger = logging.getLogger(__name__)


class OmdbService:
    """Service for interacting with the OMDb API."""

    async def _get_movie_details_by_imdb_id(
        self,
        client: httpx.AsyncClient, 
        imdb_id: str
    ) -> Optional[Dict[str, Any]]:
        """Helper to fetch details for a single IMDb ID."""
        base_url = settings.OMDB_API_BASE_URL or "http://www.omdbapi.com/"
        params = {"i": imdb_id, "apikey": settings.OMDB_API_KEY}
        try:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("Response") == "True":
                return {
                    "imdb_id": data.get("imdbID"),
                    "title": data.get("Title"),
                    "year": data.get("Year"),
                    "poster_url": data.get("Poster"),
                    "genres": data.get("Genre"),
                    "plot": data.get("Plot"),
                    "actors": data.get("Actors"),
                    "imdbRating": data.get("imdbRating"),
                }
            else:
                logger.warning(f"OMDb API returned an error for IMDb ID {imdb_id}: {data.get('Error')}")
                return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching details for IMDb ID {imdb_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching details for IMDb ID {imdb_id}: {e}")
            return None

    async def get_movie_details_by_ids(self, imdb_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch full movie details for a list of IMDb IDs concurrently."""
        if not settings.OMDB_API_KEY:
            logger.error("OMDB_API_KEY not configured. Cannot fetch movie details.")
            return []

        timeout = httpx.Timeout(10.0, connect=3.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            tasks = [self._get_movie_details_by_imdb_id(client, imdb_id) for imdb_id in imdb_ids]
            results = await asyncio.gather(*tasks)
        
        return [result for result in results if result is not None]

    async def search_movies_by_title(self, title: str) -> List[Dict[str, Any]]:
        """Search for movies by title using the OMDb API."""
        logger.info(f"Searching OMDb API for movies with title: '{title}'")

        if not settings.OMDB_API_KEY:
            logger.error("OMDB_API_KEY not configured. Cannot search for movies.")
            return []

        base_url = settings.OMDB_API_BASE_URL or "http://www.omdbapi.com/"
        params = {
            "s": title,
            "apikey": settings.OMDB_API_KEY,
            "type": "movie"
        }

        try:
            timeout = httpx.Timeout(10.0, connect=3.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("Response") == "True":
                search_results = data.get("Search", [])
                imdb_ids = [movie["imdbID"] for movie in search_results if "imdbID" in movie]
                logger.info(f"Found {len(imdb_ids)} results from OMDb for '{title}', now fetching full details.")
                
                # Fetch full details to include actors, plot, etc.
                detailed_results = await self.get_movie_details_by_ids(imdb_ids)
                return detailed_results
            else:
                error_message = data.get("Error", "Unknown error from OMDb API.")
                logger.warning(f"OMDb API returned an error for title '{title}': {error_message}")
                return []

        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting from OMDb API: {e}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred during movie search: {e}")
            return []
