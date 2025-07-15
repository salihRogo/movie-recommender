import logging # Added for basicConfig
from fastapi import FastAPI, HTTPException
from typing import List, Dict

logging.basicConfig(level=logging.INFO) # Set default logging level to INFO
logger = logging.getLogger(__name__)
import asyncio # Added for asyncio.gather
from contextlib import asynccontextmanager
import os
import httpx
from .services.recommender_service import RecommenderService
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

# Initialize Recommender Service, which orchestrates the other services
logger.info("Initializing Recommender Service for API...")
recommender = RecommenderService()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Movie Recommender API!"}

@app.get("/search", response_model=List[Dict])
async def search_movies(movie_title: str):
    """
    Search for movies by title using the OMDb API.
    - **movie_title**: The search query for the movie title.
    """
    try:
        search_results = await recommender.omdb_service.search_movies_by_title(movie_title)
        return search_results
    except Exception as e:
        logger.error(f"An unexpected error occurred during movie search: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred during movie search.")


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

        recommendations_details = await recommender.omdb_service.get_movie_details_by_ids(recommendation_ids)

        return {"recommendations": recommendations_details, "message": message}
    except Exception as e:
        logger.error(f"Error getting profile recommendations: {e}")
        logger.exception("An exception occurred during profile recommendation generation:")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations.")
