import logging # Added for basicConfig
from fastapi import FastAPI, HTTPException
from typing import List, Dict

logging.basicConfig(level=logging.INFO) # Set default logging level to INFO
logger = logging.getLogger(__name__)
import asyncio # Added for asyncio.gather
from contextlib import asynccontextmanager
import os
import httpx
from .services.unified_recommender_service import UnifiedRecommenderService
from .schemas import RecommendationResponse, MovieSearchResponse, ProfileRecommendationRequest, ProfileRecommendationResponse
from .core.config import settings
import asyncio
from fastapi.concurrency import run_in_threadpool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    asyncio.create_task(run_in_threadpool(recommender.load_model))
    yield
    logger.info("Application shutdown.")

app = FastAPI(
    lifespan=lifespan,
    title="Movie Recommender API",
    description="API for a movie recommender system using collaborative filtering and OMDb for search.",
    version="0.1.0",
)

# Initialize Unified Recommender Service for recommendations
logger.info("Initializing Unified Recommender Service for API...")
recommender = UnifiedRecommenderService()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Movie Recommender API!"}

@app.get("/search")
async def search_movies(movie_title: str):
    """
    Search for movies by title using the OMDb API and enrich results with details.
    - **movie_title**: The search query for the movie title.
    """
    api_key = settings.OMDB_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="OMDb API key not configured.")

    search_url = f"http://www.omdbapi.com/?s={movie_title}&apikey={api_key}&type=movie"

    async with httpx.AsyncClient() as client:
        try:
            search_response = await client.get(search_url)
            search_response.raise_for_status()
            search_data = search_response.json()

            if search_data.get("Response") != "True":
                return []

            search_results = search_data.get("Search", [])

            async def get_details(imdb_id: str):
                details_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={api_key}"
                try:
                    details_response = await client.get(details_url)
                    details_response.raise_for_status()
                    details_data = details_response.json()
                    if details_data.get("Response") == "True":
                        return details_data
                except httpx.RequestError as exc:
                    logger.error(f"Error fetching details for {imdb_id}: {exc}")
                return None

            tasks = [get_details(movie["imdbID"]) for movie in search_results]
            detailed_results = await asyncio.gather(*tasks)

            return [result for result in detailed_results if result]

        except httpx.RequestError as exc:
            logger.error(f"An error occurred while requesting {exc.request.url!r}: {exc}")
            raise HTTPException(status_code=503, detail="Error communicating with OMDb API.")
        except Exception as exc:
            logger.error(f"An unexpected error occurred during movie search: {exc}")
            raise HTTPException(status_code=500, detail="An internal error occurred.")


@app.post("/recommendations/by_profile", response_model=ProfileRecommendationResponse)
async def get_profile_recommendations(request: ProfileRecommendationRequest, n: int = 10):
    """
    Get movie recommendations based on a list of liked IMDb IDs.
    - **request**: A list of IMDb IDs for movies the user likes.
    - **n**: The number of recommendations to return.
    """
    try:
        recommendation_ids, message = await run_in_threadpool(
            recommender.get_recommendations_for_profile,
            request.imdb_ids,
            n=n
        )

        if not recommendation_ids:
            logger.info("No recommendation IDs returned from service, returning empty list.")
            return {"recommendations": [], "message": message}

        recommendations_details = await recommender.get_movie_details_by_ids(recommendation_ids)

        return {"recommendations": recommendations_details, "message": message}
    except Exception as e:
        logger.error(f"Error getting profile recommendations: {e}")
        logger.exception("An exception occurred during profile recommendation generation:")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations.")
