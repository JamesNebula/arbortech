import laspy
import numpy as np
import time
import tempfile
import os
import shutil
import hashlib
import logging
import traceback
from fastapi import HTTPException
from laspy.errors import LaspyException

logger = logging.getLogger(__name__)

def compute_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()

def read_laz(file, filename: str):
    start = time.perf_counter()
    # Create a temp file with .laz extension so laspy detects compression
    with tempfile.NamedTemporaryFile(delete=False, suffix=".laz") as tmp:
        try:
            # Copy uploaded file content to the temp file
            # We seek(0) to ensure we start from the beginning
            file.file.seek(0)
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

            file_hash = compute_file_hash(tmp_path)
            logger.info(f"Ingesting {filename} | hash={file_hash}")
            # Now open with laspy
            with laspy.open(tmp_path) as las:
                file_info = {}
                file_info['filename'] = filename
                file_info['point_count'] = las.header.point_count
                # Convert version to string for Pydantic compatibility
                file_info['file_version'] = str(las.header.version) 
                file_info['point_format_id'] = las.header.point_format.id
                file_info['bounding_box'] = [
                    np.array(las.header.min).tolist(), 
                    np.array(las.header.max).tolist()
                ]
                crs = las.header.parse_crs()

                if crs:
                    epsg = crs.to_epsg()
                    file_info['crs'] = str(epsg)
                else:
                    file_info['crs'] = "Unknown"
                
                end = time.perf_counter()
                processing_time = float(end - start) * 1000 # Convert to ms
                file_info['processing_time_ms'] = processing_time

                logger.info(f"Processed {filename} | points={file_info['point_count']} time_ms={file_info['processing_time_ms']}")

            return file_info
        
        except (LaspyException) as e:
            logger.warning(f"Invalid file format for {filename}: {e}")
            raise HTTPException(status_code=422, detail="Invalid LAZ file format")

        except Exception as e:
            # Reveal the actual error for debugging
            logger.exception(f"Server error processing {filename}")
            raise HTTPException(status_code=500, detail="Internal server error")
        
        finally:
            # Always clean up the temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)