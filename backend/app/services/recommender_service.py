import pandas as pd
from surprise import Dataset, Reader, SVD
from collections import defaultdict
import joblib
from pathlib import Path
from sqlalchemy import create_engine, text # Added for DB interaction

import httpx # For making API calls to OMDb
from ..core.config import settings, BACKEND_APP_DIR

MODEL_FILENAME = "svd_model.joblib"
MODEL_PATH = BACKEND_APP_DIR.parent / "models" / MODEL_FILENAME

# Constants for popular movies fallback
MIN_RATINGS_FOR_POPULARITY = 50
TOP_N_POPULAR_FALLBACK = 20

class RecommenderService:
    _db_engine = None # Class variable for engine, initialized once
    def __init__(self):
        self.algo = SVD() # Will be loaded from file on Heroku
        self.trainset = None # Will be loaded from file on Heroku
        self.popular_movie_ids_fallback = []
        self.raw_to_inner_uid_map = {} # Loaded from file
        self.inner_to_raw_iid_map = {} # Loaded from file
        self.all_movie_imdb_ids = set() # Loaded from file

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

        if not RecommenderService._db_engine and settings.DATABASE_URL:
            try:
                RecommenderService._db_engine = create_engine(settings.DATABASE_URL)
                print("Database engine created.")
            except Exception as e:
                print(f"Failed to create database engine: {e}")
                RecommenderService._db_engine = None

        # Model loading logic for all environments (Heroku or local)
        if MODEL_PATH.exists():
            print(f"Loading pre-trained model from {MODEL_PATH}...")
            try:
                (self.algo, 
                 self.trainset, 
                 self.raw_to_inner_uid_map, 
                 self.inner_to_raw_iid_map, 
                 self.all_movie_imdb_ids) = joblib.load(MODEL_PATH)
                print("Pre-trained model loaded successfully.")
            except Exception as e:
                print(f"CRITICAL: Error loading pre-trained model: {e}")
                print("The service might be non-operational for personalized recommendations.")
                # Initialize attributes to safe defaults if loading fails
                self.algo = SVD() 
                self.trainset = None
                self.raw_to_inner_uid_map = {}
                self.inner_to_raw_iid_map = {}
                self.all_movie_imdb_ids = set()
        else:
            print(f"CRITICAL: Pre-trained model not found at {MODEL_PATH}.")
            print("Please run the training script: python backend/scripts/train_model_from_db.py")
            # Initialize attributes to safe defaults
            self.algo = SVD() 
            self.trainset = None
            self.raw_to_inner_uid_map = {}
            self.inner_to_raw_iid_map = {}
            self.all_movie_imdb_ids = set()

        # Calculate popular movies (from DB if engine available, otherwise fallback or empty)
        self._calculate_and_store_popular_movies()

    def _calculate_and_store_popular_movies(self):
        if not RecommenderService._db_engine:
            print("Database engine not available. Cannot calculate popular movies from DB.")
            # Optionally, try to use self.ratings_df if available (local dev without DB)
            if hasattr(self, 'ratings_df') and self.ratings_df is not None and not self.ratings_df.empty:
                print("Attempting to calculate popular movies from local ratings_df as fallback...")
                try:
                    movie_stats = self.ratings_df.groupby('imdbId').agg(
                        num_ratings=('rating', 'size'),
                        avg_rating=('rating', 'mean')
                    ).reset_index()
                    popular_movies_df = movie_stats[movie_stats['num_ratings'] >= MIN_RATINGS_FOR_POPULARITY]
                    popular_movies_df = popular_movies_df.sort_values(by=['num_ratings', 'avg_rating'], ascending=[False, False])
                    self.popular_movie_ids_fallback = popular_movies_df['imdbId'].head(TOP_N_POPULAR_FALLBACK).tolist()
                    print(f"Stored {len(self.popular_movie_ids_fallback)} popular movies from local df.")
                except Exception as e_df:
                    print(f"Error calculating popular movies from local df: {e_df}")
                    self.popular_movie_ids_fallback = []
            return

        print("Calculating popular movies for fallback from database...")
        try:
            with RecommenderService._db_engine.connect() as connection:
                query = text(f"""
                    SELECT
                        l."imdbId",
                        COUNT(r.rating) AS num_ratings,
                        AVG(r.rating) AS avg_rating
                    FROM ratings r
                    JOIN links l ON r."movieId" = l."movieId"
                    GROUP BY l."imdbId"
                    HAVING COUNT(r.rating) >= :min_ratings
                    ORDER BY num_ratings DESC, avg_rating DESC
                    LIMIT :top_n
                """)
                result = connection.execute(query, {
                    "min_ratings": MIN_RATINGS_FOR_POPULARITY,
                    "top_n": TOP_N_POPULAR_FALLBACK
                })
                self.popular_movie_ids_fallback = [row[0] for row in result] # imdb_id is the first column
                print(f"Stored {len(self.popular_movie_ids_fallback)} popular movies from database for fallback.")
        except Exception as e:
            print(f"Error calculating popular movies from database: {e}")
            self.popular_movie_ids_fallback = []

    async def get_movie_details_by_imdb_id(self, imdb_id: str) -> dict:
        """Fetches movie details from OMDb API using IMDb ID."""
        if not settings.OMDB_API_KEY or settings.OMDB_API_KEY == "YOUR_OMDB_API_KEY_HERE":
            logger.error("OMDb API key not configured or is placeholder.")
            return {"Error": "OMDb API key not configured."}

        if not isinstance(imdb_id, str):
            logger.error(f"Invalid imdb_id type: {type(imdb_id)}, value: {imdb_id}. Must be a string.")
            return {"Error": "Invalid IMDb ID format (must be string)."}
        
        imdb_id_original_for_log = imdb_id # Save original for logging before stripping
        imdb_id = imdb_id.strip()

        numeric_part = imdb_id[2:] if imdb_id.startswith("tt") else imdb_id
        # IMDb IDs can be 7 to 9 digits long (e.g. tt1234567, tt123456789)
        if not numeric_part.isdigit() or not (7 <= len(numeric_part) <= 9):
             logger.warning(f"Potentially malformed IMDb ID numeric part: '{numeric_part}' (from original: '{imdb_id_original_for_log}'). Proceeding with tt prefixing.")

        full_imdb_id = imdb_id if imdb_id.startswith("tt") else f"tt{imdb_id}"
        
        params = {
            "apikey": settings.OMDB_API_KEY,
            "i": full_imdb_id
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        request_url = f"{settings.OMDB_API_BASE_URL}?{query_string}"
        
        logger.info(f"Attempting OMDb API call to: {settings.OMDB_API_BASE_URL}?i={params['i']}&apikey=REDACTED (using original imdb_id: {imdb_id_original_for_log})")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(settings.OMDB_API_BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                if data.get("Response") == "True":
                    logger.info(f"Successfully fetched details for IMDb ID {full_imdb_id} from OMDb.")
                    return {
                        "imdb_id": full_imdb_id,
                        "Title": data.get("Title"),
                        "Year": data.get("Year"),
                        "Rated": data.get("Rated"),
                        "Released": data.get("Released"),
                        "Runtime": data.get("Runtime"),
                        "Genre": data.get("Genre"),
                        "Director": data.get("Director"),
                        "Writer": data.get("Writer"),
                        "Actors": data.get("Actors"),
                        "Plot": data.get("Plot"),
                        "Language": data.get("Language"),
                        "Country": data.get("Country"),
                        "Awards": data.get("Awards"),
                        "Poster": data.get("Poster"),
                        "imdbRating": data.get("imdbRating"),
                        "imdbVotes": data.get("imdbVotes"),
                        "Type": data.get("Type"),
                    }
                else:
                    logger.error(f"OMDb API returned error for full_imdb_id {full_imdb_id} (original imdb_id: {imdb_id_original_for_log}): {data.get('Error')}. URL: {settings.OMDB_API_BASE_URL}?i={params['i']}&apikey=REDACTED. Full response: {data}")
                    return {"Error": f"OMDb API Error: {data.get('Error')}", "imdb_id_queried": full_imdb_id, "original_imdb_id": imdb_id_original_for_log}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTPStatusError when calling OMDb API for {full_imdb_id} (original: {imdb_id_original_for_log}). Status: {e.response.status_code}. URL: {settings.OMDB_API_BASE_URL}?i={params['i']}&apikey=REDACTED. Response: {e.response.text}")
            return {"Error": f"HTTP error: {e.response.status_code}", "imdb_id_queried": full_imdb_id, "original_imdb_id": imdb_id_original_for_log}
        except httpx.RequestError as e:
            logger.error(f"RequestError when calling OMDb API for {full_imdb_id} (original: {imdb_id_original_for_log}). URL: {settings.OMDB_API_BASE_URL}?i={params['i']}&apikey=REDACTED. Error: {str(e)}")
            return {"Error": f"Request error: {str(e)}", "imdb_id_queried": full_imdb_id, "original_imdb_id": imdb_id_original_for_log}
        except Exception as e:
            logger.exception(f"Unexpected error fetching movie details for {full_imdb_id} (original: {imdb_id_original_for_log}) from OMDb. URL: {settings.OMDB_API_BASE_URL}?i={params['i']}&apikey=REDACTED.")
            return {"Error": "Unexpected error fetching movie details.", "imdb_id_queried": full_imdb_id, "original_imdb_id": imdb_id_original_for_log}

    def get_recommendations(self, user_id: int, n: int = 10) -> tuple[list[str], str]:
        if self.trainset is None:
            msg = "Personalized recommendation model not available."
            print(msg)
            if self.popular_movie_ids_fallback:
                print("Providing popular fallback movies as model is unavailable.")
                return self.popular_movie_ids_fallback[:n], "popular_fallback_model_unavailable"
            return [], "error_model_not_ready_no_fallback"

        try:
            user_inner_id = self.trainset.to_inner_uid(user_id)
        except ValueError:
            print(f"User {user_id} not in trainset (ValueError in to_inner_uid). Providing popular fallback.")
            if self.popular_movie_ids_fallback:
                return self.popular_movie_ids_fallback[:n], "popular_fallback_unknown_user"
            return [], "error_unknown_user_no_fallback"

        # This check is somewhat redundant due to to_inner_uid but kept for clarity
        if not self.trainset.knows_user(user_id):
             print(f"User {user_id} not found in training data (knows_user). Providing popular fallback.")
             if self.popular_movie_ids_fallback:
                return self.popular_movie_ids_fallback[:n], "popular_fallback_unknown_user"
             return [], "error_unknown_user_no_fallback"

        user_rated_items_inner_ids = {item_inner_id for (item_inner_id, _) in self.trainset.ur[user_inner_id]}
        
        predictions = []
        for item_inner_id in self.trainset.all_items():
            if item_inner_id not in user_rated_items_inner_ids:
                item_raw_id = self.trainset.to_raw_iid(item_inner_id)
                predicted_rating = self.algo.predict(user_id, item_raw_id).est
                predictions.append((item_raw_id, predicted_rating))

        predictions.sort(key=lambda x: x[1], reverse=True)
        top_n_imdb_ids = [imdb_id for imdb_id, rating in predictions[:n]]
        
        if not top_n_imdb_ids:
            print(f"No personalized recommendations for user {user_id}. Providing popular fallback.")
            if self.popular_movie_ids_fallback:
                return self.popular_movie_ids_fallback[:n], "popular_fallback_no_personalized"
            return [], "error_no_personalized_no_fallback"
            
        return top_n_imdb_ids, "personalized"
