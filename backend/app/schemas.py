from pydantic import BaseModel
from typing import List, Dict, Any

from pydantic import BaseModel, Field # Import Field
from typing import List, Dict, Any

class MovieSearchResult(BaseModel):
    imdb_id: str = Field(..., alias='imdbID')
    title: str = Field(..., alias='Title')
    year: str = Field(..., alias='Year')
    # We can also add other fields from OMDb if needed, e.g., poster
    # poster: Optional[str] = Field(None, alias='Poster')

class MovieSearchResponse(BaseModel):
    results: List[MovieSearchResult]

class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[Dict[str, Any]]
    message: str

class ProfileRecommendationRequest(BaseModel):
    imdb_ids: List[str]

class ProfileRecommendationResponse(BaseModel):
    recommendations: List[Dict[str, Any]]
    message: str = ""
