import os
from fastapi import FastAPI, Request
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
from app.routes import resume, search
from app.models import init_db
from dotenv import load_dotenv
from pathlib import Path
from app.auth.clerk import get_current_user

# Get the app directory path
APP_DIR = Path(__file__).resolve().parent
ENV_PATH = APP_DIR / '.env'

# Load dotenv only in development mode
if os.getenv('ENV', 'development') == "development":
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    else:
        print(f"Warning: .env file not found at {ENV_PATH}")

# Initialize FastAPI app
app = FastAPI(
    title="PeopleGPT API",
    description="AI-powered talent acquisition and screening platform",
    version="1.0.0"
)

# Allow all origins (dev only, restrict in prod)
origins = ["http://localhost:8080", "https://main.d3r5nh3ds41tf9.amplifyapp.com"]  # Replace with your frontend URL in production (e.g., "https://yourfrontend.com")

# CORS middleware must be added before including routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or use allow_origin_regex for dynamic domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to inject user ID
@app.middleware("http")
async def add_user_id(request: Request, call_next):
    try:
        user_id = get_current_user(request)
        request.state.user_id = user_id
    except Exception:
        request.state.user_id = None
    response = await call_next(request)
    return response

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

# Routers
app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(search.router, prefix="/api/search", tags=["search"])

# Root route
@app.get("/")
async def root():
    return {"message": "Welcome to PeopleGPT APIs from hireAI"}

# AWS Lambda handler
handler = Mangum(app)
