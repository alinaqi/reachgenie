from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from uuid import UUID
from src.auth import get_current_user
from src.database import (
    get_upload_task_file_url,
    get_companies_by_user_id,
    get_upload_task_company_id
)
from src.config import get_settings
from supabase import create_client, Client
import os

router = APIRouter()

@router.get(
    "/api/upload-tasks/{upload_task_id}/download",
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
    file_path = await get_upload_task_file_url(upload_task_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Initialize Supabase client with service role for storage access
        settings = get_settings()
        supabase: Client = create_client(
            settings.supabase_url,
            settings.SUPABASE_SERVICE_KEY
        )
        
        # Download file from Supabase storage
        storage = supabase.storage.from_("leads-uploads")
        file_data = storage.download(file_path)
        
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found in storage")
        
        # Get original filename from path
        filename = os.path.basename(file_path)
        
        # Create streaming response
        return StreamingResponse(
            content=iter([file_data]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}") 