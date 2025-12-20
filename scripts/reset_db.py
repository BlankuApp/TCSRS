"""
Reset database script for Supabase.
This script drops all tables and recreates them using init_db.sql
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file")
    sys.exit(1)


def reset_database():
    """Drop all tables and recreate them."""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        print("🗑️  Dropping existing tables...")
        
        # Drop tables in reverse order of dependencies
        drop_statements = [
            "DROP TABLE IF EXISTS cards CASCADE;",
            "DROP TABLE IF EXISTS topics CASCADE;",
            "DROP TABLE IF EXISTS decks CASCADE;",
            "DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;"
        ]
        
        for statement in drop_statements:
            try:
                supabase.rpc('exec_sql', {'sql': statement}).execute()
                print(f"  ✓ Executed: {statement}")
            except Exception as e:
                print(f"  ⚠️  Warning: {statement} - {str(e)}")
        
        print("\n📝 Creating tables from init_db.sql...")
        
        # Read and execute init_db.sql
        init_sql_path = Path(__file__).parent / "init_db.sql"
        with open(init_sql_path, 'r') as f:
            init_sql = f.read()
        
        # Split by statement and execute
        statements = [s.strip() for s in init_sql.split(';') if s.strip()]
        
        for statement in statements:
            if statement:
                try:
                    supabase.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"  ✓ Executed statement")
                except Exception as e:
                    print(f"  ⚠️  Warning: {str(e)}")
        
        print("\n✅ Database reset complete!")
        
    except Exception as e:
        print(f"\n❌ Error resetting database: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("Topic-Centric SRS - Database Reset")
    print("=" * 60)
    print("\n⚠️  WARNING: This will delete all data in the database!")
    
    response = input("\nAre you sure you want to continue? (yes/no): ")
    
    if response.lower() == 'yes':
        reset_database()
    else:
        print("\n❌ Reset cancelled.")
