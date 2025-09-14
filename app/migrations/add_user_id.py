from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    # Get database connection details from environment
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')
    database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
    
    # Create engine
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check if user_id column exists
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.columns 
                WHERE table_schema = :db_name 
                AND table_name = 'resumes' 
                AND column_name = 'user_id'
            """), {"db_name": db_name})
            
            if result.scalar() == 0:
                print("Adding user_id column to resumes table...")
                # Add user_id column
                conn.execute(text("""
                    ALTER TABLE resumes 
                    ADD COLUMN user_id VARCHAR(255) NOT NULL DEFAULT 'default_user'
                """))
                print("Successfully added user_id column")
            else:
                print("user_id column already exists")
                
            # Commit the transaction
            conn.commit()
            
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        raise

if __name__ == "__main__":
    run_migration() 