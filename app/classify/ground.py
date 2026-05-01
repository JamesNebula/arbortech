import tempfile
import shutil
import time
import numpy as np
import laspy
import logging

from pathlib import Path as FilePath
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.utilities import compute_file_hash
from app.config import MAX_CLASSIFY_SIZE, ALLOWED_EXTENSIONS, MAX_POINTS_FOR_RANSAC

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
    tmp_path = None
    start_time = time.perf_counter()

    try:
        # Write upload to temp file (laspy needs a real file handle)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".las") as tmp:
            file.file.seek(0)
            shutil.copyfileobj(file.file, tmp)
            tmp.flush()
            tmp_path = tmp.name

        # Compute SHA-256 hash for provenance
        file_hash = compute_file_hash(tmp_path)

        # read file and validate point count
        las = laspy.read(tmp_path)
        total_points = las.header.point_count
        if total_points == 0:
            raise HTTPException(status_code=400, detail="File contains zero points")
            
        # Extract raw integer coordinates
        # laspy stores points as scaled integers: real = raw * scale + offset
        raw_x = las.points['X']
        raw_y = las.points['Y']
        raw_z = las.points['Z']
        # Apply header scale & offset 
        scales = np.array([las.header.scales[0], las.header.scales[1], las.header.scales[2]])
        offsets = np.array([las.header.offsets[0], las.header.offsets[1], las.header.offsets[2]])
        points = (np.vstack([raw_x, raw_y, raw_z]).T * scales) + offsets
        # Enforce memory cap: sample if > 100,000
        points_processed = total_points
        if points_processed > MAX_POINTS_FOR_RANSAC:
            logger.warning(
                f"Point count {points_processed} exceeds {MAX_POINTS_FOR_RANSAC} cap."
                f"Sampling with seed=42 for reproducibility."
            )
            rng = np.random.default_rng(42)
            sample_idx = rng.choice(points_processed, size=MAX_POINTS_FOR_RANSAC, replace=False)
            points = points[sample_idx]
            points_processed = MAX_POINTS_FOR_RANSAC
        
        logger.info(
            f"Point extraction complete | processed={points_processed} | "
            f"Shape={points.shape} | hash={file_hash[:16]}..."
        )
        return {"Message": "Extraction and scaling verified. RANSAC next"}

    except laspy.errors.LaspyException as e:
        logger.warning(f"Failed to parse LAS file {file.filename}: {e}")
        raise HTTPException(status_code=400, detail="Corrupted or invalid LAS file")
    except Exception as e:
        logger.exception(f"Unexpected error during point extraction for {file.filename}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if tmp_path and FilePath(tmp_path).exists():
            FilePath(tmp_path).unlink()