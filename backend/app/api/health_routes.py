from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

@router.get("", summary="Health check endpoint")
async def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    return {"status": "healthy", "version": "1.0.0"}