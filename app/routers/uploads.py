from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends

from app.dependencies.jwt_auth import get_current_user
from app.schemas.upload import UploadResponse
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/upload", tags=["Uploads"])

# Directory where uploaded files will be stored (../uploads relative to project root)
BASE_DIR = Path(__file__).resolve().parents[2]  # .../major
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post(
    "/image", 
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image file",
    description="Upload a JPG or PNG image file. File size limit is 10MB. Returns file information including generated filename.",
    responses={
        201: {"description": "Image uploaded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file type or size"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        413: {"model": ErrorResponse, "description": "File too large"}
    }
)
async def upload_image(
    file: UploadFile = File(..., description="Image file to upload (JPG or PNG)"),
    current_user: str = Depends(get_current_user)
):
    """Upload a JPG or PNG image and save it to the local 'uploads' directory."""
    # Validate file type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_TYPE", 
                "message": "Invalid file type. Only JPEG and PNG images are allowed."
            }
        )

    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE", 
                "message": f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024*1024)}MB"
            }
        )

    # Generate unique filename preserving the correct extension
    extension = ALLOWED_CONTENT_TYPES[file.content_type]
    saved_filename = f"{uuid4()}{extension}"
    saved_path = UPLOAD_DIR / saved_filename

    # Read the uploaded file and write to disk in chunks
    file_size = 0
    try:
        with saved_path.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1 MB chunks
                buffer.write(chunk)
                file_size += len(chunk)
                
                # Check size during upload
                if file_size > MAX_FILE_SIZE:
                    # Clean up partial file
                    saved_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail={
                            "code": "FILE_TOO_LARGE", 
                            "message": f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024*1024)}MB"
                        }
                    )
    except Exception as e:
        # Clean up partial file on error
        saved_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "UPLOAD_FAILED", 
                "message": "Failed to upload file. Please try again."
            }
        )
    finally:
        await file.close()

    return UploadResponse(
        filename=saved_filename,
        file_size=file_size,
        content_type=file.content_type
    ) 