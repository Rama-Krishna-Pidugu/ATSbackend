from fastapi import APIRouter, HTTPException
from app.services.background_check import BackgroundChecker
from app.models import BackgroundCheckRequest, BackgroundCheckResponse

router = APIRouter()
background_checker = BackgroundChecker()

@router.post("/check/", response_model=BackgroundCheckResponse)
async def check_background(request: BackgroundCheckRequest):
    """Perform a background check on a candidate."""
    try:
        result = background_checker.check(
            name=request.name,
            location=request.location
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing background check: {str(e)}"
        )

@router.post("/add-record/")
async def add_record(name: str, status: str, details: str):
    """Add a record to the mock background check database."""
    try:
        background_checker.add_record(name, status, details)
        return {"message": "Record added successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adding record: {str(e)}"
        ) 