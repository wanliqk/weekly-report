from fastapi import APIRouter, Request, Response

from app.schemas.common import ApiResponse
from app.schemas.health import HealthData

router = APIRouter(tags=["system"])


@router.get("/health", response_model=ApiResponse[HealthData])
async def health(request: Request, response: Response) -> ApiResponse[HealthData]:
    response.headers["Cache-Control"] = "no-store"
    return ApiResponse(data=HealthData(status="ok", version=request.app.version))
