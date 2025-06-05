from fastapi import FastAPI, HTTPException
from typing import List, Dict
import asyncio # Added for asyncio.gather

from app.services.recommender_service import RecommenderService
from app.schemas import RecommendationResponse
from app.core.config import settings

app = FastAPI(
    title="Movie Recommender API",
    description="API for a movie recommender system using collaborative filtering.",
    version="0.1.0",
)

# Initialize Recommender Service
# Using a smaller sample for quicker API startup during development, can be configured.
# Set force_retrain=False to load model if available, True to always retrain on startup.
print("Initializing Recommender Service for API...")
recommender = RecommenderService()
print("Recommender Service initialized.")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Movie Recommender API!"}


@app.get("/recommendations/{user_id}", response_model=RecommendationResponse)
async def get_movie_recommendations(user_id: int, n: int = 10):
    """
    Get top N movie recommendations for a given user_id.
    - **user_id**: The ID of the user for whom to generate recommendations.
    - **n**: The number of recommendations to return (default: 10).
    """
    recommendations_imdb_ids, rec_type = recommender.get_recommendations(user_id, n=n)
    
    movie_details_list = []
    message = ""

    if recommendations_imdb_ids:
        # Fetch details for all recommended IMDb IDs concurrently
        detail_tasks = [recommender.get_movie_details_by_imdb_id(imdb_id) for imdb_id in recommendations_imdb_ids]
        movie_details_results = await asyncio.gather(*detail_tasks)
        
        # Filter out any errors and keep successful details
        for details in movie_details_results:
            if not details.get("Error"):
                movie_details_list.append(details)
            else:
                # Log or handle movies that couldn't be fetched, if necessary
                print(f"Could not fetch details for IMDb ID {details.get('imdbID', 'unknown')}: {details.get('Error')}")

    # Construct messages based on recommendation type
    if rec_type == "personalized":
        message = f"Personalized recommendations successfully retrieved for user {user_id}."
        if len(movie_details_list) < len(recommendations_imdb_ids):
            message += " Some movie details could not be fetched."
    elif rec_type == "popular_fallback_unknown_user":
        message = f"User {user_id} is unknown. Showing generally popular movies as a fallback."
    elif rec_type == "popular_fallback_no_personalized":
        message = f"Could not generate personalized recommendations for user {user_id}. Showing generally popular movies as a fallback."
    elif rec_type == "popular_fallback_model_unavailable":
        message = "Personalized recommendation model is currently unavailable. Showing generally popular movies as a fallback."
    elif rec_type == "error_model_not_ready_no_fallback":
        message = "Recommender model not ready and no fallback recommendations available."
        return RecommendationResponse(user_id=user_id, recommendations=[], message=message)
    elif rec_type.startswith("error_"):
        message = f"An error occurred while generating recommendations for user {user_id} ({rec_type})."
        if not movie_details_list and not recommendations_imdb_ids:
             message += " No fallback recommendations are available."
        elif not movie_details_list and recommendations_imdb_ids:
            message += " Fallback IMDb IDs were found, but their details could not be fetched."
        elif movie_details_list:
            message += " Fallback popular movies provided."
        return RecommendationResponse(user_id=user_id, recommendations=movie_details_list, message=message)

    if not movie_details_list and recommendations_imdb_ids: # Had IDs but couldn't fetch details
        message += " However, details for the recommended movies could not be fetched."
    elif not movie_details_list and not recommendations_imdb_ids and not rec_type.startswith("error_"):
        message += " However, no fallback recommendations could be provided at this time."

    return RecommendationResponse(user_id=user_id, recommendations=movie_details_list, message=message)

# Placeholder for future development
# To run this app directly for development:
# cd backend
# python -m uvicorn app.main:app --reload
