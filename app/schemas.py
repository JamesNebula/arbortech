from typing import Optional
from pydantic import BaseModel, Field

class IngestResponse(BaseModel):
    filename: str = Field(..., description="Original uploaded filename")
    point_count: int = Field(..., description="Total number of points in the file.")

    # Spec: dict with explicit min/max keys per axis
    bounding_box: dict[str, float] = Field(
        ...,
        description="Spatial extent: {min_x, max_x, min_y, max_y, min_z, max_z}"
    )

    # Spec: CRS may be absent -> optional[str]
    crs: Optional[str] = Field(
        None,
        description="Coordinate Reference System as EPSG code, or null if absent"
    )
    
    point_format_id: int = Field(..., description="LAS point data record format ID")
    file_version: str = Field(..., description="LAS file version")
    processing_time_ms: float = Field(..., description="Server side processing time in ms")

    # Spec: audit trail for data provenance
    file_hash_sha256: str = Field(..., description="SHA-256 hash of uploaded file for integrity tracking")

    class Config:
        # Ensure JSON schema includes descriptions in /docs
        json_schema_extra = {
            "example": {
                "filename": "scan_001.laz",
                "point_count": 125000,
                "bounding_box": {
                    "min_x": 153.1, "max_x": 153.2,
                    "min_y": -28.1, "max_y": -28.0,
                    "min_z": 0.0, "max_z": 150.0
                },
                "crs": "EPSG:7844",
                "point_format_id": 6,
                "file_version": "1.4",
                "processing_time_ms": 42.3,
                "file_hash_sha256": "A1b2c3d4b3n5..."
            }
        }

