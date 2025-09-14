from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models import Resume
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

async def store_resume(db: AsyncSession, resume_data: dict) -> Resume:
    """Store a resume in the database."""
    try:
        # Ensure user_id is present
        if not resume_data.get('user_id'):
            raise ValueError("user_id is required")

        # Create a new Resume instance
        resume = Resume(
            user_id=resume_data['user_id'],
            name=resume_data['name'],
            skills=resume_data.get('skills', []),
            experience=resume_data.get('experience'),
            education=resume_data.get('education'),
            contact=resume_data.get('contact', {}),
            summary=resume_data.get('summary'),
            s3_location=resume_data.get('s3_location'),
            embedding=resume_data.get('embedding'),
            created_at=datetime.utcnow(),
            certifications=resume_data.get('certifications', []),
            work_history=resume_data.get('work_history', [])
        )

        # Add to database
        db.add(resume)
        await db.commit()
        await db.refresh(resume)
        
        return resume
    except Exception as e:
        await db.rollback()
        raise Exception(f"Error storing resume: {str(e)}")

async def get_resume(db: AsyncSession, resume_id: int) -> Resume:
    """Get a resume by ID."""
    result = await db.execute(
        text("SELECT * FROM resumes WHERE id = :id"),
        {"id": resume_id}
    )
    return result.fetchone()

async def get_all_resumes(db: AsyncSession, skip: int = 0, limit: int = 100) -> list:
    """Get all resumes with pagination."""
    result = await db.execute(
        text("SELECT * FROM resumes LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip}
    )
    return result.fetchall()

async def search_resumes(db: AsyncSession, query: str) -> list:
    """Search resumes by query."""
    result = await db.execute(
        text("""
            SELECT * FROM resumes 
            WHERE name LIKE :query 
            OR summary LIKE :query 
            OR skills LIKE :query
        """),
        {"query": f"%{query}%"}
    )
    return result.fetchall() 