import os
import boto3
from dotenv import load_dotenv
from pathlib import Path

# Get the app directory path
APP_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = APP_DIR / '.env'

# Load dotenv only in development mode
dev = os.getenv('ENV', 'development')
if dev == "development":
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    else:
        print(f"Warning: .env file not found at {ENV_PATH}")

# AWS Configuration
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

if not S3_BUCKET:
    raise RuntimeError("S3_BUCKET environment variable not set")

# Initialize S3 client
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION
) 