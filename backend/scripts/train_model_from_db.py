import pandas as pd
from sqlalchemy import create_engine, text
from surprise import Dataset, Reader, SVD
import joblib
from pathlib import Path
import sys
import logging # Import logging
from typing import Union

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add backend app directory to sys.path to allow absolute imports
# Correcting path assuming 'scripts' is directly under 'backend'
# __file__ is .../backend/scripts/train_model_from_db.py
# .parent is .../backend/scripts/
# .parent.parent is .../backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR)) # Add .../backend to sys.path

from app.core.config import settings # Now this should work

MODEL_FILENAME = "svd_model.joblib"
MODELS_DIR = BACKEND_DIR / "models" # models directory directly under backend
MODEL_PATH = MODELS_DIR / MODEL_FILENAME

def fetch_data_from_db(engine) -> Union[pd.DataFrame, None]:
    """Fetches ratings and links data from the database and merges them."""
    # Avoid logging full credentials, show only host/db part if possible
    try:
        logger.info(f"Connecting to database via provided engine: {engine.url.host}...")
        with engine.connect() as connection:
            query = text("""
                SELECT r.userId AS "userId", l.imdbId AS "imdbId", r.rating
                FROM ratings r
                JOIN links l ON r.movieId = l.movieId;
            """)
            logger.info("Executing query to fetch all ratings data... This may take a while for large datasets.")
            df = pd.read_sql_query(query, connection)
        logger.info(f"Successfully fetched {len(df)} ratings.")
        if df.empty:
            logger.warning("No data fetched from the database.")
            return None
        
        df['userId'] = df['userId'].astype(int)
        df['imdbId'] = df['imdbId'].astype(str)
        df['rating'] = df['rating'].astype(float)
        return df
    except Exception as e:
        logger.error(f"Error fetching data from database: {e}", exc_info=True)
        return None

def main():
    logger.info("Starting model training process using data from the database...")
    
    engine = None
    try:
        logger.info(f"Database URL from settings: {settings.DATABASE_URL[:settings.DATABASE_URL.find('@') if '@' in settings.DATABASE_URL else len(settings.DATABASE_URL)]}...") # Log URL safely
        engine = create_engine(settings.DATABASE_URL)
        ratings_df = fetch_data_from_db(engine)
    except Exception as e:
        logger.error(f"An error occurred during database engine creation or data fetching: {e}", exc_info=True)
        ratings_df = None

    if ratings_df is None or ratings_df.empty:
        logger.error("Model training aborted due to data loading failure.")
        if engine:
            engine.dispose()
        return

    logger.info("Preparing data for Surprise model training...")
    reader = Reader(rating_scale=(0.5, 5.0))
    data = Dataset.load_from_df(ratings_df[['userId', 'imdbId', 'rating']], reader)
    
    logger.info("Building full trainset...")
    trainset = data.build_full_trainset()
    
    logger.info("Initializing SVD model...")
    algo = SVD()
    
    logger.info("Training SVD model... This can also take a significant amount of time.")
    algo.fit(trainset)
    logger.info("Model training complete.")

    # Create mappings and collect all item IDs
    # _raw2inner_id_users maps raw user IDs to Surprise inner IDs
    raw_to_inner_uid_map = trainset._raw2inner_id_users
    # _raw2inner_id_items maps raw item IDs (imdbId) to Surprise inner IDs
    raw_to_inner_iid_map = trainset._raw2inner_id_items
    # to_raw_iid maps Surprise inner item IDs back to raw item IDs (imdbId in our case)
    inner_to_raw_iid_map = {inner_id: trainset.to_raw_iid(inner_id) for inner_id in trainset.all_items()}
    # Get all unique imdbIds that were part of the training
    all_movie_imdb_ids = set(ratings_df['imdbId'].unique())

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Saving model components individually...")

    try:
        logger.info("  - Saving 'raw_to_inner_uid_map'...")
        joblib.dump(raw_to_inner_uid_map, MODELS_DIR / "raw_to_inner_uid_map.joblib")
        logger.info("    'raw_to_inner_uid_map' saved successfully.")

        logger.info("  - Saving 'raw_to_inner_iid_map'...")
        joblib.dump(raw_to_inner_iid_map, MODELS_DIR / "raw_to_inner_iid_map.joblib")
        logger.info("    'raw_to_inner_iid_map' saved successfully.")
        
        logger.info("  - Saving 'inner_to_raw_iid_map'...")
        joblib.dump(inner_to_raw_iid_map, MODELS_DIR / "inner_to_raw_iid_map.joblib")
        logger.info("    'inner_to_raw_iid_map' saved successfully.")

        logger.info("  - Saving 'all_movie_imdb_ids'...")
        joblib.dump(all_movie_imdb_ids, MODELS_DIR / "all_movie_imdb_ids.joblib")
        logger.info("    'all_movie_imdb_ids' saved successfully.")

        # The 'algo' object is too complex to pickle efficiently. 
        # Instead, we extract its essential components (numpy arrays) and save them.
        model_components = {
            'pu': algo.pu,
            'qi': algo.qi,
            'bu': algo.bu,
            'bi': algo.bi,
            'global_mean': trainset.global_mean
        }
        logger.info("  - Saving 'svd_model_components'...")
        joblib.dump(model_components, MODELS_DIR / "svd_model_components.joblib")
        logger.info("    'svd_model_components' saved successfully.")

        logger.info("\nAll model components saved successfully as separate files.")
        logger.info(f"Old combined model file at {MODEL_PATH} is no longer used by this script for saving, ensure RecommenderService.load_model is updated accordingly.")

    except Exception as e:
        logger.error(f"An error occurred during model saving or main processing: {e}", exc_info=True)
    finally:
        if engine:
            logger.info("Disposing database engine...")
            engine.dispose()
            logger.info("Database engine disposed.")

if __name__ == '__main__':
    main()