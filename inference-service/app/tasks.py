import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from celery import Task
from sqlmodel import Session, select, create_engine

from app.worker import celery_app
from app.config import settings
from app.pipeline.preprocessor import Preprocessor
from app.pipeline.inference import InferenceEngine
from app.pipeline.postprocessor import Postprocessor
from app.models.model_loader import ModelLoader

logger = logging.getLogger(__name__)

# Database engine for worker
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)


class InferenceTask(Task):
    """Base task with shared resources"""

    _model_loader = None
    _preprocessor = None
    _inference_engine = None
    _postprocessor = None

    @property
    def model_loader(self):
        if self._model_loader is None:
            self._model_loader = ModelLoader(settings.MODELS_PATH)
        return self._model_loader

    @property
    def preprocessor(self):
        if self._preprocessor is None:
            self._preprocessor = Preprocessor()
        return self._preprocessor

    @property
    def inference_engine(self):
        if self._inference_engine is None:
            self._inference_engine = InferenceEngine(
                providers=settings.ONNX_PROVIDERS,
                gpu_memory_limit=settings.GPU_MEMORY_LIMIT,
            )
        return self._inference_engine

    @property
    def postprocessor(self):
        if self._postprocessor is None:
            self._postprocessor = Postprocessor()
        return self._postprocessor


@celery_app.task(bind=True, base=InferenceTask, name="app.tasks.run_inference")
def run_inference_task(self, job_id_str: str) -> Dict[str, Any]:
    """Main inference task"""
    job_id = uuid.UUID(job_id_str)
    logger.info(f"Starting inference job {job_id}")

    try:
        # Import models from local worker models
        from app.db_models import (
            InferenceJob,
            InferenceModel,
            SegmentationResult,
        )

        with Session(engine) as session:
            # Get job details
            job = session.exec(
                select(InferenceJob).where(InferenceJob.id == job_id)
            ).first()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Update status
            job.status = "running"
            job.started_at = datetime.utcnow()
            job.progress = 0.0
            session.add(job)
            session.commit()

            # Get model details
            model = session.exec(
                select(InferenceModel).where(InferenceModel.id == job.model_id)
            ).first()

            if not model:
                raise ValueError(f"Model {job.model_id} not found")

            # Load model and config together
            logger.info(f"Loading model {model.name}")
            onnx_session, config = self.model_loader.load_model_with_config(
                model.onnx_path, model.config_path
            )
            job.progress = 0.1
            session.add(job)
            session.commit()

            # Preprocess
            logger.info(f"Preprocessing DICOM data for job {job_id}")
            preprocessed_data = self.preprocessor.process(
                job_id=job_id,
                study_id=job.study_id,
                series_id=job.series_id,
                session=session,
                model_config=config,
            )
            job.progress = 0.3
            session.add(job)
            session.commit()

            # Run inference with progress tracking
            logger.info(f"Running inference for job {job_id}")

            # Create progress callback to update DB during inference
            def update_inference_progress(current_patch: int, total_patches: int):
                """Update job progress during sliding window inference"""
                # Map patch progress to 0.3-0.7 range (40% of total job)
                patch_fraction = current_patch / total_patches
                job.progress = 0.3 + (patch_fraction * 0.4)
                session.add(job)
                session.commit()

            predictions = self.inference_engine.predict(
                onnx_session=onnx_session,
                input_data=preprocessed_data["image"],
                config=config,
                parameters=job.parameters or {},
                progress_callback=update_inference_progress,
            )
            job.progress = 0.7
            session.add(job)
            session.commit()

            # Postprocess
            logger.info(f"Postprocessing results for job {job_id}")
            result_path, metrics = self.postprocessor.process(
                predictions=predictions,
                preprocessed_metadata=preprocessed_data["metadata"],
                output_format=job.parameters.get("output_format", "nifti")
                if job.parameters
                else "nifti",
                job_id=job_id,
                model_config=config,
            )
            job.progress = 0.9
            session.add(job)
            session.commit()

            # Save result
            result = SegmentationResult(
                job_id=job_id,
                output_format=job.parameters.get("output_format", "nifti")
                if job.parameters
                else "nifti",
                file_path=result_path,
                classes=metrics.get("classes", {}),
                result_metadata=metrics,
            )
            session.add(result)

            # Update job
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.progress = 1.0
            job.result_path = result_path
            job.metrics = metrics
            session.add(job)
            session.commit()

            logger.info(f"Completed inference job {job_id}")
            return {"status": "completed", "job_id": str(job_id)}

    except Exception as e:
        logger.error(f"Error in inference job {job_id}: {e}", exc_info=True)

        # Update job status
        try:
            with Session(engine) as session:
                from app.db_models import InferenceJob

                job = session.exec(
                    select(InferenceJob).where(InferenceJob.id == job_id)
                ).first()

                if job:
                    job.status = "failed"
                    job.completed_at = datetime.utcnow()
                    job.error_message = str(e)
                    session.add(job)
                    session.commit()
        except Exception as update_error:
            logger.error(f"Failed to update job status: {update_error}")

        raise
