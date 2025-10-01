import uuid
import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    InferenceJob,
    InferenceJobPublic,
    InferenceJobCreate,
    InferenceJobsPublic,
    InferenceModel,
    InferenceModelPublic,
    SegmentationResult,
    SegmentationResultPublic,
    Message,
)
from app.services.inference_service import inference_service
from app.services.minio_service import minio_service
from app.celery_client import get_active_workers

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/submit", response_model=InferenceJobPublic)
async def submit_inference_job(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    job_data: InferenceJobCreate,
) -> InferenceJob:
    """
    Submit DICOM study or series for AI segmentation inference
    """
    try:
        job = await inference_service.submit_inference_job(
            job_data=job_data, user_id=current_user.id, session=session
        )

        logger.info(f"Submitted inference job {job.id} for user {current_user.id}")
        return job

    except ValueError as e:
        logger.warning(f"Inference job validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting inference job: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit inference job")


@router.get("/jobs", response_model=InferenceJobsPublic)
async def list_inference_jobs(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> InferenceJobsPublic:
    """
    List inference jobs for current user
    """
    try:
        jobs = await inference_service.list_user_jobs(
            user_id=current_user.id, session=session, skip=skip, limit=limit
        )

        return InferenceJobsPublic(data=jobs, count=len(jobs))

    except Exception as e:
        logger.error(f"Error listing inference jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs")


@router.get("/jobs/{job_id}", response_model=InferenceJobPublic)
async def get_inference_job_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    job_id: uuid.UUID,
) -> InferenceJob:
    """
    Get inference job status and details
    """
    try:
        job = await inference_service.get_job_status(
            job_id=job_id, user_id=current_user.id, session=session
        )

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")


@router.get("/jobs/{job_id}/result", response_model=SegmentationResultPublic)
async def get_inference_result(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    job_id: uuid.UUID,
) -> SegmentationResult:
    """
    Get completed inference job result metadata
    """
    try:
        result = await inference_service.get_job_result(
            job_id=job_id, user_id=current_user.id, session=session
        )

        if not result:
            raise HTTPException(status_code=404, detail="Result not found")

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving inference result: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve result")


@router.get("/jobs/{job_id}/download")
async def download_inference_result(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    job_id: uuid.UUID,
):
    """
    Download segmentation result file
    """
    try:
        result = await inference_service.get_job_result(
            job_id=job_id, user_id=current_user.id, session=session
        )

        if not result:
            raise HTTPException(status_code=404, detail="Result not found")

        # Get presigned download URL from MinIO
        download_url = await minio_service.get_presigned_download_url(result.file_path)

        # Redirect to presigned URL
        return RedirectResponse(url=download_url)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading result: {e}")
        raise HTTPException(status_code=500, detail="Failed to download result")


@router.delete("/jobs/{job_id}", response_model=Message)
async def cancel_inference_job(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    job_id: uuid.UUID,
) -> Message:
    """
    Cancel pending or running inference job
    """
    try:
        await inference_service.cancel_job(
            job_id=job_id, user_id=current_user.id, session=session
        )

        return Message(message="Inference job cancelled successfully")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/models", response_model=List[InferenceModelPublic])
async def list_available_models(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> List[InferenceModel]:
    """
    List available inference models
    """
    try:
        models = await inference_service.list_available_models(session=session)
        return models

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve models")


@router.get("/health", response_model=dict)
async def inference_health_check() -> dict:
    """
    Check inference service health and active worker count
    """
    try:
        worker_count = get_active_workers()

        return {
            "status": "healthy",
            "service": "InferenceService",
            "workers": worker_count,
        }

    except Exception as e:
        logger.error(f"Inference health check failed: {e}")
        raise HTTPException(status_code=503, detail="Inference service unavailable")
