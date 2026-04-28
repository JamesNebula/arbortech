from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Header
from typing import Annotated
import laspy
import numpy as np
from schemas import IngestResponse
from utilities import read_laz

app = FastAPI()
MAX_FILE_SIZE = 500 * 1024 * 1024 # 500MB

@app.post("/ingest", response_model=IngestResponse)
async def upload_file(file: UploadFile = File(...)):
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large.")
    
    file_info = read_laz(file, file.filename)

    return file_info

