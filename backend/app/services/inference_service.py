import logging
import uuid
from typing import List

from sqlmodel import Session, select

from app.models import (
    InferenceJob,
    InferenceJobCreate,
    InferenceModel,
    SegmentationResult,
    DICOMStudy,
    DICOMSeries,
)

logger = logging.getLogger(__name__)


class InferenceService:
    """Service for managing AI inference jobs"""

    async def submit_inference_job(
        self, job_data: InferenceJobCreate, user_id: uuid.UUID, session: Session
    ) -> InferenceJob:
        """Submit new inference job to queue"""
        # Validate study exists and user owns it
        study = session.exec(
            select(DICOMStudy).where(
                DICOMStudy.id == job_data.study_id, DICOMStudy.owner_id == user_id
            )
        ).first()

        if not study:
            raise ValueError("Study not found or access denied")

        # Validate series if specified
        if job_data.series_id:
            series = session.exec(
                select(DICOMSeries).where(
                    DICOMSeries.id == job_data.series_id,
                    DICOMSeries.study_id == job_data.study_id,
                )
            ).first()

            if not series:
                raise ValueError("Series not found in study")

        # Validate model exists and is active
        model = session.exec(
            select(InferenceModel).where(
                InferenceModel.id == job_data.model_id, InferenceModel.is_active == True
            )
        ).first()

        if not model:
            raise ValueError("Model not found or inactive")

        # Create job record
        job = InferenceJob(
            user_id=user_id,
            study_id=job_data.study_id,
            series_id=job_data.series_id,
            model_id=job_data.model_id,
            status="pending",
            parameters=job_data.parameters or {},
        )

        session.add(job)
        session.commit()
        session.refresh(job)

        # TODO: Enqueue to Celery when worker is ready
        # from app.services.inference_tasks import run_inference_task
        # run_inference_task.apply_async(
        #     args=[str(job.id)],
        #     task_id=str(job.id)
        # )

        logger.info(f"Submitted inference job {job.id} for study {study.id}")
        return job

    async def get_job_status(
        self, job_id: uuid.UUID, user_id: uuid.UUID, session: Session
    ) -> InferenceJob | None:
        """Get job status and details"""
        job = session.exec(
            select(InferenceJob).where(
                InferenceJob.id == job_id, InferenceJob.user_id == user_id
            )
        ).first()

        return job

    async def get_job_result(
        self, job_id: uuid.UUID, user_id: uuid.UUID, session: Session
    ) -> SegmentationResult | None:
        """Get completed job result"""
        job = await self.get_job_status(job_id, user_id, session)

        if not job:
            return None

        if job.status != "completed":
            raise ValueError(f"Job not completed (status: {job.status})")

        result = session.exec(
            select(SegmentationResult).where(SegmentationResult.job_id == job_id)
        ).first()

        return result

    async def list_user_jobs(
        self, user_id: uuid.UUID, session: Session, skip: int = 0, limit: int = 100
    ) -> List[InferenceJob]:
        """List jobs for user"""
        jobs = session.exec(
            select(InferenceJob)
            .where(InferenceJob.user_id == user_id)
            .order_by(InferenceJob.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).all()

        return list(jobs)

    async def cancel_job(
        self, job_id: uuid.UUID, user_id: uuid.UUID, session: Session
    ) -> InferenceJob:
        """Cancel pending/running job"""
        job = await self.get_job_status(job_id, user_id, session)

        if not job:
            raise ValueError("Job not found")

        if job.status in ["completed", "failed", "cancelled"]:
            raise ValueError(f"Cannot cancel job in status: {job.status}")

        # TODO: Revoke Celery task when worker is ready
        # from app.services.inference_service import celery_app
        # celery_app.control.revoke(str(job_id), terminate=True)

        # Update job status
        from datetime import datetime

        job.status = "cancelled"
        job.completed_at = datetime.utcnow()
        session.add(job)
        session.commit()
        session.refresh(job)

        logger.info(f"Cancelled inference job {job_id}")
        return job

    async def list_available_models(self, session: Session) -> List[InferenceModel]:
        """List available inference models"""
        models = session.exec(
            select(InferenceModel).where(InferenceModel.is_active == True)
        ).all()

        return list(models)


# Global service instance
inference_service = InferenceService()
