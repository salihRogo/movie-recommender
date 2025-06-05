from pydantic import BaseModel
from typing import List, Dict

class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[Dict] # List of movie detail dictionaries
    message: str = ""
