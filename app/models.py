from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, Integer, String, JSON, DateTime, Text, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from datetime import datetime
from pathlib import Path
from jose import jwt
from fastapi import Header, HTTPException, Depends

# Get the app directory path
APP_DIR = Path(__file__).resolve().parent
ENV_PATH = APP_DIR / '.env'

# Load environment variables
if ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)

# SQLAlchemy setup
Base = declarative_base()

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)  # Clerk's user ID
    name = Column(String(255), nullable=False)
    skills = Column(JSON, nullable=True)
    experience = Column(String(255), nullable=True)
    education = Column(Text, nullable=True)
    contact = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    s3_location = Column(String(255), nullable=True)
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    certifications = Column(JSON, nullable=True)
    work_history = Column(JSON, nullable=True)

# Create database engine and session
DATABASE_URL = f"mysql+aiomysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=True
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Dependency to get database session
async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# Authentication dependencies
CLERK_JWT_PUBLIC_KEY = os.getenv("CLERK_JWT_PUBLIC_KEY")

async def get_current_user(authorization: str = Header(...)) -> str:
    """Extract and validate the user ID from the JWT token."""
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
            
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, CLERK_JWT_PUBLIC_KEY, algorithms=["RS256"])
        return payload["sub"]  # Clerk uses 'sub' as the unique user ID
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

class ResumeUploadResponse(BaseModel):
    name: str
    skills: List[str]
    experience: str
    education: str
    contact: Dict[str, str]
    summary: str
    s3_location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    certifications: Optional[List[str]] = []
    work_history: Optional[List[Dict[str, Any]]] = []

    class Config:
        from_attributes = True

class SearchQuery(BaseModel):
    query: str
    location: Optional[str] = None
    experience_years: Optional[int] = None

class SearchResult(BaseModel):
    name: str
    skills: List[str]
    score: float
    experience: str
    location: Optional[str] = None

class SearchResponse(BaseModel):
    matches: List[Dict[str, Any]]
    analysis: str

class ScreeningRequest(BaseModel):
    skill: str
    level: str = Field(..., description="junior, mid, or senior")

class ScreeningResponse(BaseModel):
    questions: List[str]

class EmailRequest(BaseModel):
    name: str
    skill: str
    company_name: Optional[str] = None
    position: Optional[str] = None

class EmailResponse(BaseModel):
    email: str

class BackgroundCheckRequest(BaseModel):
    name: str
    location: str

class BackgroundCheckResponse(BaseModel):
    status: str
    details: str 