import logging # Added for basicConfig
from fastapi import FastAPI, HTTPException
from typing import List, Dict

logging.basicConfig(level=logging.INFO) # Set default logging level to INFO
logger = logging.getLogger(__name__)
import asyncio # Added for asyncio.gather

import os
import httpx
from .services.unified_recommender_service import UnifiedRecommenderService
from .schemas import RecommendationResponse, MovieSearchResponse, ProfileRecommendationRequest, ProfileRecommendationResponse
from .core.config import settings
import asyncio
from fastapi.concurrency import run_in_threadpool

app = FastAPI(
    title="Movie Recommender API",
    description="API for a movie recommender system using collaborative filtering and OMDb for search.",
    version="0.1.0",
)

# Initialize Unified Recommender Service for recommendations
logger.info("Initializing Unified Recommender Service for API...")
recommender = UnifiedRecommenderService()
logger.info("Unified Recommender Service will use direct, enhanced, and model-based ID mappings.")

@app.on_event("startup")
async def startup_event():
    """Load the model on startup in a non-blocking background task."""
    logger.info("Application startup: Creating background task for model loading.")
    asyncio.create_task(run_in_threadpool(recommender.load_model))

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
            # Step 1: Perform the initial search
            search_response = await client.get(search_url)
            search_response.raise_for_status()
            search_data = search_response.json()

            if search_data.get("Response") != "True":
                return []

            search_results = search_data.get("Search", [])

            # Step 2: Fetch detailed information for each search result concurrently
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

            # Filter out any None results from failed detail fetches
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
        # Use run_in_threadpool to avoid blocking the event loop
        # This returns a tuple of (list of IMDb IDs, message)
        recommendation_ids, message = await run_in_threadpool(
            recommender.get_recommendations_for_profile,
            request.imdb_ids,
            n=n
        )

        # If no IDs were recommended (e.g., fallback), return an empty list
        if not recommendation_ids:
            logger.info("No recommendation IDs returned from service, returning empty list.")
            return {"recommendations": [], "message": message}

        # Fetch full movie details for the recommended IDs to satisfy the response model
        logger.info(f"Fetching details for {len(recommendation_ids)} recommended movie IDs.")
        recommendations_details = await recommender.get_movie_details_by_ids(recommendation_ids)
        logger.info(f"Successfully fetched details for {len(recommendations_details)} movies.")

        return {"recommendations": recommendations_details, "message": message}
    except Exception as e:
        logger.error(f"Error getting profile recommendations: {e}")
        logger.exception("An exception occurred during profile recommendation generation:")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations.")


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


