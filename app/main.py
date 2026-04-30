from fastapi import FastAPI, UploadFile, File, HTTPException
import logging

from .logging_config import setup_logging
from .schemas import IngestResponse
from .utilities import read_laz

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="LiDAR Ingestion Service", version="1.0.0")

MAX_FILE_SIZE = 500 * 1024 * 1024
ALLOWED_EXTENSIONS = {".las", ".laz"}

@app.post("/api/v1/ingest", response_model=IngestResponse, status_code=200)
async def upload_file(file: UploadFile = File(...)) -> IngestResponse:
    # Validate file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in ALLOWED_EXTENSIONS:
        logger.warning(f"Rejected {file.filename}: Invalid Extension '.{ext}'")
        raise HTTPException(status_code=400, detail="Invalid file extension. Must be .las or .laz")
    
    if file.size is not None and file.size > MAX_FILE_SIZE:
        logger.warning(f"Rejected {file.filename}: size: {file.size} exceeds limit {MAX_FILE_SIZE}")
        raise HTTPException(status_code=413, detail="File too large, Maximum size is 500 MB.")

    # Process file (header integrity, metadata extraction)
    try:
        result = read_laz(file, file.filename)
        logger.info(
            f"Ingest success: {result['filename']} | "
            f"points={result['point_count']} | "
            f"hash={result['file_hash_sha256'][:16]}... | "
            f"time_ms={result['processing_time_ms']:.2f}"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing {file.filename}")
        raise HTTPException(status_code=500, detail="Internal Server Error")