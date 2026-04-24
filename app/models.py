from pathlib import Path
from pydantic import BaseModel, FilePath, field_validator

class Document(BaseModel):
    file_path: FilePath

    @field_validator('file_path')
    @classmethod
    def validate_extension(cls, v: Path) -> Path:
        if v.suffix not in ('.las', '.laz'):
            raise ValueError("File must be a (.las) or (.laz) file.")
        
        return v

    
