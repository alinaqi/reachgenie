from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Query
from typing import List, Optional
from uuid import UUID
import uuid
import logging

from src.models import (
    DoNotEmailRequest,
    DoNotEmailResponse,
    DoNotEmailListResponse,
    TaskResponse
)
from src.database import (
    get_user_company_profile,
    add_to_do_not_email_list,
    get_do_not_email_list,
    remove_from_do_not_email_list,
    is_email_in_do_not_email_list,
    create_upload_task,
    process_do_not_email_csv_upload
)
from src.auth import get_current_user
from src.config import get_settings
from supabase import create_client, Client

# Set up logger
logger = logging.getLogger(__name__)
settings = get_settings()

# Create routers
companies_router = APIRouter(
    prefix="/api/companies",
    tags=["Email Management"]
)

check_router = APIRouter(
    prefix="/api",
    tags=["Email Management"]
)

@companies_router.get("/{company_id}/do-not-email", response_model=DoNotEmailListResponse)
async def get_do_not_email_list_endpoint(
    company_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Do Not Email list for a company
    """
    # Validate company access
    user_company_profile = await get_user_company_profile(current_user['id'], company_id)
    if not user_company_profile:
        raise HTTPException(status_code=403, detail="You don't have access to this company")
    
    result = await get_do_not_email_list(
        company_id=company_id,
        page=page,
        limit=limit
    )
    
    return result

@companies_router.post("/{company_id}/do-not-email", response_model=DoNotEmailResponse)
async def add_to_do_not_email_list_endpoint(
    company_id: UUID,
    request: DoNotEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Add an email to the Do Not Email list
    """
    # Validate company access
    user_company_profile = await get_user_company_profile(current_user['id'], company_id)
    if not user_company_profile:
        raise HTTPException(status_code=403, detail="You don't have access to this company")
    
    result = await add_to_do_not_email_list(
        email=request.email,
        reason=request.reason,
        company_id=company_id
    )
    
    if result["success"]:
        return {"success": True, "message": f"Added {request.email} to Do Not Email list"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to add to Do Not Email list: {result.get('error')}")

@companies_router.delete("/{company_id}/do-not-email/{email}", response_model=DoNotEmailResponse)
async def remove_from_do_not_email_list_endpoint(
    company_id: UUID,
    email: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove an email from the Do Not Email list
    """
    # Validate company access
    user_company_profile = await get_user_company_profile(current_user['id'], company_id)
    if not user_company_profile:
        raise HTTPException(status_code=403, detail="You don't have access to this company")
    
    result = await remove_from_do_not_email_list(
        email=email,
        company_id=company_id
    )
    
    if result["success"]:
        return {"success": True, "message": f"Removed {email} from Do Not Email list"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to remove from Do Not Email list: {result.get('error')}")

@check_router.get("/do-not-email/check")
async def check_do_not_email_status(
    email: str = Query(..., description="Email address to check"),
    company_id: Optional[UUID] = Query(None, description="Optional company ID to check company-specific exclusions"),
    current_user: dict = Depends(get_current_user)
):
    """
    Check if an email is in the Do Not Email list
    """
    if company_id:
        # Validate company access if company_id is provided
        user_company_profile = await get_user_company_profile(current_user['id'], company_id)
        if not user_company_profile:
            raise HTTPException(status_code=403, detail="You don't have access to this company")
    
    is_excluded = await is_email_in_do_not_email_list(
        email=email,
        company_id=company_id
    )
    
    return {"email": email, "is_excluded": is_excluded}

@companies_router.post("/{company_id}/do-not-email/upload", response_model=TaskResponse)
async def upload_do_not_email_list(
    background_tasks: BackgroundTasks,
    company_id: UUID,
    current_user: dict = Depends(get_current_user),
    file: UploadFile = File(...)
):
    """
    Upload email addresses from CSV file to add to the Do Not Email list.
    The processing will be done in the background.
    """
    # Validate company access
    user_company_profile = await get_user_company_profile(current_user['id'], company_id)
    if not user_company_profile:
        raise HTTPException(status_code=403, detail="You don't have access to this company")
    
    try:
        # Initialize Supabase client with service role
        settings = get_settings()
        supabase: Client = create_client(
            settings.supabase_url,
            settings.SUPABASE_SERVICE_KEY
        )
        
        # Generate unique file name
        file_name = f"{company_id}/{uuid.uuid4()}.csv"
        
        # Read and upload file content
        file_content = await file.read()
        if isinstance(file_content, str):
            file_content = file_content.encode('utf-8')
        
        # Upload file to Supabase storage
        storage = supabase.storage.from_("do-not-email-uploads")
        try:
            storage.upload(
                path=file_name,
                file=file_content,
                file_options={"content-type": "text/csv"}
            )
        except Exception as upload_error:
            logger.error(f"Storage upload error: {str(upload_error)}")
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")
        
        # Create task record
        task_id = uuid.uuid4()
        await create_upload_task(task_id, company_id, current_user["id"], file_name)
        
        # Add background task
        background_tasks.add_task(
            process_do_not_email_csv_upload,
            company_id,
            file_name,
            current_user["id"],
            task_id
        )
        
        return TaskResponse(
            task_id=task_id,
            message="File upload started. Use the task ID to check the status."
        )
        
    except Exception as e:
        logger.error(f"Error starting do-not-email list upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Export both routers
router = companies_router
check_router = check_router 