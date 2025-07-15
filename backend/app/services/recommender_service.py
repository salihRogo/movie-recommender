"""Core Movie Recommender Service

This module contains the core logic for generating movie recommendations.
It uses a pre-trained SVD model and delegates external communications
to specialized services for OMDb API and database interactions.
"""

import logging
from typing import List, Dict, Tuple, Optional
import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from functools import lru_cache
from ..core.config import MODELS_DIR
from .omdb_service import OmdbService
from .movie_data_service import MovieDataService

logger = logging.getLogger(__name__)


class RecommenderService:
    """Orchestrates recommendation logic by coordinating with other services."""

    def __init__(self):
        """Initialize the recommender service and its dependencies."""
        self.model_loaded = False
        self.raw_to_inner_iid_map: Dict[str, int] = {}
        self.inner_to_raw_iid_map: Dict[int, str] = {}
        self.popular_movie_ids_fallback: List[str] = []
        self.qi: Optional[np.ndarray] = None  # Item vectors

        self.popular_movies_file = MODELS_DIR / "popular_movies_fallback.joblib"

        self.omdb_service = OmdbService()
        self.movie_data_service = MovieDataService()

    def load_model(self):
        """Loads the individual model components from disk."""
        logger.info("Attempting to load model components and popular movies...")
        try:
            model_components_path = MODELS_DIR / "svd_model_components.joblib"
            raw_to_inner_map_path = MODELS_DIR / "raw_to_inner_iid_map.joblib"

            if model_components_path.exists() and raw_to_inner_map_path.exists():
                model_components = joblib.load(model_components_path)
                self.qi = model_components['qi']
                
                self.raw_to_inner_iid_map = joblib.load(raw_to_inner_map_path)
                self.inner_to_raw_iid_map = {v: k for k, v in self.raw_to_inner_iid_map.items()}
                
                self.model_loaded = True
                logger.info(f"SVD model components loaded successfully. Item vectors shape: {self.qi.shape}")
            else:
                logger.warning(f"One or more model component files not found in {MODELS_DIR}. Recommendations will be disabled.")

            if self.popular_movies_file.exists():
                self.popular_movie_ids_fallback = joblib.load(self.popular_movies_file)
                logger.info(f"Loaded {len(self.popular_movie_ids_fallback)} popular movies from cache.")
            else:
                logger.warning("Popular movies cache not found. Using empty fallback.")

        except Exception as e:
            logger.error(f"A critical error occurred during model loading: {e}", exc_info=True)
            self.model_loaded = False

    def get_recommendations_for_profile(
        self, imdb_ids: List[str], n: int = 10
    ) -> Tuple[List[str], str]:
        """Generate recommendations based on a list of liked IMDb IDs."""
        if not self.model_loaded or self.qi is None:
            logger.warning("Model not loaded, returning popular movie fallback.")
            return self.popular_movie_ids_fallback[:n], "Recommender model is loading. Popular movies returned."

        mapped_raw_ids = []
        for imdb_id in imdb_ids:
            if imdb_id in self.raw_to_inner_iid_map:
                mapped_raw_ids.append(imdb_id)
            else:
                raw_id = self.movie_data_service.get_raw_movie_id_from_imdb_id(imdb_id)
                if raw_id and raw_id in self.raw_to_inner_iid_map:
                    mapped_raw_ids.append(raw_id)

        if not mapped_raw_ids:
            logger.warning("Could not map any profile movies. Using popular fallback.")
            return self.popular_movie_ids_fallback[:n], "None of your liked movies were found. Showing popular movies."

        inner_ids = [self.raw_to_inner_iid_map[raw_id] for raw_id in mapped_raw_ids]
        n_items = self.qi.shape[0]
        valid_inner_ids = [iid for iid in inner_ids if iid < n_items]

        if not valid_inner_ids:
            logger.warning("No valid inner IDs found. Using popular fallback.")
            return self.popular_movie_ids_fallback[:n], "Could not generate recommendations. Showing popular movies."

        item_vectors = np.array([self.qi[inner_id] for inner_id in valid_inner_ids])
        average_item_vector = np.mean(item_vectors, axis=0)

        all_similarity_scores = []
        for inner_id, raw_id in self.inner_to_raw_iid_map.items():
            if raw_id in mapped_raw_ids or inner_id >= n_items:
                continue
            item_vector = self.qi[inner_id]
            similarity = cosine_similarity([average_item_vector], [item_vector])[0][0]
            all_similarity_scores.append((raw_id, similarity))

        all_similarity_scores.sort(key=lambda x: x[1], reverse=True)
        top_raw_ids = [score[0] for score in all_similarity_scores[:n * 2]]

        recommended_imdb_ids = self.movie_data_service.get_imdb_ids_from_raw_ids(top_raw_ids)

        if not recommended_imdb_ids:
            logger.warning("No personalized recommendations found. Falling back to popular.")
            return self.popular_movie_ids_fallback[:n], "No recommendations found. Showing popular movies."

        return recommended_imdb_ids[:n], f"Generated {len(recommended_imdb_ids)} recommendations."

@lru_cache()
def get_recommender_service():
    """Cached dependency injector for RecommenderService to ensure it's a singleton."""
    service = RecommenderService()
    return service
