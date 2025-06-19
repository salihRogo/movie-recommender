#!/usr/bin/env python
"""Test script for enhanced IMDb ID to MovieLens ID mapping

This script tests the enhanced recommender service by sending requests to the API
with IMDb IDs that previously had no mappings.
"""

import sys
import asyncio
import json
import logging
from pathlib import Path
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to Python path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BACKEND_DIR))

# Test IMDb IDs - including some that were not directly mapped before
TEST_IMDB_IDS = [
    "tt0114709",  # Toy Story - now mapped via similar IMDb ID
    "tt0133093",  # The Matrix - now mapped via similar IMDb ID 
    "tt0137523",  # Fight Club - now mapped via fallback
    "tt0068646",  # The Godfather - now mapped via similar IMDb ID
    "tt0468569",  # The Dark Knight - now mapped via similar IMDb ID
    "tt1375666",  # Inception - had original mapping
]

async def test_profile_recommendations():
    """Test profile recommendations with enhanced mapping."""
    url = "http://localhost:8000/recommendations/by_profile"
    
    # Create a profile with our test IMDb IDs
    profile = {
        "imdb_ids": TEST_IMDB_IDS
    }
    
    logger.info(f"Testing profile recommendations with IMDb IDs: {TEST_IMDB_IDS}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=profile)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully got {len(data['recommendations'])} recommendations")
                logger.info(f"Message: {data.get('message', 'No message')}")
                logger.info(f"First few recommendations: {json.dumps(data['recommendations'][:3], indent=2) if data['recommendations'] else 'None'}")
                return True
            else:
                logger.error(f"API request failed with status code: {response.status_code}")
                logger.error(f"Response content: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error making API request: {str(e)}")
        return False

async def test_individual_recommendations():
    """Test individual IMDb ID recommendations with enhanced mapping."""
    url = "http://localhost:8000/recommendations/by_profile"
    
    for imdb_id in TEST_IMDB_IDS:
        logger.info(f"\nTesting recommendations for IMDb ID: {imdb_id}")
        
        # Create a profile with just this one IMDb ID
        profile = {
            "imdb_ids": [imdb_id]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=profile)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Successfully got {len(data['recommendations'])} recommendations")
                    logger.info(f"Message: {data.get('message', 'No message')}")
                    if data['recommendations']:
                        logger.info(f"First recommendation: {json.dumps(data['recommendations'][0], indent=2)}")
                    else:
                        logger.info("No recommendations returned")
                else:
                    logger.error(f"API request failed with status code: {response.status_code}")
                    logger.error(f"Response content: {response.text}")
        except Exception as e:
            logger.error(f"Error making API request for {imdb_id}: {str(e)}")

async def main():
    """Run the test suite."""
    logger.info("Starting enhanced mapping test...")
    
    # Test profile recommendations
    await test_profile_recommendations()
    
    # Test individual IMDb ID recommendations
    await test_individual_recommendations()
    
    logger.info("Testing complete.")

if __name__ == "__main__":
    asyncio.run(main())
