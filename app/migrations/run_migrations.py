import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import the migration
from migrations.add_new_columns import run_migration

def main():
    """Run all migrations."""
    try:
        print("Starting migrations...")
        run_migration()
        print("All migrations completed successfully!")
    except Exception as e:
        print(f"Error running migrations: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 