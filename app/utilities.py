import laspy
import numpy as np
import time
import tempfile
import os
import shutil
from fastapi import HTTPException

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

            return file_info
        
        except Exception as e:
            # Reveal the actual error for debugging
            raise HTTPException(status_code=500, detail=f"Internal error: {e}")
        
        finally:
            # Always clean up the temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)