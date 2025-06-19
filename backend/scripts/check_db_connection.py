import sys
from pathlib import Path
from sqlalchemy import create_engine, text
import pandas as pd

# Add backend app directory to sys.path to allow absolute imports
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings

def check_connection():
    """Checks the database connection using the URL from settings."""
    if not settings.DATABASE_URL:
        print("Error: DATABASE_URL is not set in your .env file.")
        return

    # Hide credentials for printing
    db_identifier = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL
    print(f"Attempting to connect to: {db_identifier}...")

    try:
        # Create an engine
        engine = create_engine(settings.DATABASE_URL)

        # Try to connect
        with engine.connect() as connection:
            print("\n*** SUCCESS! Connection established. ***")
            print("\nVerifying data presence by fetching first 5 ratings...")
            query = text("SELECT * FROM ratings LIMIT 5;")
            result_df = pd.read_sql_query(query, connection)

            if not result_df.empty:
                print("*** SUCCESS! Data fetched successfully. ***\n")
                print("Sample data from 'ratings' table:")
                print(result_df.to_string())
            else:
                print("\n*** WARNING! ***")
                print("Connection successful, but could not fetch data. The 'ratings' table might be empty.")

    except Exception as e:
        print("\n*** FAILURE! ***")
        print("Failed to connect to the database.")
        print(f"Error details: {e}")

if __name__ == '__main__':
    check_connection()
