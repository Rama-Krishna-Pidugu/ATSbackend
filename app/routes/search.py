from fastapi import APIRouter, HTTPException, Depends
from app.services.search_engine import SearchEngine
from app.models import SearchQuery, SearchResponse, get_db
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import sqlite3
from app.services.screening_generator import ScreeningGenerator
from app.services.email_generator import EmailGenerator
from app.services.llm_utils import call_groq
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.auth.clerk import get_current_user
from fastapi import Request, Body
import json

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
        # Get user_id from request state
        user_id = request.state.user_id
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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Search candidates based on query parameters using semantic search."""
    try:
        # Verify database state before searching
        search_engine.verify_database()

        # Get user_id from request state
        user_id = request.state.user_id

        # Parse location and experience_years from query if not provided
        location = query.location
        experience_years = query.experience_years

        if location is None or experience_years is None:
            try:
                prompt = f"""
                Extract the location and years of experience from this job search query.
                Return ONLY a JSON object in this exact format:
                {{"location": "city name or null", "experience_years": number or null}}

                Examples:
                Query: "Python developers in Bangalore"
                {{"location": "Bangalore", "experience_years": null}}

                Query: "React developers with 5 years experience"
                {{"location": null, "experience_years": 5}}

                Query: "JavaScript developers in Mumbai with 3+ years"
                {{"location": "Mumbai", "experience_years": 3}}

                Query: "Find data scientists"
                {{"location": null, "experience_years": null}}

                Query: "{query.query}"
                """
                response, _ = call_groq(prompt, temperature=0.0, max_tokens=100)
                parsed = json.loads(response.strip())
                if location is None:
                    location = parsed.get("location")
                if experience_years is None:
                    experience_years = parsed.get("experience_years")
            except Exception as e:
                print(f"Error parsing query: {str(e)}")
                # Continue with None values

        # Use the search engine's semantic search with user_id filter
        results = search_engine.search(
            query=query.query,
            location=location,
            experience_years=experience_years,
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
                
                # Ensure similarity_score is a float within 0..1
                sim = match.get("similarity_score", 0)
                try:
                    sim = float(sim)
                except Exception:
                    sim = 0.0
                sim = max(0.0, min(sim, 1.0))

                processed_results.append({
                    "id": match["id"],
                    "name": match["name"],
                    "skills": skills,
                    "experience": match["experience"],
                    "education": match["education"],
                    "contact": contact,
                    "summary": match["summary"],
                    "similarity_score": sim
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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific resume by ID."""
    try:
        user_id = request.state.user_id
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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Add a new candidate to the search index."""
    try:
        # Add user_id to the candidate data
        candidate["user_id"] = request.state.user_id
        search_engine.add_candidate(candidate)
        return {"message": "Candidate added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding candidate: {str(e)}")

@router.delete("/clear-index/")
async def clear_index(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Clear the search index for the current user."""
    try:
        user_id = request.state.user_id
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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific resume."""
    try:
        user_id = request.state.user_id
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
async def get_screening_questions(resume_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Generate AI screening questions for a candidate based on their skills and experience."""
    try:
        user_id = request.state.user_id
        # For development/testing, use a default user_id if None
        if user_id is None:
            user_id = "test_user"
        query = text("SELECT name, skills, experience FROM resumes WHERE id = :resume_id AND user_id = :user_id")
        result = await db.execute(query, {"resume_id": resume_id, "user_id": user_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Resume not found")
        name, skills_json, experience = row
        try:
            skills = json.loads(skills_json) if skills_json else []
        except (json.JSONDecodeError, TypeError):
            skills = []
        # Use the top skill or fallback
        skill = skills[0] if skills else "developer"
        questions = screening_generator.generate_questions(skill=skill, level="senior" if experience and ("5" in experience or "senior" in experience.lower()) else "mid")
        return {"questions": questions}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating screening questions: {str(e)}")

@router.post("/resume/{resume_id}/generate-email")
async def generate_outreach_email(resume_id: int, request: Request, email_request: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Generate an outreach email for a candidate based on a template."""
    try:
        template = email_request.get("template", "initial_outreach")
        user_id = request.state.user_id
        query = text("SELECT name, skills, experience FROM resumes WHERE id = :resume_id AND user_id = :user_id")
        result = await db.execute(query, {"resume_id": resume_id, "user_id": user_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Resume not found")
        name, skills_json, experience = row
        try:
            skills = json.loads(skills_json) if skills_json else []
        except (json.JSONDecodeError, TypeError):
            skills = []
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating outreach email: {str(e)}")

@router.post("/resume/{resume_id}/send-email")
async def send_email(resume_id: int, request: Request, payload: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Send an email to the candidate using SMTP config from .env."""
    try:
        user_id = request.state.user_id
        # Check if resume belongs to user
        query = text("SELECT id FROM resumes WHERE id = :resume_id AND user_id = :user_id")
        result = await db.execute(query, {"resume_id": resume_id, "user_id": user_id})
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Resume not found")
        
        to_email = payload.get("recipient")
        subject = payload.get("subject")
        body = payload.get("email_body")
        if not (to_email and subject and body):
            raise HTTPException(status_code=400, detail="Missing recipient, subject, or email_body.")
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        sender_email = os.getenv("SENDER_EMAIL")
        if not all([smtp_host, smtp_user, smtp_pass, sender_email]):
            print("Warning: SMTP configuration incomplete. Simulating email send for development.")
            return {"message": "Email simulated (SMTP config missing). Check logs for details."}
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@router.get("/dashboard-metrics")
async def dashboard_metrics(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Return dashboard metrics for the current user."""
    try:
        user_id = request.state.user_id
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