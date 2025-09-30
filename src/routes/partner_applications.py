from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Body
from typing import List, Optional, Dict
from uuid import UUID
import logging
from datetime import datetime, timezone

from src.models import (
    PartnerApplicationCreate,
    PartnerApplicationUpdate,
    PartnerApplicationNoteCreate,
    PartnerApplicationResponse,
    PartnerApplicationListResponse,
    PartnerApplicationStats,
    SimplePartnerApplicationResponse,
    ApplicationStatus
)
from src.database import (
    create_partner_application,
    get_partner_applications,
    get_partner_application_by_id,
    update_partner_application_status,
    create_partner_application_note,
    get_partner_application_statistics
)
from src.auth import get_current_user
from src.services.partner_application_service import PartnerApplicationService
from src.config import get_settings

# Set up logger
logger = logging.getLogger(__name__)
settings = get_settings()

# Create router
router = APIRouter(
    prefix="/api",
    tags=["partner-applications"]
)

# Public endpoints
@router.post(
    "/partner-applications",
    response_model=SimplePartnerApplicationResponse,
    status_code=status.HTTP_201_CREATED
)
async def submit_partner_application(
    application: PartnerApplicationCreate
):
    """
    Submit a new partner application.
    
    This endpoint is publicly accessible and allows potential partners to submit their applications.
    """
    try:
        # Create the application in the database
        application_data = await create_partner_application(
            company_name=application.company_name,
            contact_name=application.contact_name,
            contact_email=application.contact_email,
            contact_phone=application.contact_phone,
            website=application.website,
            partnership_type=application.partnership_type,
            company_size=application.company_size,
            industry=application.industry,
            current_solutions=application.current_solutions,
            target_market=application.target_market,
            motivation=application.motivation,
            additional_information=application.additional_information
        )
        
        # Generate and send personalized confirmation email
        try:
            partner_service = PartnerApplicationService()
            # Use the new method that handles both generation and sending
            email_sent = await partner_service.send_confirmation_email(application_data)
            
            if email_sent:
                logger.info(f"Confirmation email sent to {application.contact_email}")
            else:
                logger.warning(f"Failed to send confirmation email to {application.contact_email}")
        except Exception as e:
            # Log the error, but don't fail the entire request
            logger.error(f"Error in email generation or sending: {str(e)}")
            logger.exception(e)  # Log the full exception with traceback
        
        # Return success response
        return SimplePartnerApplicationResponse(
            id=application_data["id"],
            message="Your partnership application has been submitted successfully. We will contact you soon."
        )
    except Exception as e:
        logger.error(f"Error submitting partner application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit partner application: {str(e)}"
        )


# Admin endpoints
@router.get(
    "/admin/partner-applications",
    response_model=PartnerApplicationListResponse,
    dependencies=[Depends(get_current_user)]
)
async def list_partner_applications(
    status: Optional[str] = Query(None, description="Filter by application status"),
    partnership_type: Optional[str] = Query(None, description="Filter by partnership type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)")
):
    """
    List partner applications with filtering and pagination.
    
    This endpoint is protected and requires authentication.
    """
    try:
        result = await get_partner_applications(
            status=status,
            partnership_type=partnership_type,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return result
    except Exception as e:
        logger.error(f"Error listing partner applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list partner applications: {str(e)}"
        )


@router.get(
    "/admin/partner-applications/{application_id}",
    response_model=PartnerApplicationResponse,
    dependencies=[Depends(get_current_user)]
)
async def get_partner_application(
    application_id: UUID = Path(..., description="ID of the partner application")
):
    """
    Get detailed information about a specific partner application.
    
    This endpoint is protected and requires authentication.
    """
    try:
        application = await get_partner_application_by_id(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Partner application with ID {application_id} not found"
            )
        
        return application
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting partner application {application_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get partner application: {str(e)}"
        )


@router.patch(
    "/admin/partner-applications/{application_id}/status",
    response_model=PartnerApplicationResponse,
    dependencies=[Depends(get_current_user)]
)
async def update_application_status(
    application_id: UUID = Path(..., description="ID of the partner application"),
    status_update: PartnerApplicationUpdate = Body(...)
):
    """
    Update the status of a partner application.
    
    This endpoint is protected and requires authentication.
    """
    try:
        updated_application = await update_partner_application_status(
            application_id=application_id,
            status=status_update.status
        )
        
        if not updated_application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Partner application with ID {application_id} not found"
            )
        
        # Get the full application with notes to return
        application = await get_partner_application_by_id(application_id)
        
        return application
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating partner application status {application_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update partner application status: {str(e)}"
        )


@router.post(
    "/admin/partner-applications/{application_id}/notes",
    response_model=Dict,
    dependencies=[Depends(get_current_user)]
)
async def add_note_to_application(
    application_id: UUID = Path(..., description="ID of the partner application"),
    note: PartnerApplicationNoteCreate = Body(...)
):
    """
    Add an internal note to a partner application.
    
    This endpoint is protected and requires authentication.
    """
    try:
        created_note = await create_partner_application_note(
            application_id=application_id,
            author_name=note.author_name,
            note=note.note
        )
        
        return {
            "status": "success",
            "message": "Note added successfully",
            "data": created_note
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding note to partner application {application_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add note to partner application: {str(e)}"
        )


@router.get(
    "/admin/partner-applications/statistics",
    response_model=PartnerApplicationStats,
    dependencies=[Depends(get_current_user)]
)
async def get_application_statistics():
    """
    Get statistics about partner applications.
    
    This endpoint is protected and requires authentication.
    """
    try:
        stats = await get_partner_application_statistics()
        
        return stats
    except Exception as e:
        logger.error(f"Error getting partner application statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get partner application statistics: {str(e)}"
        ) 