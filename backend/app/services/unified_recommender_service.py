"""Unified Movie Recommender Service

This module combines the best features from the original recommender service and the enhanced version:
1. Core model loading and recommendation functionality from the original service
2. Enhanced IMDb ID to MovieLens ID mapping from the enhanced service
3. Improved error handling, logging, and performance optimizations
"""

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Tuple, Optional
from surprise import SVD
from collections import defaultdict
import logging
import joblib
from pathlib import Path
import time
import asyncio
from sqlalchemy import create_engine, text, inspect
import httpx
from types import SimpleNamespace

from ..core.config import settings, BACKEND_APP_DIR

logger = logging.getLogger(__name__)

# Constants
MODEL_FILENAME = "svd_model.joblib"
MODEL_PATH = BACKEND_APP_DIR.parent / "models" / MODEL_FILENAME
MIN_RATINGS_FOR_POPULARITY = 50
TOP_N_POPULAR_FALLBACK = 20

class UnifiedRecommenderService:
    """Unified recommender service that combines the best features of both previous implementations."""
    
    # Shared database engine across all instances
    _db_engine = None
    
    # Track mapping statistics for debugging
    _mapping_stats = {
        'direct_hits': 0,
        'enhanced_hits': 0,
        'misses': 0,
        'total_requests': 0,
        'errors': 0
    }
    
    async def _get_movie_details_by_imdb_id(self, client: httpx.AsyncClient, imdb_id: str) -> Optional[Dict[str, Any]]:
        """Helper to fetch details for a single IMDb ID."""
        base_url = settings.OMDB_API_BASE_URL or "http://www.omdbapi.com/"
        params = {"i": imdb_id, "apikey": settings.OMDB_API_KEY}
        try:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("Response") == "True":
                return {
                    "imdb_id": data.get("imdbID"),
                    "title": data.get("Title"),
                    "year": data.get("Year"),
                    "poster_url": data.get("Poster"),
                    "genres": data.get("Genre"),
                    "plot": data.get("Plot"),
                    "actors": data.get("Actors"),
                    "imdbRating": data.get("imdbRating"),
                }
            else:
                logger.warning(f"OMDb API returned an error for IMDb ID {imdb_id}: {data.get('Error')}")
                return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching details for IMDb ID {imdb_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching details for IMDb ID {imdb_id}: {e}")
            return None

    async def get_movie_details_by_ids(self, imdb_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch full movie details for a list of IMDb IDs concurrently."""
        if not settings.OMDB_API_KEY:
            logger.error("OMDB_API_KEY not configured. Cannot fetch movie details.")
            return []

        timeout = httpx.Timeout(10.0, connect=3.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            tasks = [self._get_movie_details_by_imdb_id(client, imdb_id) for imdb_id in imdb_ids]
            results = await asyncio.gather(*tasks)
        
        return [result for result in results if result is not None]

    def __init__(self):
        """Initialize the unified recommender service."""
        self.algo = SVD()
        self.trainset = None  # Will be populated when model is loaded
        self.popular_movie_ids_fallback = []
        self.raw_to_inner_uid_map = {}
        self.raw_to_inner_iid_map = {}
        self.inner_to_raw_iid_map = {}
        self.all_movie_imdb_ids = set()
        self.model_loaded = False
        
        # Set up model directories
        self.models_dir = MODEL_PATH.parent
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.popular_movies_file = self.models_dir / "popular_movies_fallback.joblib"
        
        # Initialize database engine if needed
        if not self.__class__._db_engine and settings.DATABASE_URL:
            try:
                self.__class__._db_engine = create_engine(settings.DATABASE_URL)
                logger.info("Database engine created.")
                
                # Verify enhanced_links table existence
                self._verify_enhanced_links_table()
            except Exception as e:
                logger.error(f"Failed to create database engine: {e}")
                self.__class__._db_engine = None

    def _verify_enhanced_links_table(self):
        """Check if the enhanced_links table exists and has data."""
        if not self.__class__._db_engine:
            logger.error("Database engine not initialized, cannot verify enhanced_links table")
            return
            
        try:
            # Check if the table exists
            inspector = inspect(self.__class__._db_engine)
            tables = inspector.get_table_names()
            
            if 'enhanced_links' not in tables:
                logger.warning("Enhanced links table does not exist in database. Only standard mapping will be used.")
                return
                
            # Check if the table has data
            with self.__class__._db_engine.connect() as connection:
                result = connection.execute(text("SELECT COUNT(*) FROM enhanced_links")).fetchone()
                count = result[0] if result else 0
                
                logger.info(f"Enhanced links table contains {count} mappings")
                
                if count == 0:
                    logger.warning("Enhanced links table exists but contains no data")
                    
        except Exception as e:
            logger.error(f"Error verifying enhanced_links table: {str(e)}")
            
    def load_model(self):
        """Loads the pre-trained SVD model and associated data from disk."""
        logger.info("Attempting to load model and popular movies...")
        self.model_loaded = False  # Initialize to False
        try:
            # Define paths for individual model components
            models_dir = BACKEND_APP_DIR.parent / "models"
            components_path = models_dir / "svd_model_components.joblib"
            uid_map_path = models_dir / "raw_to_inner_uid_map.joblib"
            iid_map_path = models_dir / "raw_to_inner_iid_map.joblib"
            inner_iid_map_path = models_dir / "inner_to_raw_iid_map.joblib"
            all_ids_path = models_dir / "all_movie_imdb_ids.joblib"

            component_paths = [components_path, uid_map_path, iid_map_path, inner_iid_map_path, all_ids_path]

            if not all(p.exists() for p in component_paths):
                missing_files = [p.name for p in component_paths if not p.exists()]
                logger.critical(f"One or more pre-trained model component files not found in {models_dir}.")
                logger.critical(f"Missing files: {missing_files}")
                logger.critical("Please run the training script to generate the model components.")
                # self.model_loaded remains False
            else:
                logger.info("Loading and reconstructing pre-trained model...")

                # Load the raw model components (numpy arrays)
                model_components = joblib.load(components_path)
                logger.info("  - 'svd_model_components' loaded.")

                # Reconstruct the SVD object
                self.algo = SVD()
                self.algo.pu = model_components['pu']
                self.algo.qi = model_components['qi']
                self.algo.bu = model_components['bu']
                self.algo.bi = model_components['bi']
                
                self.algo.trainset = SimpleNamespace(global_mean=model_components['global_mean'])
                logger.info("  - SVD model successfully reconstructed.")

                # Load mapping files
                try:
                    logger.info(f"Attempting to load 'raw_to_inner_uid_map.joblib' from {uid_map_path}")
                    self.raw_to_inner_uid_map = joblib.load(uid_map_path)
                    logger.info("  - 'raw_to_inner_uid_map.joblib' loaded successfully.")
                    
                    logger.info(f"Attempting to load 'raw_to_inner_iid_map.joblib' from {iid_map_path}")
                    self.raw_to_inner_iid_map = joblib.load(iid_map_path)
                    logger.info("  - 'raw_to_inner_iid_map.joblib' loaded successfully.")
                    
                    logger.info(f"Attempting to load 'inner_to_raw_iid_map.joblib' from {inner_iid_map_path}")
                    self.inner_to_raw_iid_map = joblib.load(inner_iid_map_path)
                    logger.info("  - 'inner_to_raw_iid_map.joblib' loaded successfully.")
                    
                    logger.info(f"Attempting to load 'all_movie_imdb_ids.joblib' from {all_ids_path}")
                    self.all_movie_imdb_ids = joblib.load(all_ids_path)
                    logger.info("  - 'all_movie_imdb_ids.joblib' loaded successfully.")

                    logger.info("All pre-trained model components loaded successfully.")
                    self.model_loaded = True
                    
                    # Calculate and cache popular movies
                    logger.info("Proceeding to calculate and store popular movies...")
                    self._calculate_and_store_popular_movies()
                    
                except Exception as e:
                    logger.error(f"Error loading model mappings: {e}")
                    self.model_loaded = False

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model_loaded = False

        logger.info("load_model method finished.")

    def _calculate_and_store_popular_movies(self):
        """Calculate and store popular movies for fallback recommendations."""
        logger.info("Popular movies cache file path: {}".format(self.popular_movies_file))

        # Try to load cached popular movies first
        if self.popular_movies_file.exists():
            logger.info(f"Attempting to load popular movies from cache file: {self.popular_movies_file}")
            try:
                self.popular_movie_ids_fallback = joblib.load(self.popular_movies_file)
                logger.info(f"Successfully loaded {len(self.popular_movie_ids_fallback)} popular movies from cache: {self.popular_movies_file}")
                logger.info("Using cached popular movies.")
                return
            except Exception as e:
                logger.warning(f"Failed to load popular movies from cache: {e}. Will recalculate.")

        # If we're here, either the cache didn't exist or couldn't be loaded
        if not self.model_loaded:
            logger.warning("Model not loaded. Cannot calculate popular movies.")
            self.popular_movie_ids_fallback = []
            return

        try:
            logger.info("Calculating popular movies from ratings data...")
            
            # We define popularity as movies with the most ratings
            popular_movies = []
            if self.__class__._db_engine:
                with self.__class__._db_engine.connect() as connection:
                    # Get movies with many ratings (efficient SQL query)
                    query = text("""
                    SELECT movieId, COUNT(*) as num_ratings 
                    FROM ratings 
                    GROUP BY movieId 
                    HAVING COUNT(*) > :min_ratings
                    ORDER BY num_ratings DESC
                    LIMIT :limit
                    """)
                    
                    result = connection.execute(query, {
                        'min_ratings': MIN_RATINGS_FOR_POPULARITY,
                        'limit': TOP_N_POPULAR_FALLBACK
                    }).fetchall()
                    
                    if result:
                        # Convert MovieLens IDs to IMDb IDs
                        for movie_id, _ in result:
                            imdb_ids = self._get_imdb_ids_from_raw_ids([str(movie_id)])
                            if imdb_ids:
                                popular_movies.extend(imdb_ids)
                        
                        logger.info(f"Found {len(popular_movies)} popular movies from database")
                    else:
                        logger.warning("No popular movies found in database")
            
            # If we have popular movies, save them
            if popular_movies:
                self.popular_movie_ids_fallback = popular_movies[:TOP_N_POPULAR_FALLBACK]
                
                # Cache to file
                logger.info(f"Saving {len(self.popular_movie_ids_fallback)} popular movie IDs to cache")
                joblib.dump(self.popular_movie_ids_fallback, self.popular_movies_file)
                logger.info(f"Popular movies saved to cache: {self.popular_movies_file}")
            else:
                # Fallback - if we can't get popular movies from DB, use some from our model
                if hasattr(self, 'inner_to_raw_iid_map') and self.inner_to_raw_iid_map:
                    # This uses our raw_to_inner_iid_map which now contains IMDb IDs directly
                    logger.info("Using model movie IDs as fallback for popular movies")
                    sample_movie_ids = list(self.raw_to_inner_iid_map.keys())[:TOP_N_POPULAR_FALLBACK]
                    self.popular_movie_ids_fallback = sample_movie_ids
                    
                    # Cache these to file as well
                    joblib.dump(self.popular_movie_ids_fallback, self.popular_movies_file)
                else:
                    logger.error("Could not generate any popular movies fallback list")
                    self.popular_movie_ids_fallback = []
        
        except Exception as e:
            logger.error(f"Error calculating popular movies: {e}")
            self.popular_movie_ids_fallback = []
        
        logger.info("Popular movies calculation step completed (see previous logs for details).")
    
    def _get_raw_movie_id_from_imdb_id(self, imdb_id: str) -> Optional[str]:
        """Get MovieLens ID from IMDb ID using both direct and enhanced mappings.
        
        Args:
            imdb_id: IMDb ID (with or without tt prefix)
            
        Returns:
            MovieLens ID if found, None otherwise
        """
        # Update statistics
        self.__class__._mapping_stats['total_requests'] += 1
        
        start_time = time.time()
        
        # First scenario: Our model now uses IMDb IDs directly as raw IDs in newer models
        # Check if this IMDb ID exists directly in the raw_to_inner_iid_map
        if imdb_id in self.raw_to_inner_iid_map:
            self.__class__._mapping_stats['direct_hits'] += 1
            logger.debug(f"IMDb ID {imdb_id} found directly in model's item map")
            return imdb_id
        
        # Second scenario: Older model with MovieLens IDs - need database lookup
        # If imdb_id includes 'tt' prefix, remove it for direct database lookup
        db_imdb_id = imdb_id
        if imdb_id.startswith('tt'):
            db_imdb_id = imdb_id[2:]
        
        # Try standard links table first
        try:
            if self.__class__._db_engine:
                with self.__class__._db_engine.connect() as connection:
                    # Standard lookup in links table
                    query = text("SELECT movieId FROM links WHERE imdbId = :imdb_id")
                    result = connection.execute(query, {"imdb_id": db_imdb_id}).fetchone()
                    if result:
                        movielens_id = str(result[0])
                        self.__class__._mapping_stats['direct_hits'] += 1
                        logger.debug(f"Found direct mapping for IMDb ID {imdb_id} -> MovieLens ID {movielens_id}")
                        return movielens_id
        except Exception as e:
            logger.error(f"Error looking up direct mapping for IMDb ID {imdb_id}: {e}")
            self.__class__._mapping_stats['errors'] += 1
        
        # Try enhanced links table if available
        try:
            if self.__class__._db_engine:
                with self.__class__._db_engine.connect() as connection:
                    # Check if enhanced_links table exists first
                    inspector = inspect(self.__class__._db_engine)
                    if 'enhanced_links' in inspector.get_table_names():
                        # Use full IMDb ID (with tt) for enhanced lookup
                        enhanced_imdb_id = imdb_id
                        if not enhanced_imdb_id.startswith('tt'):
                            enhanced_imdb_id = f"tt{enhanced_imdb_id}"
                        
                        query = text("SELECT movielens_id, match_type, confidence FROM enhanced_links WHERE imdb_id = :imdb_id ORDER BY confidence DESC LIMIT 1")
                        result = connection.execute(query, {"imdb_id": enhanced_imdb_id}).fetchone()
                        if result:
                            self.__class__._mapping_stats['enhanced_hits'] += 1
                            movielens_id, match_type, confidence = result
                            logger.debug(f"Found enhanced mapping for IMDb ID {imdb_id} -> MovieLens ID {movielens_id} (match_type: {match_type}, confidence: {confidence})")
                            return str(movielens_id)
        except Exception as e:
            self.__class__._mapping_stats['errors'] += 1
            logger.error(f"Error looking up enhanced mapping for IMDb ID {imdb_id}: {e}")
        
        # If we get here, no mapping was found
        self.__class__._mapping_stats['misses'] += 1
        logger.debug(f"No mapping found for IMDb ID {imdb_id} after {time.time() - start_time:.3f}s")
        
        # Log overall statistics every 100 requests
        if self.__class__._mapping_stats['total_requests'] % 100 == 0:
            stats = self.__class__._mapping_stats
            success_rate = (stats['direct_hits'] + stats['enhanced_hits']) / max(1, stats['total_requests']) * 100
            logger.info(f"Mapping statistics: {stats['total_requests']} requests, "
                      f"{stats['direct_hits']} direct hits, {stats['enhanced_hits']} enhanced hits, "
                      f"{stats['misses']} misses, {stats['errors']} errors, {success_rate:.1f}% success rate")
        
        return None
        
    def _get_imdb_ids_from_raw_ids(self, raw_ids: List[str]) -> List[str]:
        """Convert raw item IDs to IMDb IDs.
        
        Args:
            raw_ids: List of raw item IDs (could be either IMDb IDs or MovieLens IDs)
            
        Returns:
            List of IMDb IDs
        """
        if not raw_ids:
            return []
        
        # First case: raw_ids are already IMDb IDs
        # This happens with newer models where raw_ids are IMDb IDs directly
        # Check if the raw_ids look like IMDb IDs (start with tt or are in all_movie_imdb_ids)
        if all(rid.startswith('tt') or rid in self.all_movie_imdb_ids for rid in raw_ids):
            return raw_ids
        
        # Second case: raw_ids are MovieLens IDs that need conversion
        try:
            if not self.__class__._db_engine:
                logger.error("No database engine available for ID conversion")
                return []
                
            with self.__class__._db_engine.connect() as connection:
                # Use SQL parameter binding for safety
                query = text("SELECT imdbId FROM links WHERE movieId IN :raw_ids")
                # Format raw_ids to tuple for SQL IN clause
                result = connection.execute(query, {'raw_ids': tuple(raw_ids)}).fetchall()
                
                # Format IMDb IDs with 'tt' prefix if needed
                imdb_ids = []
                for row in result:
                    imdb_id = str(row[0])
                    if not imdb_id.startswith('tt'):
                        imdb_id = f"tt{imdb_id}"
                    imdb_ids.append(imdb_id)
                
                return imdb_ids
        except Exception as e:
            logger.error(f"Error fetching imdb ids from raw ids: {e}")
            return []
            
    def get_recommendations(self, user_id: int, n: int = 10) -> Tuple[List[str], str, str]:
        """Get personalized movie recommendations for a user or fall back to popular movies if needed.
        
        Args:
            user_id: The user ID to generate recommendations for
            n: Number of recommendations to return
            
        Returns:
            A tuple of (list of IMDb IDs, recommendation type, message)
        """
        start_time = time.time()
        recommendation_type = "personalized"
        message = ""
        
        if not self.model_loaded:
            logger.warning(f"Model not loaded, returning popular movie fallback for user {user_id}")
            return (self.popular_movie_ids_fallback[:n], "error_model_not_loaded", 
                    "Recommender model is still loading. Popular movies returned instead.")
        
        # Try to get raw user ID from database by user_id
        raw_user_id = str(user_id)
        
        # Check if user exists in our model
        if raw_user_id not in self.raw_to_inner_uid_map:
            logger.warning(f"User {user_id} not found in model. Using popular movie fallback.")
            return (self.popular_movie_ids_fallback[:n], "popular_fallback_new_user", 
                    "You're a new user! Try rating some movies to get personalized recommendations.")
        
        # Get inner user ID
        inner_user_id = self.raw_to_inner_uid_map[raw_user_id]
        
        # Get user's already rated items to exclude from recommendations
        user_rated_inner_ids = set()
        
        try:
            if self.__class__._db_engine:
                with self.__class__._db_engine.connect() as connection:
                    # Get all movies this user has already rated
                    query = text("SELECT movieId FROM ratings WHERE userId = :user_id")
                    rated_results = connection.execute(query, {"user_id": user_id}).fetchall()
                    
                    # Convert rated MovieLens IDs to inner IDs (only if they exist in our model)
                    for result in rated_results:
                        ml_id = str(result[0])
                        if ml_id in self.raw_to_inner_iid_map:
                            inner_id = self.raw_to_inner_iid_map[ml_id]
                            user_rated_inner_ids.add(inner_id)
                            
                    logger.info(f"User {user_id} has rated {len(user_rated_inner_ids)} movies that exist in our model")
        except Exception as e:
            logger.error(f"Error getting rated items for user {user_id}: {e}")
            # Continue with empty set of rated items
            
        # Generate raw predictions for all items
        raw_predictions = []
        
        # For each item in the model, predict rating if user hasn't rated it yet
        for inner_item_id in self.inner_to_raw_iid_map.keys():
            if inner_item_id not in user_rated_inner_ids:
                # Predict rating using SVD model
                try:
                    # The Surprise predict() checks for known user/item, so we need to verify they exist first
                    est = self.algo.estimate(inner_user_id, inner_item_id)
                    raw_id = self.inner_to_raw_iid_map[inner_item_id]
                    raw_predictions.append((raw_id, est))
                except Exception as e:
                    # Skip items that cause prediction errors
                    continue
                        
        # Sort items by predicted rating
        raw_predictions.sort(key=lambda x: x[1], reverse=True)
        
        # Take top N raw IDs and convert to IMDb IDs
        top_raw_ids = [p[0] for p in raw_predictions[:n*2]]  # Get more than needed in case some mappings fail
        
        if not top_raw_ids:
            logger.warning(f"No recommendations generated for user {user_id}. Using popular fallback.")
            return (self.popular_movie_ids_fallback[:n], "popular_fallback_no_recommendations", 
                    "Could not generate personalized recommendations. Showing popular movies instead.")
        
        recommended_imdb_ids = self._get_imdb_ids_from_raw_ids(top_raw_ids)
        
        # If no IMDb IDs found, use popular fallback
        if not recommended_imdb_ids:
            logger.warning(f"Failed to convert movie IDs to IMDb IDs for user {user_id}. Using popular fallback.")
            return (self.popular_movie_ids_fallback[:n], "popular_fallback_id_mapping_failed",
                   "Could not map movie IDs to IMDb IDs. Showing popular movies instead.")
        
        # Limit to requested number
        recommended_imdb_ids = recommended_imdb_ids[:n]  
        
        logger.info(f"Successfully generated {len(recommended_imdb_ids)} personalized recommendations for user {user_id}")
        message = f"Generated {len(recommended_imdb_ids)} personalized recommendations based on your rating history."
        
        # Calculate total time
        total_time = time.time() - start_time
        logger.debug(f"get_recommendations for user {user_id} took {total_time:.3f}s")
        
        return (recommended_imdb_ids, recommendation_type, message)
        
    def get_recommendations_for_profile(self, imdb_ids: List[str], n: int = 10) -> Tuple[List[str], str]:
        """Get recommendations based on a list of IMDb IDs representing movies a user likes.
        
        This is the core method for generating personalized recommendations based on a profile
        of liked movies, rather than from the rating history in the database.
        
        Args:
            imdb_ids: List of IMDb IDs of movies the user likes
            n: Number of recommendations to return
            
        Returns:
            Tuple of (recommended IMDb IDs, message)
        """
        logger.info(f"Generating recommendations based on profile with {len(imdb_ids)} movies")
        if not self.model_loaded:
            logger.warning("Model not loaded, returning popular movie fallback.")
            return self.popular_movie_ids_fallback[:n], "Recommender model is still loading. Popular movies returned instead."

        # If no IMDb IDs provided, return popular movies
        if not imdb_ids:
            logger.warning("Empty profile provided, returning popular movie fallback.")
            return self.popular_movie_ids_fallback[:n], "No movies provided in your profile. Showing popular movies instead."
            
        # Try to map each IMDb ID to model's raw ID 
        mapped_raw_ids = []
        for imdb_id in imdb_ids:
            # First check: if our model uses IMDb IDs directly, then check if this ID is in the model
            if imdb_id in self.raw_to_inner_iid_map:
                mapped_raw_ids.append(imdb_id)
                continue
                
            # Second approach: try to map IMDb ID to a MovieLens ID if needed
            raw_id = self._get_raw_movie_id_from_imdb_id(imdb_id)
            if raw_id and raw_id in self.raw_to_inner_iid_map:
                mapped_raw_ids.append(raw_id)
            
        # Calculate proportion of IMDb IDs that were mapped successfully
        mapping_success_rate = len(mapped_raw_ids) / len(imdb_ids) if imdb_ids else 0
        logger.info(f"Successfully mapped {len(mapped_raw_ids)}/{len(imdb_ids)} IMDb IDs ({mapping_success_rate:.1%}) to model raw IDs")
        
        # If none of the IMDb IDs could be mapped, fall back to popular movies
        if not mapped_raw_ids:
            logger.warning("None of the profile movies could be mapped to model IDs. Using popular movies fallback.")
            return self.popular_movie_ids_fallback[:n], "None of your liked movies were found in our database. Showing popular movies instead."

        # Get inner IDs for the raw IDs
        inner_ids = [self.raw_to_inner_iid_map[raw_id] for raw_id in mapped_raw_ids if raw_id in self.raw_to_inner_iid_map]
        
        # Get item vectors for inner IDs from model's qi matrix, with boundary checks
        n_items = self.algo.qi.shape[0]
        valid_inner_ids = [iid for iid in inner_ids if iid < n_items]

        if not valid_inner_ids:
            logger.warning("None of the mapped profile movies have valid inner IDs in the model. Using popular fallback.")
            return self.popular_movie_ids_fallback[:n], "None of your liked movies could be used for recommendations. Showing popular movies instead."
        
        item_vectors = np.array([self.algo.qi[inner_id] for inner_id in valid_inner_ids])
        
        # Calculate the average item vector representing this user's taste
        average_item_vector = np.mean(item_vectors, axis=0)
        
        # Calculate similarity between this "user vector" and all item vectors
        # using efficient matrix operations
        all_similarity_scores = []
        
        # For each movie in the model, calculate similarity to average item vector
        for inner_id, raw_id in self.inner_to_raw_iid_map.items():
            # Skip items that are already in the user's profile
            if raw_id in mapped_raw_ids:
                continue
                
            # CRITICAL: Add boundary check to prevent crash from inconsistent model files
            if inner_id >= self.algo.qi.shape[0]:
                continue
                
            # Calculate cosine similarity
            item_vector = self.algo.qi[inner_id]
            similarity = cosine_similarity([average_item_vector], [item_vector])[0][0]
            
            all_similarity_scores.append((raw_id, similarity))
        
        # Sort by similarity score (descending)
        all_similarity_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Take top N raw IDs and convert to IMDb IDs
        top_raw_ids = [score[0] for score in all_similarity_scores[:n*2]]  # Get more than needed in case some mappings fail
        
        # Convert raw IDs to IMDb IDs
        recommended_imdb_ids_to_return = self._get_imdb_ids_from_raw_ids(top_raw_ids)
        
        # Add fallback in case no personalized recommendations found
        if not recommended_imdb_ids_to_return:
            logger.warning("No personalized recommendations found. Falling back to popular movies.")
            recommended_imdb_ids_to_return = [str(imdb_id) for imdb_id in self.popular_movie_ids_fallback[:n]]
            base_message = "Could not find personalized recommendations based on your profile. Showing popular movies instead."
        else:
            base_message = f"Generated {len(recommended_imdb_ids_to_return)} recommendations based on your movie profile."
            
        # Trim to requested size
        recommended_imdb_ids_to_return = recommended_imdb_ids_to_return[:n]
        
        # Return IMDb IDs and message
        return recommended_imdb_ids_to_return, base_message
        
    async def search_movies_by_title(self, title: str) -> List[Dict[str, Any]]:
        """Search for movies by title using the OMDb API.

        Args:
            title: The movie title to search for.

        Returns:
            A list of movie detail dictionaries from OMDb.
        """
        logger.info(f"Searching OMDb API for movies with title: '{title}'")

        if not settings.OMDB_API_KEY:
            logger.error("OMDB_API_KEY not configured. Cannot search for movies.")
            return []

        # OMDb API endpoint for searching by title (the 's' parameter)
        # Using http:// because the default is not https
        base_url = settings.OMDB_API_BASE_URL or "http://www.omdbapi.com/"
        params = {
            "s": title,
            "apikey": settings.OMDB_API_KEY,
            "type": "movie"  # To ensure we only get movies
        }

        try:
            timeout = httpx.Timeout(10.0, connect=3.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                data = response.json()

            if data.get("Response") == "True":
                search_results = data.get("Search", [])
                logger.info(f"Found {len(search_results)} results from OMDb for '{title}'")
                return search_results
            else:
                error_message = data.get("Error", "Unknown error from OMDb API.")
                logger.warning(f"OMDb API returned an error for title '{title}': {error_message}")
                return []

        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting from OMDb API: {e}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred during movie search: {e}")
            return []
        
    async def get_movie_details_by_imdb_id(self, imdb_id: str) -> Dict[str, Any]:
        """Get detailed information about a movie using its IMDb ID.
        
        Args:
            imdb_id: The IMDb ID of the movie
            
        Returns:
            Dictionary with movie details
        """
        logger.debug(f"Fetching details for movie with IMDb ID: {imdb_id}")
        
        # Check if IMDb ID is properly formatted
        if not imdb_id:
            logger.warning("Empty IMDb ID provided")
            return {"Error": "Invalid IMDb ID"}
        
        # Ensure IMDb ID has tt prefix
        if not imdb_id.startswith('tt'):
            imdb_id = f"tt{imdb_id}"
        
        # Use OMDb API to get movie details by IMDb ID
        if not settings.OMDB_API_KEY or not settings.OMDB_API_BASE_URL:
            logger.error("OMDb API key or base URL not configured for get_movie_details_by_imdb_id.")
            return {"Error": "OMDb API not configured", "imdbID": imdb_id}

        try:
            # Construct the OMDb API URL for fetching by IMDb ID
            omdb_url = f"{settings.OMDB_API_BASE_URL}?i={imdb_id}&apikey={settings.OMDB_API_KEY}"
            
            timeout = httpx.Timeout(10.0, connect=5.0) # Standard timeout
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(f"Fetching details from OMDb for IMDb ID: {imdb_id} using URL: {omdb_url}")
                omdb_response = await client.get(omdb_url)
                omdb_response.raise_for_status()  # Raise an exception for HTTP error codes (4xx or 5xx)
                response_data = omdb_response.json()

            # Check if OMDb API returned a successful response
            if response_data.get("Response") == "True":
                logger.info(f"Successfully fetched details for movie {imdb_id} from OMDb: {response_data.get('Title')}")
                # The response_data from OMDb (e.g., Title, Year, Poster, Plot, imdbID)
                # is directly usable by the frontend after its mapping logic.
                return response_data
            else:
                error_message = response_data.get("Error", "Movie not found or OMDb API error")
                logger.warning(f"OMDb API returned an error for {imdb_id}: {error_message}")
                return {"Error": f"OMDb API error: {error_message}", "imdbID": imdb_id}

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching details for {imdb_id} from OMDb API: {e.response.status_code} - {e.response.text}")
            return {"Error": f"OMDb API HTTP error {e.response.status_code}", "imdbID": imdb_id}
        except httpx.RequestError as e:
            # This catches network errors, DNS failures, timeouts not covered by HTTPStatusError, etc.
            logger.error(f"Request error fetching details for {imdb_id} from OMDb API: {e}")
            return {"Error": f"OMDb API request error", "imdbID": imdb_id}
        except Exception as e:
            # Catch any other unexpected errors, including JSONDecodeError if response is not valid JSON
            logger.error(f"Unexpected error fetching details for {imdb_id} from OMDb API: {e}", exc_info=True)
            return {"Error": f"Unexpected error processing OMDb API response for {imdb_id}", "imdbID": imdb_id}
