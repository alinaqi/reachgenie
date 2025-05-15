from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from uuid import UUID
import httpx
from src.auth import get_current_user
from src.database import (
    get_upload_task_file_url,
    get_companies_by_user_id,
    get_upload_task_company_id
)
import os
from urllib.parse import urlparse

router = APIRouter()

@router.get(
    "/upload-tasks/{upload_task_id}/download",
    tags=["Upload Tasks"]
)
async def download_upload_file(
    upload_task_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Download the file associated with an upload task.
    
    Args:
        upload_task_id: UUID of the upload task
        current_user: Current authenticated user
        
    Returns:
        StreamingResponse: The file as a streaming download
    """
    # Get the company_id for the upload task
    company_id = await get_upload_task_company_id(upload_task_id)
    if not company_id:
        raise HTTPException(status_code=404, detail="Upload task not found")
    
    # Check if user has access to the company
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=403, detail="Not authorized to access this upload task")
    
    # Get the file URL
    file_url = await get_upload_task_file_url(upload_task_id)
    if not file_url:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Create async HTTP client
        async with httpx.AsyncClient() as client:
            # Get the file from Supabase storage
            response = await client.get(file_url)
            response.raise_for_status()
            
            # Get original filename from URL
            filename = os.path.basename(urlparse(file_url).path)
            
            # Create streaming response
            return StreamingResponse(
                content=response.iter_bytes(),
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
            
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") 