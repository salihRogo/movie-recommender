"""Diagnose Model Coverage

This script diagnoses model coverage issues by:
1. Loading the model data
2. Checking for specific IMDb IDs in the test profiles
3. Verifying if the mapped MovieLens IDs are in the model
4. Generating a detailed report of missing mappings and model items
"""

import sys
from pathlib import Path
import logging
import time
import joblib
from sqlalchemy import create_engine, text
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add backend directory to path for imports
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Import settings from app
from app.core.config import settings

class ModelDiagnostic:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.models_dir = BACKEND_DIR / "models"
        self.stats = {
            'model_items': 0,
            'enhanced_links': 0,
            'test_items': 0,
            'items_in_model': 0,
            'items_with_direct_mapping': 0,
            'items_with_enhanced_mapping': 0
        }
        
        # Test profile IMDb IDs from test_enhanced_mapping.py
        self.test_imdb_ids = [
            "tt0111161", "tt0068646", "tt0071562", "tt0468569", 
            "tt0050083", "tt0108052", "tt0167260", "tt0110912", 
            "tt0060196", "tt0120737", "tt0137523", "tt0109830", 
            "tt1375666", "tt0080684"
        ]
    
    def load_model_data(self):
        """Load model data from joblib files"""
        try:
            # Load model mapping data
            self.raw_to_inner_iid_map = joblib.load(self.models_dir / "raw_to_inner_iid_map.joblib")
            self.all_movie_imdb_ids = joblib.load(self.models_dir / "all_movie_imdb_ids.joblib")
            self.inner_to_raw_iid_map = joblib.load(self.models_dir / "inner_to_raw_iid_map.joblib")
            
            # Count items
            self.stats['model_items'] = len(self.all_movie_imdb_ids)
            logger.info(f"Loaded mapping for {self.stats['model_items']} movies in the model")
            return True
        except FileNotFoundError as e:
            logger.error(f"Could not load model files: {e}")
            return False
    
    def get_enhanced_mappings(self):
        """Get enhanced mappings from database"""
        try:
            with self.engine.connect() as connection:
                # Get all enhanced mappings
                result = connection.execute(text("SELECT imdb_id, movielens_id, match_type, confidence FROM enhanced_links"))
                self.enhanced_mappings = {row[0]: {"movielens_id": row[1], "match_type": row[2], "confidence": row[3]} 
                                         for row in result.fetchall()}
                self.stats['enhanced_links'] = len(self.enhanced_mappings)
                logger.info(f"Found {len(self.enhanced_mappings)} enhanced mappings in the database")
                return True
        except Exception as e:
            logger.error(f"Error fetching enhanced mappings: {e}")
            return False
    
    def get_direct_mappings(self):
        """Get direct mappings from links table"""
        try:
            with self.engine.connect() as connection:
                # Get all direct mappings
                result = connection.execute(text("SELECT imdbId, movieId FROM links"))
                self.direct_mappings = {f"tt{row[0]}": str(row[1]) for row in result.fetchall()}
                logger.info(f"Found {len(self.direct_mappings)} direct mappings in the database")
                return True
        except Exception as e:
            logger.error(f"Error fetching direct mappings: {e}")
            return False
    
    def check_test_profile_coverage(self):
        """Check if test profile IMDb IDs are covered by the model"""
        self.stats['test_items'] = len(self.test_imdb_ids)
        
        # Check each test IMDb ID
        self.test_results = []
        for imdb_id in self.test_imdb_ids:
            result = {
                "imdb_id": imdb_id,
                "in_model_directly": imdb_id in self.raw_to_inner_iid_map,
                "has_enhanced_mapping": imdb_id in self.enhanced_mappings,
                "has_direct_mapping": imdb_id in self.direct_mappings,
            }
            
            if result["in_model_directly"]:
                self.stats['items_in_model'] += 1

            # Check for direct mapping from 'links' table
            if imdb_id in self.direct_mappings:
                result["has_direct_mapping"] = True
                result["direct_mapped_movielens_id"] = self.direct_mappings[imdb_id]
                self.stats['items_with_direct_mapping'] += 1
            
            # Check for enhanced mapping from 'enhanced_links' table
            if imdb_id in self.enhanced_mappings:
                result["has_enhanced_mapping"] = True
                result["enhanced_mapped_movielens_id"] = self.enhanced_mappings[imdb_id]["movielens_id"]
                result["enhanced_mapping_type"] = self.enhanced_mappings[imdb_id]["match_type"]
                result["enhanced_mapping_confidence"] = self.enhanced_mappings[imdb_id].get("confidence", 0) * 100
                self.stats['items_with_enhanced_mapping'] += 1

            self.test_results.append(result)
    
    def print_report(self):
        """Print a detailed diagnostic report"""
        print("\n" + "="*80)
        print("MODEL COVERAGE DIAGNOSTIC REPORT")
        print("="*80)
        
        print(f"\nOverall Statistics:")
        print(f"- Total movies in model: {self.stats['model_items']}")
        print(f"- Enhanced mappings in database: {self.stats['enhanced_links']}")
        print(f"- Direct mappings in links table: {len(self.direct_mappings)}")
        print(f"- Test profile items: {self.stats['test_items']}")
        print(f"- Test items directly in model (IMDb ID in raw_to_inner_iid_map): {self.stats['items_in_model']} ({self.stats['items_in_model']/self.stats['test_items']*100:.1f}%)")
        print(f"- Test items with direct DB mapping (in 'links' table): {self.stats['items_with_direct_mapping']} ({self.stats['items_with_direct_mapping']/self.stats['test_items']*100:.1f}%)")
        print(f"- Test items with enhanced DB mapping (in 'enhanced_links' table): {self.stats['items_with_enhanced_mapping']} ({self.stats['items_with_enhanced_mapping']/self.stats['test_items']*100:.1f}%)")

        print("\nDetailed Test Profile Results:")
        for result in self.test_results:
            status_model = "✅" if result["in_model_directly"] else "❌"
            status_direct_map = "✅" if result["has_direct_mapping"] else "❌"
            status_enhanced_map = "✅" if result["has_enhanced_mapping"] else "❌"
            
            print(f"\nIMDb ID: {result['imdb_id']}")
            print(f"   {status_model} Directly in model (as IMDb ID): {result['in_model_directly']}")
            print(f"   {status_direct_map} Has direct DB mapping (links table): {result['has_direct_mapping']}")
            if result["has_direct_mapping"]:
                print(f"     └── Direct MovieLens ID: {result['direct_mapped_movielens_id']}")
            print(f"   {status_enhanced_map} Has enhanced DB mapping (enhanced_links table): {result['has_enhanced_mapping']}")
            if result["has_enhanced_mapping"]:
                print(f"     └── Enhanced MovieLens ID: {result['enhanced_mapped_movielens_id']}")
                print(f"     └── Enhanced Mapping Type: {result['enhanced_mapping_type']}")
                print("     └── Enhanced Mapping Confidence: {}%".format(result.get('enhanced_mapping_confidence', 'N/A')))

        print("\n" + "="*80)
        print("RECOMMENDATIONS / OBSERVATIONS")
        print("="*80)

        if self.stats['items_in_model'] < self.stats['test_items']:
            print("\n- Some test IMDb IDs are not directly included in the trained model.")
            print("  Consider:")
            print("    1. Ensuring these IMDb IDs have ratings in the 'ratings' table used for training.")
            print("    2. Verifying 'train_model_from_db.py' correctly processes and includes them.")
        
        missing_all_coverage = [r['imdb_id'] for r in self.test_results if not r["in_model_directly"] and not r["has_direct_mapping"] and not r["has_enhanced_mapping"]]
        if missing_all_coverage:
            print("\n- The following IMDb IDs have NO model coverage AND NO DB mappings (direct or enhanced):")
            for imdb_id in missing_all_coverage:
                print(f"  - {imdb_id}")
            print("  These items will likely result in fallback to popular movies if used in a profile.")

        print("\n- For IMDb IDs not directly in the model, the UnifiedRecommenderService will attempt to use direct or enhanced DB mappings to find a corresponding MovieLens ID, and then check if *that MovieLens ID* has an equivalent IMDb ID that *is* in the model. This script does not simulate that final step.")

    
    def run_diagnostic(self):
        """Run the full diagnostic"""
        if not self.load_model_data():
            return False
            
        if not self.get_enhanced_mappings():
            return False
            
        if not self.get_direct_mappings():
            return False
            
        self.check_test_profile_coverage()
        self.print_report()
        
        return True

def main():
    """Main function"""
    logger.info("Starting model coverage diagnostic")
    diagnostic = ModelDiagnostic()
    success = diagnostic.run_diagnostic()
    
    if success:
        logger.info("Model coverage diagnostic completed successfully")
    else:
        logger.error("Model coverage diagnostic failed")

if __name__ == "__main__":
    main()
