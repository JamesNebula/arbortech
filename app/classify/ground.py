import tempfile
import shutil
import time
import numpy as np
import laspy
import logging
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.utilities import compute_file_hash
from app.config import MAX_CLASSIFY_SIZE, ALLOWED_EXTENSIONS

router = APIRouter()
logger = logging.getLogger(__name__)

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
    # Validate RANSAC params 
    if distance_threshold <= 0:
        raise HTTPException(status_code=400, detail="distance_threshold must be > 0")
    if ransac_n < 3:
        raise HTTPException(status_code=400, detail="ransac_n must be >= 3 (minimum points for a plane)")
    if num_iterations <= 0:
        raise HTTPException(status_code=400, detail="num_iterations must be > 0")
    
    # Validate extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "" # type: ignore
    if f".{ext}" not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file extension. must be .las or .laz")
    
    # Validate file size
    if file.size is not None and file.size > MAX_CLASSIFY_SIZE: #200MB cap 
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 200 MB")
    
    # Compute SHA-256 hash
    file_hash = "pending_temp_file"

    # Log RANSAC config for audit trail
    logger.info(
        f"Starting ground classification | "
        f"file={file.filename} | "
        f"distance_threshold={distance_threshold} | "
        f"ransac_n={ransac_n} | "
        f"num_iterations={num_iterations}" 
    )

    # Need to add point extraction, scaling, sampling and open3d RANSAC
    pass
    