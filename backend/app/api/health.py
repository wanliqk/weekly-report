from fastapi import APIRouter

from app.schemas.common import ApiResponse
from app.schemas.health import HealthData

router = APIRouter(tags=["system"])


@router.get("/health", response_model=ApiResponse[HealthData])
async def health() -> ApiResponse[HealthData]:
    return ApiResponse(data=HealthData(status="ok"))
