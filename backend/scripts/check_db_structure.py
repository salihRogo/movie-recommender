"""
Script to check database structure
"""
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Get database URL from environment
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("DATABASE_URL not set in environment")
    sys.exit(1)

# Create engine
engine = create_engine(database_url)

# Use inspector to get schema information
inspector = inspect(engine)
print("Tables in database:", inspector.get_table_names())

# Check links table structure
print("\nStructure of links table:")
for column in inspector.get_columns('links'):
    print(f"  {column['name']} ({column['type']}) {'' if column.get('nullable', True) else 'NOT NULL'}")

# Check primary keys
print("\nPrimary keys of links table:")
for pk in inspector.get_pk_constraint('links').get('constrained_columns', []):
    print(f"  {pk}")

# Check ratings table structure if it exists
if 'ratings' in inspector.get_table_names():
    print("\nStructure of ratings table:")
    for column in inspector.get_columns('ratings'):
        print(f"  {column['name']} ({column['type']}) {'' if column.get('nullable', True) else 'NOT NULL'}")

# Sample data from links table
print("\nSample data from links table (first 5 rows):")
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM links LIMIT 5"))
    for row in result:
        print(f"  {row}")
