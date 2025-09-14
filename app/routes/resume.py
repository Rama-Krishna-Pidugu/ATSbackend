from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from app.services.resume_parser import ResumeParser
from app.models import ResumeUploadResponse, Resume, get_db
from app.services.database import store_resume, get_resume, get_all_resumes, search_resumes
from app.services.aws import s3, S3_BUCKET
from app.auth.clerk import get_current_user
import os
import uuid
from typing import Optional, List
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.services.search_engine import SearchEngine

router = APIRouter()
resume_parser = ResumeParser()
search_engine = SearchEngine()  # Initialize the search engine

@router.post("/upload/", response_model=ResumeUploadResponse)
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload and parse a resume."""
    try:
        # Get user_id from Clerk token
        user_id = get_current_user(request)
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
            
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
            
        if not file.filename.lower().endswith(('.pdf', '.doc', '.docx')):
            raise HTTPException(status_code=400, detail="Only PDF and Word documents are allowed")
        
        # Generate a unique filename for S3
        timestamp = int(time.time())
        file_extension = os.path.splitext(file.filename)[1]
        s3_key = f"resumes/{user_id}/{timestamp}_{uuid.uuid4()}{file_extension}"
        
        # Read file content
        file_content = await file.read()
        
        # Upload to S3
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type
        )
        
        # Get the file from S3 for parsing
        s3_response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        file_content = s3_response['Body'].read()
        
        # Parse the resume
        result = resume_parser.parse_resume_text(file_content)
        
        # Add user_id and S3 file location to result
        result['user_id'] = user_id
        result['s3_location'] = f"s3://{S3_BUCKET}/{s3_key}"
        
        # Generate embedding for the resume
        text_parts = [
            result.get('summary', ''),
            ' '.join(result.get('skills', [])),
            result.get('experience', ''),
            result.get('education', ''),
            ' '.join(str(v) for v in result.get('contact', {}).values())
        ]
        text_blob = ' '.join(filter(None, text_parts))
        
        # Create embedding using the search engine
        embedding = search_engine.model.encode(text_blob)
        result['embedding'] = embedding.tolist()
        
        # Store in database
        db_resume = await store_resume(db, result)
        
        # Convert to ResumeUploadResponse
        response = ResumeUploadResponse(
            name=db_resume.name,
            skills=db_resume.skills,
            experience=db_resume.experience,
            education=db_resume.education,
            contact=db_resume.contact,
            summary=db_resume.summary,
            s3_location=db_resume.s3_location,
            created_at=db_resume.created_at
        )
        
        return response
        
    except Exception as e:
        # If there's an error, try to clean up the S3 object
        try:
            if 's3_key' in locals():
                s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")

@router.get("/resumes/{resume_id}", response_model=ResumeUploadResponse)
async def get_resume_by_id(resume_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific resume by ID."""
    resume = await get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume

@router.get("/resumes/", response_model=List[ResumeUploadResponse])
async def list_resumes(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """List all resumes with pagination."""
    return await get_all_resumes(db, skip, limit)

@router.get("/resumes/search/", response_model=List[ResumeUploadResponse])
async def search_resumes_by_query(query: str, db: AsyncSession = Depends(get_db)):
    """Search resumes by name, skills, or summary."""
    return await search_resumes(db, query) 