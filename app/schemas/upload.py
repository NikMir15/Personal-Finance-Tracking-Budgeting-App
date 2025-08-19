from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    filename: str = Field(..., description="Generated filename of uploaded file")
    file_size: int = Field(..., description="Size of uploaded file in bytes")
    content_type: str = Field(..., description="MIME type of uploaded file") 