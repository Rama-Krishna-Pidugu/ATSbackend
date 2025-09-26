from fastapi import APIRouter, HTTPException, Depends
from app.services.email_generator import EmailGenerator
from app.services.email_sender import EmailSender
from app.models import EmailRequest, EmailResponse
from app.auth.clerk import get_current_user_claims
from typing import Dict

router = APIRouter()
email_generator = EmailGenerator()
email_sender = EmailSender()

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

@router.post("/send-email/")
async def send_email(request: EmailRequest, current_user: Dict = Depends(get_current_user_claims)):
    """Generate and send a personalized outreach email from the user's account."""
    try:
        # Generate email content
        email_content = email_generator.generate_email(
            name=request.name,
            skill=request.skill,
            company_name=request.company_name,
            position=request.position
        )

        # Get email from Clerk claims (email_addresses array)
        email_addresses = current_user.get('email_addresses', [])
        if not email_addresses:
            raise HTTPException(status_code=400, detail="User email not found in token")
        from_email = email_addresses[0]['email_address']

        success = email_sender.send_email(
            from_email=from_email,
            to_email=request.recipient_email,
            subject=email_content['subject'],
            body=email_content['body']
        )

        if success:
            return {"status": "Email sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending email: {str(e)}"
        )
