import pandas as pd
from sqlalchemy import create_engine, text
from surprise import Dataset, Reader, SVD
import joblib
from pathlib import Path
import sys

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

def fetch_data_from_db(db_url: str) -> pd.DataFrame | None:
    """Fetches ratings and links data from PostgreSQL and merges them."""
    # Avoid logging full credentials, show only host/db part if possible
    db_identifier = db_url.split('@')[-1] if '@' in db_url else db_url
    print(f"Connecting to database: {db_identifier}...")
    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            # Ensure column names match CSV headers if possible, or adjust here
            # Using "userId", "imdbId" as per previous conventions
            query = text("""
                SELECT r.user_id AS "userId", l.imdb_id AS "imdbId", r.rating
                FROM ratings r
                JOIN links l ON r.movie_id = l.movie_id;
            """)
            print("Executing query to fetch all ratings data... This may take a while for large datasets.")
            df = pd.read_sql_query(query, connection)
            print(f"Successfully fetched {len(df)} ratings.")
            if df.empty:
                print("No data fetched from the database.")
                return None
            
            # Ensure correct dtypes for surprise
            df['userId'] = df['userId'].astype(int)
            df['imdbId'] = df['imdbId'].astype(str) # imdbId is used as item_id in surprise
            df['rating'] = df['rating'].astype(float)
            return df
    except Exception as e:
        print(f"Error fetching data from database: {e}")
        return None

def main():
    print("Starting model training process using data from PostgreSQL...")
    
    ratings_df = fetch_data_from_db(settings.DATABASE_URL)

    if ratings_df is None or ratings_df.empty:
        print("Model training aborted due to data loading failure.")
        return

    print("Preparing data for Surprise model training...")
    reader = Reader(rating_scale=(0.5, 5.0)) # Adjust rating_scale if your data differs
    # Using 'userId', 'imdbId', 'rating' as per the DataFrame from fetch_data_from_db
    data = Dataset.load_from_df(ratings_df[['userId', 'imdbId', 'rating']], reader)
    
    print("Building full trainset...")
    trainset = data.build_full_trainset()
    
    print("Initializing SVD model...")
    algo = SVD()
    
    print("Training SVD model... This can also take a significant amount of time.")
    algo.fit(trainset)
    print("Model training complete.")

    # Create mappings and collect all item IDs
    # _raw2inner_id_users maps raw user IDs to Surprise inner IDs
    raw_to_inner_uid_map = trainset._raw2inner_id_users 
    # to_raw_iid maps Surprise inner item IDs back to raw item IDs (imdbId in our case)
    inner_to_raw_iid_map = {inner_id: trainset.to_raw_iid(inner_id) for inner_id in trainset.all_items()}
    # Get all unique imdbIds that were part of the training
    all_movie_imdb_ids = set(ratings_df['imdbId'].unique())

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Saving trained model, trainset, and mappings to {MODEL_PATH}...")
    try:
        # Save all components needed by RecommenderService
        joblib.dump((algo, trainset, raw_to_inner_uid_map, inner_to_raw_iid_map, all_movie_imdb_ids), MODEL_PATH)
        print(f"Model, trainset, and mappings saved successfully to {MODEL_PATH}")
    except Exception as e:
        print(f"Error saving model: {e}")

if __name__ == '__main__':
    main()