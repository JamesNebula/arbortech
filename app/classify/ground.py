from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File

router = APIRouter()

class GroundResponse(BaseModel):
    ground_point_count: int
    ground_point_indices: list[int]
    plane_model: list[float]
    points_processed: int
    processing_time_ms: float
    file_hash: str

@router.post('/api/v1/classify/ground', response_model=GroundResponse)
async def classify_ground(
    file: UploadFile = File(...),
    distance_threshold: float = 0.3,
    ransac_n: int = 3,
    num_iterations: int = 100
):
    pass