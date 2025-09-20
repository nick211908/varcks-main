from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
