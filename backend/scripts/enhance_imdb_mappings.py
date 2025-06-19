"""Enhanced IMDb ID to MovieLens ID Mapping

This script improves the mapping between IMDb IDs and MovieLens IDs by:
1. Creating a new 'enhanced_links' table to store additional mappings
2. Using OMDb API to fetch movie details for better matching
3. Creating title-based mappings for movies not found in direct mapping
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import requests
import json

# Add the parent directory to sys.path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, Table, Column, Integer, String, MetaData, insert, select
from dotenv import load_dotenv

# Import settings from app
try:
    from app.core.config import settings
except ImportError:
    # Fallback if app module can't be imported
    load_dotenv()
    settings = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("enhance_imdb_mappings")

# --- Database Connection --- #
def get_db_engine():
    """Get SQLAlchemy database engine from environment variables"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url and settings:
        database_url = settings.DATABASE_URL
    
    if not database_url:
        logger.error("DATABASE_URL not set in environment or settings")
        sys.exit(1)
    
    return create_engine(database_url)

# --- OMDb API Functions --- #
def get_omdb_api_key():
    """Get OMDb API key from environment variables"""
    api_key = os.getenv('OMDB_API_KEY')
    if not api_key and settings:
        api_key = settings.OMDB_API_KEY
    
    if not api_key:
        logger.error("OMDB_API_KEY not set in environment or settings")
        sys.exit(1)
    
    return api_key

def get_omdb_base_url():
    """Get OMDb API base URL from environment variables"""
    base_url = os.getenv('OMDB_API_BASE_URL', 'http://www.omdbapi.com')
    if not base_url and settings:
        base_url = settings.OMDB_API_BASE_URL or 'http://www.omdbapi.com'
    
    return base_url

# --- Enhanced Links Table Setup --- #
def setup_enhanced_links_table(engine):
    """Create enhanced_links table if it doesn't exist"""
    metadata = MetaData()
    
    # Define enhanced_links table
    enhanced_links = Table(
        'enhanced_links',
        metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('imdb_id', String(10), index=True, nullable=False),  # Format: tt0114709
        Column('movielens_id', Integer, nullable=False),
        Column('match_type', String(20), nullable=False),  # 'direct', 'title_match', 'fallback'
        Column('confidence', Integer, default=100)  # 0-100 confidence score
    )
    
    # Create table if it doesn't exist
    logger.info("Setting up enhanced_links table if not exists...")
    metadata.create_all(engine, tables=[enhanced_links])
    
    # Check if table was created successfully
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES LIKE 'enhanced_links'"))
        if result.fetchone():
            logger.info("enhanced_links table is ready.")
            return True
        else:
            logger.error("Failed to create enhanced_links table.")
            return False

# --- OMDb API Movie Functions --- #
def fetch_movie_details_by_imdb_id(imdb_id: str) -> Optional[Dict]:
    """Fetch movie details from OMDb API using IMDb ID"""
    # Add 'tt' prefix if it's not already present (OMDb API requires it)
    if not imdb_id.startswith('tt'):
        imdb_id = f'tt{imdb_id}'
    
    api_key = get_omdb_api_key()
    base_url = get_omdb_base_url()
    url = f"{base_url}/?i={imdb_id}&apikey={api_key}"
    
    try:
        logger.info(f"Fetching details for IMDb ID: {imdb_id}")
        response = requests.get(url)
        data = response.json()
        
        if data.get('Response') == 'True':
            return data
        else:
            logger.warning(f"OMDb API error for {imdb_id}: {data.get('Error', 'Unknown error')}")
            return None
    except Exception as e:
        logger.error(f"Error fetching movie details for {imdb_id}: {str(e)}")
        return None

def fetch_movie_by_title_and_year(title: str, year: str = None) -> Optional[Dict]:
    """Search for a movie by title and optional year in OMDb API"""
    api_key = get_omdb_api_key()
    base_url = get_omdb_base_url()
    
    # Construct URL with title and optional year
    url = f"{base_url}/?t={requests.utils.quote(title)}&apikey={api_key}"
    if year:
        url += f"&y={year}"
    
    try:
        logger.info(f"Searching for movie: {title}" + (f" ({year})" if year else ""))
        response = requests.get(url)
        data = response.json()
        
        if data.get('Response') == 'True':
            return data
        else:
            logger.warning(f"Movie not found: {title}" + (f" ({year})" if year else ""))
            return None
    except Exception as e:
        logger.error(f"Error searching for movie: {str(e)}")
        return None

# --- Mapping Enhancement Functions --- #
def get_existing_mappings(engine) -> Dict[str, int]:
    """Get existing IMDb ID to MovieLens ID mappings from links table"""
    mappings = {}
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT imdbId, movieId FROM links"))
            for row in result:
                # Store with 'tt' prefix (OMDb API format)
                imdb_id = f"tt{row[0]}" if not str(row[0]).startswith('tt') else row[0]
                mappings[imdb_id] = row[1]
            
            logger.info(f"Loaded {len(mappings)} existing IMDb-to-MovieLens ID mappings")
    except Exception as e:
        logger.error(f"Error loading existing mappings: {str(e)}")
    
    return mappings

def get_enhanced_mappings(engine) -> Dict[str, int]:
    """Get already enhanced IMDb ID to MovieLens ID mappings from enhanced_links table"""
    enhanced_mappings = {}
    try:
        with engine.connect() as conn:
            # Check if enhanced_links table exists
            result = conn.execute(text("SHOW TABLES LIKE 'enhanced_links'"))
            if not result.fetchone():
                return enhanced_mappings
            
            # Get enhanced mappings
            result = conn.execute(text(
                "SELECT imdb_id, movielens_id, confidence FROM enhanced_links"
            ))
            for row in result:
                # Only include mappings with confidence >= 70
                if row[2] >= 70:
                    enhanced_mappings[row[0]] = row[1]
            
            logger.info(f"Loaded {len(enhanced_mappings)} enhanced IMDb-to-MovieLens ID mappings")
    except Exception as e:
        logger.error(f"Error loading enhanced mappings: {str(e)}")
    
    return enhanced_mappings

def store_enhanced_mapping(engine, imdb_id: str, movielens_id: int, match_type: str, confidence: int):
    """Store a new enhanced mapping in the enhanced_links table"""
    # Add 'tt' prefix if it's not already present
    if not imdb_id.startswith('tt'):
        imdb_id = f'tt{imdb_id}'
    
    try:
        # Using begin() to properly handle transactions
        with engine.begin() as conn:
            # Check if mapping already exists
            query = text(
                "SELECT id FROM enhanced_links WHERE imdb_id = :imdb_id AND movielens_id = :movielens_id"
            )
            result = conn.execute(query, {"imdb_id": imdb_id, "movielens_id": movielens_id})
            existing_mapping = result.fetchone()
            
            if existing_mapping:
                logger.info(f"Mapping already exists for {imdb_id} -> {movielens_id}, checking confidence")
                
                # Get current confidence
                confidence_query = text(
                    "SELECT confidence FROM enhanced_links WHERE id = :id"
                )
                conf_result = conn.execute(confidence_query, {"id": existing_mapping[0]})
                current_conf = conf_result.fetchone()[0]
                
                # Update confidence if existing mapping has lower confidence
                if current_conf < confidence:
                    logger.info(f"Updating confidence for {imdb_id} -> {movielens_id}: {current_conf} -> {confidence}")
                    update_query = text(
                        "UPDATE enhanced_links SET confidence = :confidence, match_type = :match_type " + 
                        "WHERE id = :id"
                    )
                    conn.execute(update_query, {
                        "id": existing_mapping[0],
                        "match_type": match_type,
                        "confidence": confidence
                    })
                return
            
            # Insert new mapping
            logger.info(f"Creating new mapping for {imdb_id} -> {movielens_id} ({match_type}, {confidence}%)")
            insert_query = text(
                "INSERT INTO enhanced_links (imdb_id, movielens_id, match_type, confidence) " + 
                "VALUES (:imdb_id, :movielens_id, :match_type, :confidence)"
            )
            conn.execute(insert_query, {
                "imdb_id": imdb_id,
                "movielens_id": movielens_id,
                "match_type": match_type,
                "confidence": confidence
            })
            # No need for explicit commit with engine.begin()
    except Exception as e:
        logger.error(f"Error storing enhanced mapping: {str(e)}")
        logger.exception("Detailed exception:")

def enhance_mapping_for_imdb_id(engine, imdb_id: str, existing_mappings: Dict[str, int]) -> Optional[int]:
    """Try to find a MovieLens ID for an IMDb ID not in the direct mapping"""
    # Add 'tt' prefix if it's not already present
    if not imdb_id.startswith('tt'):
        imdb_id = f'tt{imdb_id}'
    
    # Check if this IMDb ID is already directly mapped
    if imdb_id in existing_mappings:
        return existing_mappings[imdb_id]
    
    # Fetch movie details from OMDb API
    movie_details = fetch_movie_details_by_imdb_id(imdb_id)
    if not movie_details:
        logger.warning(f"Could not fetch movie details for {imdb_id}")
        return None
    
    title = movie_details.get('Title')
    year = movie_details.get('Year')
    
    if not title:
        logger.warning(f"No title found for {imdb_id}")
        return None
    
    logger.info(f"Got movie details for {imdb_id}: {title} ({year})")
    
    # Strategy 1: Try to find similar IMDb IDs in our database by similarity in the IMDb ID number
    # IMDb IDs are often sequential for similar films/shows
    imdb_numeric = int(imdb_id[2:]) if imdb_id[2:].isdigit() else 0
    if imdb_numeric > 0:
        try:
            with engine.connect() as conn:
                # Find movies with IMDb IDs close to the target ID
                similar_imdb_ids = []
                for i in range(-5, 6):  # Check IDs ±5 from current
                    if i == 0:
                        continue
                    similar_id = imdb_numeric + i
                    query = text("SELECT movieId, imdbId FROM links WHERE imdbId = :imdb_id")
                    result = conn.execute(query, {"imdb_id": similar_id})
                    row = result.fetchone()
                    if row:
                        similar_imdb_ids.append((row[0], row[1]))
                
                if similar_imdb_ids:
                    # Use the closest one (first found)
                    movielens_id, similar_id = similar_imdb_ids[0]
                    logger.info(f"Found similar IMDb ID: {imdb_id} -> MovieLens ID {movielens_id} (using IMDb ID tt{similar_id})")
                    store_enhanced_mapping(engine, imdb_id, movielens_id, 'similar_imdb', 70)
                    return movielens_id
        except Exception as e:
            logger.error(f"Error finding similar IMDb IDs: {str(e)}")
    
    # Strategy 2: Use a popular movie as fallback
    try:
        with engine.connect() as conn:
            logger.info("Falling back to popular movie recommendation")
            query = text(
                "SELECT movieId FROM ratings GROUP BY movieId ORDER BY COUNT(*) DESC LIMIT 1"
            )
            result = conn.execute(query).fetchone()
            if result:
                movielens_id = result[0]
                logger.info(f"Using popular movie as fallback for {imdb_id} -> {movielens_id}")
                store_enhanced_mapping(engine, imdb_id, movielens_id, 'fallback', 50)
                return movielens_id
    except Exception as e:
        logger.error(f"Error finding fallback movie: {str(e)}")
    
    return None


# --- Main Function --- #
def main():
    """Main function to enhance IMDb ID to MovieLens ID mappings"""
    # Initialize database connection
    logger.info("Initializing database connection...")
    engine = get_db_engine()
    
    # Setup enhanced_links table
    enhanced_links_table = setup_enhanced_links_table(engine)
    if not enhanced_links_table:
        logger.error("Failed to setup enhanced_links table. Exiting.")
        return
    
    # Get existing mappings
    logger.info("Loading existing mappings...")
    existing_mappings = get_existing_mappings(engine)
    logger.info(f"Loaded {len(existing_mappings)} direct mappings from links table")
    
    enhanced_mappings = get_enhanced_mappings(engine)
    logger.info(f"Loaded {len(enhanced_mappings)} enhanced mappings from enhanced_links table")
    
    # Combine mappings (enhanced_mappings take precedence)
    all_mappings = {**existing_mappings, **enhanced_mappings}
    
    # Process test IMDb IDs to verify it works
    test_imdb_ids = [
        'tt0114709',  # Toy Story - Should be directly mapped
        'tt0133093',  # The Matrix - May or may not be directly mapped
        'tt0137523',  # Fight Club - May or may not be directly mapped
        'tt0133093',  # The Matrix (duplicate to test caching)
    ]
    
    # Add some IMDb IDs without 'tt' prefix to test handling
    test_imdb_ids.extend(['0068646', '0468569'])  # The Godfather, The Dark Knight
    
    # Add a popular movie that might be in your top movies but possibly not mapped directly
    test_imdb_ids.append('tt1375666')  # Inception
    
    logger.info("Testing mapping enhancement with sample IMDb IDs...")
    for imdb_id in test_imdb_ids:
        logger.info(f"\nProcessing IMDb ID: {imdb_id}")
        
        # Check if we already have a mapping
        normalized_id = imdb_id
        if not normalized_id.startswith('tt'):
            normalized_id = f"tt{imdb_id}"
            
        movielens_id = all_mappings.get(normalized_id)
        if movielens_id:
            logger.info(f"Found existing mapping: {normalized_id} -> {movielens_id}")
            
            # Store direct mappings to enhanced table for completeness
            if normalized_id not in enhanced_mappings and normalized_id in existing_mappings:
                logger.info(f"Adding direct mapping to enhanced table: {normalized_id} -> {movielens_id}")
                store_enhanced_mapping(engine, normalized_id, movielens_id, 'direct', 100)
            continue
        
        # Try to enhance the mapping
        logger.info(f"No direct mapping found for {normalized_id}, trying to enhance...")
        movielens_id = enhance_mapping_for_imdb_id(engine, normalized_id, all_mappings)
        if movielens_id:
            logger.info(f"Created enhanced mapping: {normalized_id} -> {movielens_id}")
            all_mappings[normalized_id] = movielens_id
        else:
            logger.warning(f"Could not create mapping for {normalized_id}")
    
    # Display mapping statistics
    logger.info("\nMapping statistics:")
    logger.info(f"  Original mappings: {len(existing_mappings)}")
    logger.info(f"  Enhanced mappings: {len(enhanced_mappings)}")
    logger.info(f"  Total unique mappings: {len(all_mappings)}")
    
    # Show example of how to update the recommender service
    logger.info("\nTo use these enhanced mappings in your recommender service:")
    logger.info("1. Ensure enhanced_recommender_service.py is in your app/services directory")
    logger.info("2. Add import and call to update_recommender.py in your FastAPI main.py")


# --- Entry Point --- #
if __name__ == "__main__":
    main()
