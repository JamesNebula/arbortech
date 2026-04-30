import hashlib
import logging
import os
import shutil
import tempfile
import time
from typing import Optional

import laspy
import numpy as np
from fastapi import HTTPException, UploadFile
from laspy.errors import LaspyException

logger = logging.getLogger(__name__)

HASH_CHUNK_SIZE = 8192

def compute_file_hash(file_path: str, chunk_size: int = HASH_CHUNK_SIZE) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()

def _extract_crs(header) -> Optional[str]:
    try:
        crs = header.parse_crs()
        if crs and crs.to_epsg():
            return str(crs.to_epsg())
        logger.debug("No CRS found in header")
        return None
    except (AttributeError, ValueError) as e:
        logger.debug(f"CRS extraction failed: {e}")
        return None

def process_lidar_file(file: UploadFile, filename: str) -> dict:
    """Process a las/laz file and extract metadata.
    Args:
    file: FastAPI UploadFile object
    filename: Original uploaded filename

    returns: 
    dict matching IngestResponse schema with extracted metadata
    """

    start = time.perf_counter()
    tmp_path: Optional[str] = None
    # Create a temp file with .laz extension so laspy detects compression
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".laz") as tmp:
            file.file.seek(0)
            shutil.copyfileobj(file.file, tmp)
            tmp.flush()
            tmp_path = tmp.name

        file_hash = compute_file_hash(tmp_path)
        logger.info(f"Ingesting {filename} | hash={file_hash}")

        with laspy.open(tmp_path) as las:
            header = las.header
            crs = header.parse_crs()

            return {
                "filename": filename,
                "point_count": header.point_count,
                "file_version": str(header.version),
                "point_format_id": header.point_format.id,
                "bounding_box": {
                    "min_x": float(header.min[0]),
                    "max_x": float(header.max[0]),
                    "min_y": float(header.min[1]),
                    "max_y": float(header.max[1]),
                    "min_z": float(header.min[2]),
                    "max_z": float(header.max[2]),
                },
                "crs": _extract_crs(header),
                "processing_time_ms": float((time.perf_counter() - start) * 1000),
                "file_hash_sha256": file_hash,
            }
    except LaspyException as e:
        # Client sent invalid/corrupt LAS file → 400 per spec
        logger.warning(f"Invalid LAS file {filename}: {e}")
        raise HTTPException(status_code=400, detail="Corrupted or invalid LAS file header")
    
    except Exception as e:
        # Unexpected server error: log stack trace internally, return generic 500
        logger.exception(f"Unexpected error processing {filename}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    finally:
        # Always clean up temp file to avoid disk leaks
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)