import logging # Added for basicConfig
from fastapi import FastAPI, HTTPException
from typing import List, Dict

logging.basicConfig(level=logging.INFO) # Set default logging level to INFO
logger = logging.getLogger(__name__)
import asyncio # Added for asyncio.gather

from .services.unified_recommender_service import UnifiedRecommenderService
from .schemas import RecommendationResponse, MovieSearchResponse, ProfileRecommendationRequest, ProfileRecommendationResponse
from .core.config import settings
import asyncio
from fastapi.concurrency import run_in_threadpool

app = FastAPI(
    title="Movie Recommender API",
    description="API for a movie recommender system using collaborative filtering.",
    version="0.1.0",
)

# Initialize Unified Recommender Service which combines the best features from both implementations
logger.info("Initializing Unified Recommender Service for API...")
recommender = UnifiedRecommenderService()
logger.info("Unified Recommender Service will use direct, enhanced, and model-based ID mappings.")

@app.on_event("startup")
async def startup_event():
    """Load the model on startup in a non-blocking background task."""
    print("Application startup: Creating background task for model loading...")
    # Run the synchronous `load_model` in a thread pool to avoid blocking the event loop
    asyncio.create_task(run_in_threadpool(recommender.load_model))
    print("Application startup: Model loading task is running in the background.")
print("Recommender Service initialized.")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Movie Recommender API!"}


@app.get("/movies/search", response_model=MovieSearchResponse)
async def search_movies(title: str):
    """
    Search for movies by title.
    - **title**: The search query for the movie title.
    """
    search_results = await recommender.search_movies_by_title(title)
    return MovieSearchResponse(results=search_results)


@app.post("/recommendations/by_profile", response_model=ProfileRecommendationResponse)
async def get_profile_recommendations(request: ProfileRecommendationRequest, n: int = 10):
    """
    Generate movie recommendations based on a list of liked movies.
    - **imdb_ids**: A list of IMDb IDs for the movies the user likes.
    """
    recommended_imdb_ids, base_message = recommender.get_recommendations_for_profile(request.imdb_ids, n)
    
    movie_details_list = []
    final_message = base_message

    if recommended_imdb_ids:
        # Fetch details for all recommended IMDb IDs concurrently
        detail_tasks = [recommender.get_movie_details_by_imdb_id(imdb_id) for imdb_id in recommended_imdb_ids]
        movie_details_results = await asyncio.gather(*detail_tasks)
        
        # Filter out any errors and keep successful details
        for details in movie_details_results:
            if not details.get("Error"):
                movie_details_list.append(details)
            else:
                logger.warning(f"Could not fetch details for IMDb ID {details.get('imdbID', 'unknown')} from profile recommendations: {details.get('Error')}")

        if len(movie_details_list) < len(recommended_imdb_ids):
            final_message += " Some movie details could not be fetched."
    elif not base_message: # If base_message was empty and no IDs, means something unexpected
        final_message = "Could not generate recommendations based on the provided profile."

    if not movie_details_list and recommended_imdb_ids: # Had IDs but couldn't fetch details
        final_message += " However, details for the recommended movies could not be fetched."
    
    return ProfileRecommendationResponse(recommendations=movie_details_list, message=final_message)


@app.get("/recommendations/{user_id}", response_model=RecommendationResponse)
async def get_movie_recommendations(user_id: int, n: int = 10):
    """
    Get top N movie recommendations for a given user_id.
    - **user_id**: The ID of the user for whom to generate recommendations.
    - **n**: The number of recommendations to return (default: 10).
    """
    recommendations_imdb_ids, rec_type, base_message = recommender.get_recommendations(user_id, n=n)
    
    movie_details_list = []
    final_message = base_message # Start with the message from the service

    if recommendations_imdb_ids:
        # Fetch details for all recommended IMDb IDs concurrently
        detail_tasks = [recommender.get_movie_details_by_imdb_id(imdb_id) for imdb_id in recommendations_imdb_ids]
        movie_details_results = await asyncio.gather(*detail_tasks)
        
        # Filter out any errors and keep successful details
        for details in movie_details_results:
            if not details.get("Error"):
                movie_details_list.append(details)
            else:
                logger.warning(f"Could not fetch details for IMDb ID {details.get('imdbID', 'unknown')} for user {user_id}: {details.get('Error')}")

        if len(movie_details_list) < len(recommendations_imdb_ids):
            if final_message: # Append to existing message
                final_message += " However, some movie details could not be fetched."
            else: # Should not happen if service returns base_message, but as a fallback
                final_message = "Recommendations were found, but some movie details could not be fetched."
    
    # If no recommendations were found by the service AND no details were fetched, 
    # the base_message from the service should already cover this.
    # Example: if rec_type indicated an error and popular_fallback_ids was empty.

    # Additional check: if we had IDs but fetched no details at all.
    if recommendations_imdb_ids and not movie_details_list:
        if final_message: 
            final_message += " Additionally, no details for any recommended movies could be fetched."
        else: # Fallback if base_message was somehow empty
            final_message = "Recommendations found, but no movie details could be fetched."
    
    # If the service indicated an error and returned no IDs, the base_message should suffice.
    # If no recommendations (empty list) and no error, base_message should also cover this.
    if not recommendations_imdb_ids and not movie_details_list and not rec_type.startswith("error_") and not final_message:
        final_message = f"No recommendations could be provided for user {user_id} at this time."

    return RecommendationResponse(user_id=user_id, recommendations=movie_details_list, message=final_message)


# Placeholder for future development
# To run this app directly for development:
# cd backend
# python -m uvicorn app.main:app --reload


