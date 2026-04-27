from pathlib import Path
from pydantic import BaseModel, FilePath, field_validator

class IngestResponse(BaseModel):
    filename: str
    point_count: int
    bounding_box: list
    crs: str
    point_format_id: int
    file_version: str
    processing_time_ms: float

    
