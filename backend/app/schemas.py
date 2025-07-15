from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional



class MovieDetail(BaseModel):
    """Schema for detailed movie information from OMDb."""
    imdb_id: str
    title: str
    year: str
    poster_url: Optional[str] = None
    genres: Optional[str] = None
    plot: Optional[str] = None
    actors: Optional[str] = None
    imdbRating: Optional[str] = None

    class Config:
        from_attributes = True # Allows creating from ORM models or dicts

class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[MovieDetail]
    message: str

class ProfileRecommendationRequest(BaseModel):
    imdb_ids: List[str]

class ProfileRecommendationResponse(BaseModel):
    recommendations: List[MovieDetail]
    message: str = ""
