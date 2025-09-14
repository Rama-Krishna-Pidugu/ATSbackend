from fastapi import APIRouter, HTTPException, Depends
from app.services.search_engine import SearchEngine
from app.models import SearchQuery, SearchResponse, get_db, get_current_user
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import sqlite3
from app.services.screening_generator import ScreeningGenerator
from app.services.email_generator import EmailGenerator
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.auth.clerk import get_current_user
from fastapi import Request

router = APIRouter()
search_engine = SearchEngine()
screening_generator = ScreeningGenerator()
email_generator = EmailGenerator()

@router.get("/all/", response_model=List[Dict[str, Any]])
async def get_all_resumes(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all resumes from the database for the current user."""
    try:
        # Get user_id from Clerk token
        user_id = get_current_user(request)
        print(user_id)
        query = text("""
            SELECT id, name, skills, experience, education, contact, summary 
            FROM resumes
            WHERE user_id = :user_id
        """)
        result = await db.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "name": row[1],
                "skills": json.loads(row[2]) if row[2] else [],
                "experience": row[3],
                "education": row[4],
                "contact": json.loads(row[5]) if row[5] else {},
                "summary": row[6]
            })

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving resumes: {str(e)}")

@router.post("/search/", response_model=List[Dict[str, Any]])
async def search_candidates(
    query: SearchQuery,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Search candidates based on query parameters using semantic search."""
    try:
        # Verify database state before searching
        search_engine.verify_database()
        
        # Use the search engine's semantic search with user_id filter
        results = search_engine.search(
            query=query.query,
            location=query.location,
            experience_years=query.experience_years,
            user_id=user_id
        )
        
        if not results or not results.get("matches"):
            return []
            
        # Process and return the matches
        processed_results = []
        for match in results["matches"]:
            try:
                # Ensure skills and contact are properly parsed
                skills = match["skills"]
                if isinstance(skills, str):
                    try:
                        skills = json.loads(skills)
                    except json.JSONDecodeError:
                        skills = []
                
                contact = match["contact"]
                if isinstance(contact, str):
                    try:
                        contact = json.loads(contact)
                    except json.JSONDecodeError:
                        contact = {}
                
                processed_results.append({
                    "id": match["id"],
                    "name": match["name"],
                    "skills": skills,
                    "experience": match["experience"],
                    "education": match["education"],
                    "contact": contact,
                    "summary": match["summary"],
                    "similarity_score": match.get("similarity_score", 0)
                })
            except Exception as e:
                print(f"Error processing match: {str(e)}")
                continue
        
        return processed_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching candidates: {str(e)}")

@router.get("/resumes/{resume_id}", response_model=Dict[str, Any])
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Get a specific resume by ID."""
    try:
        query = text("""
            SELECT id, name, skills, experience, education, contact, summary 
            FROM resumes 
            WHERE id = :resume_id AND user_id = :user_id
        """)
        result = await db.execute(query, {
            "resume_id": resume_id,
            "user_id": user_id
        })
        resume = result.fetchone()
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
            
        return {
            "id": resume[0],
            "name": resume[1],
            "skills": json.loads(resume[2]) if resume[2] else [],
            "experience": resume[3],
            "education": resume[4],
            "contact": json.loads(resume[5]) if resume[5] else {},
            "summary": resume[6]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving resume: {str(e)}")

@router.post("/add-candidate/")
async def add_candidate(
    candidate: dict,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Add a new candidate to the search index."""
    try:
        # Add user_id to the candidate data
        candidate["user_id"] = user_id
        search_engine.add_candidate(candidate)
        return {"message": "Candidate added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding candidate: {str(e)}")

@router.delete("/clear-index/")
async def clear_index(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Clear the search index for the current user."""
    try:
        # Only clear resumes for the current user
        query = text("DELETE FROM resumes WHERE user_id = :user_id")
        await db.execute(query, {"user_id": user_id})
        await db.commit()
        return {"message": "Search index cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing index: {str(e)}")

@router.get("/resume/{resume_id}", response_model=Dict[str, Any])
async def get_resume_details(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Get detailed information about a specific resume."""
    try:
        query = text("""
            SELECT id, name, skills, experience, education, contact, summary, created_at
            FROM resumes 
            WHERE id = :resume_id AND user_id = :user_id
        """)
        result = await db.execute(query, {
            "resume_id": resume_id,
            "user_id": user_id
        })
        resume = result.fetchone()
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
            
        # Parse the resume data
        resume_data = {
            "id": resume[0],
            "name": resume[1],
            "skills": json.loads(resume[2]) if resume[2] else [],
            "experience": resume[3],
            "education": resume[4],
            "contact": json.loads(resume[5]) if resume[5] else {},
            "summary": resume[6],
            "created_at": resume[7]
        }
        
        # Extract first name
        first_name = resume_data["name"].split()[0] if resume_data["name"] else ""
        
        # Parse education details
        education_details = []
        if resume_data["education"]:
            education_parts = [part.strip() for part in resume_data["education"].split(",")]
            for part in education_parts:
                if part:
                    education_details.append({
                        "degree": part,
                        "year": None,
                        "institution": None
                    })
        
        # Extract certifications
        certifications = []
        if resume_data["education"]:
            cert_keywords = ["CPA", "CA", "CMA", "Certified", "Professional", "Associate"]
            for part in education_parts:
                if any(keyword in part for keyword in cert_keywords):
                    certifications.append({
                        "name": part,
                        "issuing_organization": None,
                        "year": None
                    })
        
        # Structure the response
        detailed_response = {
            "basic_info": {
                "id": resume_data["id"],
                "first_name": first_name,
                "full_name": resume_data["name"],
                "experience_years": resume_data["experience"],
                "summary": resume_data["summary"]
            },
            "contact_info": resume_data["contact"],
            "skills": resume_data["skills"],
            "education": {
                "details": education_details,
                "certifications": certifications
            },
            "work_experience": {
                "summary": resume_data["experience"],
                "details": []
            },
            "created_at": resume_data["created_at"]
        }
        
        return detailed_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving resume details: {str(e)}")

@router.get("/resume/{resume_id}/screening-questions")
async def get_screening_questions(resume_id: int, db: AsyncSession = Depends(get_db)):
    """Generate AI screening questions for a candidate based on their skills and experience."""
    try:
        result = await db.execute("SELECT name, skills, experience FROM resumes WHERE id = ?", (resume_id,))
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Resume not found")
        name, skills_json, experience = row
        skills = json.loads(skills_json) if skills_json else []
        # Use the top skill or fallback
        skill = skills[0] if skills else "developer"
        questions = screening_generator.generate_questions(skill=skill, level="senior" if experience and ("5" in experience or "senior" in experience.lower()) else "mid")
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating screening questions: {str(e)}")

@router.post("/resume/{resume_id}/generate-email")
async def generate_outreach_email(resume_id: int, template: str = "initial_outreach", db: AsyncSession = Depends(get_db)):
    """Generate an outreach email for a candidate based on a template."""
    try:
        result = await db.execute("SELECT name, skills, experience FROM resumes WHERE id = ?", (resume_id,))
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Resume not found")
        name, skills_json, experience = row
        skills = json.loads(skills_json) if skills_json else []
        skill = skills[0] if skills else "developer"
        key_skills = ", ".join(skills) if skills else skill
        # You can expand template logic as needed
        company_name = os.getenv("COMPANY_NAME", "Our Company")
        position = os.getenv("POSITION_TITLE", "Developer")
        location = os.getenv("COMPANY_LOCATION", "")
        email = email_generator.generate_email(
            name=name,
            skill=skill,
            company_name=company_name,
            position=position,
            template=template,
            location=location,
            key_skills=key_skills
        )
        return email
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating outreach email: {str(e)}")

@router.post("/resume/{resume_id}/send-email")
async def send_email(resume_id: int, payload: dict):
    """Send an email to the candidate using SMTP config from .env."""
    to_email = payload.get("to")
    subject = payload.get("subject")
    body = payload.get("body")
    if not (to_email and subject and body):
        raise HTTPException(status_code=400, detail="Missing to, subject, or body.")
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    sender_email = os.getenv("SENDER_EMAIL")
    if not all([smtp_host, smtp_port, smtp_user, smtp_pass, sender_email]):
        raise HTTPException(status_code=500, detail="SMTP configuration is incomplete.")
    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, to_email, msg.as_string())
        return {"message": "Email sent successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@router.get("/dashboard-metrics")
async def dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Return dashboard metrics for the current user."""
    try:
        # Total candidates for the user
        query = text("SELECT COUNT(*) FROM resumes WHERE user_id = :user_id")
        result = await db.execute(query, {"user_id": user_id})
        total_candidates = result.scalar() or 0

        # Get all resumes for the user
        query = text("""
            SELECT experience, contact, skills 
            FROM resumes 
            WHERE user_id = :user_id
        """)
        result = await db.execute(query, {"user_id": user_id})
        rows = result.fetchall()

        # Process experience data
        exp_years = []
        locations = []
        all_skills = []

        for row in rows:
            # Process experience
            try:
                if row[0]:
                    val = float(row[0].split()[0])
                    exp_years.append(val)
            except Exception:
                continue

            # Process location
            try:
                if row[1]:
                    contact = json.loads(row[1])
                    if contact.get("location"):
                        locations.append(contact["location"])
            except Exception:
                continue

            # Process skills
            try:
                if row[2]:
                    skills = json.loads(row[2])
                    all_skills.extend(skills)
            except Exception:
                continue

        # Calculate metrics
        avg_experience = round(sum(exp_years) / len(exp_years), 1) if exp_years else 0
        top_location = max(set(locations), key=locations.count) if locations else ""
        top_skill = max(set(all_skills), key=all_skills.count) if all_skills else ""

        # Calculate distributions
        from collections import Counter

        # Skill distribution
        skill_dist = []
        if all_skills:
            skill_counts = Counter(all_skills)
            total = sum(skill_counts.values())
            for skill, count in skill_counts.items():
                skill_dist.append({"name": skill, "value": round(100 * count / total)})

        # Experience distribution
        exp_dist = []
        if exp_years:
            exp_bins = [str(int(y)) for y in exp_years]
            exp_counts = Counter(exp_bins)
            for years, count in exp_counts.items():
                exp_dist.append({"name": f"{years} years", "value": count})

        # Location distribution
        loc_dist = []
        if locations:
            loc_counts = Counter(locations)
            for loc, count in loc_counts.items():
                loc_dist.append({"name": loc, "value": count})

        return {
            "total_candidates": total_candidates,
            "average_experience": avg_experience,
            "top_location": top_location,
            "top_skill": top_skill,
            "skill_distribution": skill_dist,
            "experience_distribution": exp_dist,
            "location_distribution": loc_dist,
            "skill_gaps": []  # You can implement skill gap analysis if needed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating dashboard metrics: {str(e)}") 