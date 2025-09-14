from fastapi import APIRouter, HTTPException
from app.services.screening_generator import ScreeningGenerator
from app.models import ScreeningRequest, ScreeningResponse

router = APIRouter()
screening_generator = ScreeningGenerator()

@router.post("/generate-questions/", response_model=ScreeningResponse)
async def generate_questions(request: ScreeningRequest):
    """Generate screening questions for a specific skill and level."""
    try:
        questions = screening_generator.generate_questions(
            skill=request.skill,
            level=request.level
        )
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating questions: {str(e)}"
        ) 