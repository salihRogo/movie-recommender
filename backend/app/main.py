import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from app.recommender import MovieRecommender

# Initialize FastAPI app
app = FastAPI(
    title="Movie Recommender API",
    description="API for movie recommendations using collaborative filtering",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize recommender system
recommender = MovieRecommender()
current_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(current_dir, "data")

@app.on_event("startup")
async def startup_event():
    """Initialize data on startup"""
    recommender.initialize(
        os.path.join(data_dir, "ratings.csv"),
        os.path.join(data_dir, "movies.csv")
    )
    print("Recommender system initialized successfully")

# Define data models
class Movie(BaseModel):
    id: int
    title: str
    genres: Optional[str] = None
    
class MovieRecommendation(BaseModel):
    id: int
    title: str
    genres: Optional[str] = None
    
class MovieList(BaseModel):
    movies: List[Movie]

# API endpoints
@app.get("/")
async def root():
    return {"message": "Movie Recommender API is running"}

@app.get("/movies/search/{title}", response_model=List[Movie])
async def search_movies(title: str):
    """Search for movies by title"""
    results = recommender.get_movie_by_title(title)
    if not results:
        return []
    # Map movieId to id for the response model
    return [{"id": movie["movieId"], "title": movie["title"], "genres": movie.get("genres")} for movie in results]

@app.get("/movies/popular", response_model=List[MovieRecommendation])
async def get_popular_movies(limit: int = 10):
    """Get popular movies"""
    return recommender.get_popular_movies(limit)

@app.get("/recommendations/movie/{movie_id}", response_model=List[MovieRecommendation])
async def get_movie_recommendations(movie_id: int, limit: int = 10):
    """Get movie recommendations based on a movie ID"""
    recommendations = recommender.get_recommendations(movie_id, limit)
    if not recommendations:
        raise HTTPException(status_code=404, detail=f"Movie ID {movie_id} not found or no recommendations available")
    return recommendations

@app.get("/recommendations/user/{user_id}", response_model=List[MovieRecommendation])
async def get_user_recommendations(user_id: int, limit: int = 10):
    """Get movie recommendations for a user"""
    recommendations = recommender.recommend_movies_for_user(user_id, limit)
    if not recommendations:
        raise HTTPException(status_code=404, detail=f"User ID {user_id} not found or no recommendations available")
    return recommendations

# Run the app if executed directly
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)