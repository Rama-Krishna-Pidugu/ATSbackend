from sqlalchemy import create_engine, text
import os
from pathlib import Path

# Get the app directory path
APP_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = APP_DIR / '.env'

# Load environment variables
if ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)

# Database connection
DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

def run_migration():
    """Add new columns to the resumes table."""
    try:
        with engine.connect() as connection:
            # Add certifications column
            connection.execute(text("""
                ALTER TABLE resumes 
                ADD COLUMN certifications JSON NULL
            """))
            
            # Add work_history column
            connection.execute(text("""
                ALTER TABLE resumes 
                ADD COLUMN work_history JSON NULL
            """))
            
            connection.commit()
            print("Migration completed successfully!")
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        raise

if __name__ == "__main__":
    run_migration() 