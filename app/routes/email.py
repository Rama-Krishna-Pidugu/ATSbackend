from fastapi import APIRouter, HTTPException
from app.services.email_generator import EmailGenerator
from app.models import EmailRequest, EmailResponse

router = APIRouter()
email_generator = EmailGenerator()

@router.post("/generate-email/", response_model=EmailResponse)
async def generate_email(request: EmailRequest):
    """Generate a personalized outreach email."""
    try:
        email = email_generator.generate_email(
            name=request.name,
            skill=request.skill,
            company_name=request.company_name,
            position=request.position
        )
        return {"email": email}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating email: {str(e)}"
        ) 