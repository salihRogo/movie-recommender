import logging
from typing import List, Optional
from sqlalchemy import create_engine, text, inspect

from ..core.config import settings

logger = logging.getLogger(__name__)


class MovieDataService:
    """Service for handling database interactions related to movie data."""

    def __init__(self):
        """Initialize the database service and create the engine."""
        self._db_engine = None
        self._mapping_stats = {
            'direct_hits': 0,
            'enhanced_hits': 0,
            'misses': 0,
            'total_requests': 0,
            'errors': 0
        }
        try:
            self._db_engine = create_engine(settings.DATABASE_URL)
            logger.info("Database engine created for MovieDataService.")
            self._verify_enhanced_links_table()
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            self._db_engine = None

    def _verify_enhanced_links_table(self):
        """Check if the enhanced_links table exists and has data."""
        if not self._db_engine:
            logger.error("Database engine not initialized, cannot verify enhanced_links table")
            return
            
        try:
            inspector = inspect(self._db_engine)
            tables = inspector.get_table_names()
            
            if 'enhanced_links' not in tables:
                logger.warning("Enhanced links table does not exist in database. Only standard mapping will be used.")
                return
                
            with self._db_engine.connect() as connection:
                result = connection.execute(text("SELECT COUNT(*) FROM enhanced_links")).fetchone()
                count = result[0] if result else 0
                logger.info(f"Enhanced links table contains {count} mappings")
                if count == 0:
                    logger.warning("Enhanced links table exists but contains no data")
                    
        except Exception as e:
            logger.error(f"Error verifying enhanced_links table: {str(e)}")

    def get_raw_movie_id_from_imdb_id(self, imdb_id: str) -> Optional[str]:
        """Get MovieLens ID from IMDb ID using both direct and enhanced mappings."""
        if not self._db_engine:
            logger.error("Database engine not available for ID mapping.")
            return None

        self._mapping_stats['total_requests'] += 1
        clean_imdb_id = imdb_id.replace('tt', '')
        
        try:
            with self._db_engine.connect() as connection:
                query = text("SELECT movieId FROM enhanced_links WHERE imdbId = :imdb_id")
                result = connection.execute(query, {"imdb_id": clean_imdb_id}).fetchone()
                
                if result:
                    self._mapping_stats['enhanced_hits'] += 1
                    return str(result[0])
        except Exception as e:
            self._mapping_stats['errors'] += 1
            logger.error(f"Error querying enhanced_links for IMDb ID {clean_imdb_id}: {e}")

        self._mapping_stats['misses'] += 1
        return None

    def get_imdb_ids_from_raw_ids(self, raw_ids: List[str]) -> List[str]:
        """Convert raw item IDs to IMDb IDs."""
        if not self._db_engine:
            logger.error("Database engine not available for ID mapping.")
            return []

        imdb_ids = []
        for raw_id in raw_ids:
            if str(raw_id).startswith('tt'):
                imdb_ids.append(str(raw_id))
                continue

            try:
                with self._db_engine.connect() as connection:
                    query = text("SELECT imdbId FROM enhanced_links WHERE movieId = :movie_id")
                    result = connection.execute(query, {"movie_id": raw_id}).fetchone()
                    if result and result[0]:
                        imdb_id = f"tt{result[0]}"
                        imdb_ids.append(imdb_id)
            except Exception as e:
                logger.error(f"Error fetching imdb id from raw id {raw_id}: {e}")
        return imdb_ids

def get_movie_data_service():
    """Dependency injector for MovieDataService."""
    return MovieDataService()
