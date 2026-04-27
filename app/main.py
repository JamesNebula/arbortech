from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from typing import Annotated
import laspy
import numpy as np
from schemas import IngestResponse

app = FastAPI()
MAX_FILE_SIZE = 500 * 1024 * 1024 # 500MB

@app.post("/ingest", response_model=IngestResponse)
async def upload_file(file: UploadFile = File(...)):
    return {
        "filename": file.filename,
        "point_count": 32000,
        "bounding_box": [134134, 1313444, 525334, 532223, 42342, 54332],
        "crs": "EPSG 4424",
        "point_format_id": 4,
        "file_version": "1.0.0",
        "processing_time_ms": 8.2
    }
   

# point count, bounding box (min_x, max_x etc), crs, point_format_id, file_version, processing_time_ms (float)
