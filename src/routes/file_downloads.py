from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from uuid import UUID
from src.auth import get_current_user
from src.database import (
    get_upload_task_file_url,
    get_companies_by_user_id,
    get_upload_task_company_id,
    get_task_status
)
from src.config import get_settings
from supabase import create_client, Client
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get(
    "/api/upload-tasks/{upload_task_id}/download",
    tags=["Upload Tasks"]
)
async def download_upload_file(
    upload_task_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Download a file associated with an upload task.
    
    Args:
        upload_task_id: UUID of the upload task
        current_user: Current authenticated user
        
    Returns:
        StreamingResponse with the file content
    """
    # Get upload task details
    task = await get_task_status(upload_task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Upload task not found")
        
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(task['company_id']) for company in companies):
        raise HTTPException(status_code=403, detail="You don't have access to this file")
    
    # Get file path
    file_path = task['file_url']
    
    try:
        # Initialize Supabase client with service role for storage access
        settings = get_settings()
        supabase: Client = create_client(
            settings.supabase_url,
            settings.SUPABASE_SERVICE_KEY
        )
        
        # Determine storage bucket based on task type
        if task["type"] == "leads":
            storage_bucket = "leads-uploads"
        elif task["type"] == "do_not_email":
            storage_bucket = "do-not-email-uploads"
        else:
            logger.error(f"Invalid upload task type: {task['type']}")
            raise HTTPException(status_code=400, detail=f"Invalid upload task type: {task['type']}")
        
        # Download file from Supabase storage
        storage = supabase.storage.from_(storage_bucket)
        file_data = storage.download(file_path)
        
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found in storage")
        
        # Get original filename from task
        filename = task.get("file_name", os.path.basename(file_path))
        
        # Create streaming response
        return StreamingResponse(
            content=iter([file_data]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
            
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}") 