import logging
import numpy as np
import SimpleITK as sitk
from typing import Dict, Any, List, Tuple
import uuid
from pathlib import Path
import tempfile

from sqlmodel import Session, select, create_engine
from minio import Minio

from app.config import settings
from app.pipeline.model_configs import ModelConfigFactory

logger = logging.getLogger(__name__)


class Preprocessor:
    """Handles DICOM to NIfTI conversion and nnUNet preprocessing"""

    def __init__(self):
        self.minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    def process(
        self,
        job_id: uuid.UUID,
        study_id: uuid.UUID,
        series_id: uuid.UUID | None,
        session: Session,
        model_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Main preprocessing pipeline

        Args:
            job_id: Job identifier
            study_id: DICOM study ID
            series_id: Optional DICOM series ID
            session: Database session
            model_config: Model configuration dict from config.json

        Returns:
            Dict with:
                - 'image': preprocessed numpy array
                - 'metadata': metadata for postprocessing
        """
        # Import local worker models
        from app.db_models import DICOMMetadata, FileMetadata, DICOMSeries

        # 1. Load DICOM files from MinIO
        dicom_files = self._load_dicom_from_minio(
            study_id, series_id, session, DICOMMetadata, FileMetadata, DICOMSeries
        )

        # 2. Convert to NIfTI
        nifti_image = self._dicom_to_nifti(dicom_files)

        # 3. Get image as numpy array
        image_array = sitk.GetArrayFromImage(nifti_image)  # Shape: (Z, Y, X)

        # 4. Store original properties
        original_spacing = nifti_image.GetSpacing()  # (X, Y, Z)
        original_origin = nifti_image.GetOrigin()
        original_direction = nifti_image.GetDirection()
        original_shape = image_array.shape

        # 5. Crop to nonzero region
        bbox, cropped_array = self._crop_to_nonzero(image_array)

        # 6. Intensity normalization (MUST happen before resampling)
        # TODO: Create model-type-specific parameter extraction
        # This currently assumes nnUNet format, need to support MultiTalent
        normalized_array = self._normalize_intensity_from_config(
            cropped_array, model_config
        )

        # 7. Resample to target spacing
        # TODO: Create model-type-specific spacing extraction
        target_spacing = self._get_target_spacing_from_config(model_config)
        resampled_array = self._resample_image(
            normalized_array, original_spacing, target_spacing
        )

        # 8. Add batch and channel dimensions: (1, 1, Z, Y, X)
        preprocessed = resampled_array[np.newaxis, np.newaxis, ...]

        metadata = {
            "original_shape": original_shape,
            "original_spacing": original_spacing,  # (X, Y, Z) order
            "original_origin": original_origin,
            "original_direction": original_direction,
            "bbox": bbox,
            "target_spacing": tuple(target_spacing[::-1]),  # Convert (Z,Y,X) to (X,Y,Z) for consistency
            "cropped_shape": cropped_array.shape,
            "resampled_shape": resampled_array.shape,
        }

        logger.info(
            f"Preprocessing complete: {original_shape} -> {preprocessed.shape}"
        )

        return {"image": preprocessed, "metadata": metadata}

    def _load_dicom_from_minio(
        self,
        study_id: uuid.UUID,
        series_id: uuid.UUID | None,
        session: Session,
        DICOMMetadata,
        FileMetadata,
        DICOMSeries,
    ) -> List[Path]:
        """Download DICOM files from MinIO to temp directory"""
        temp_dir = Path(tempfile.mkdtemp(prefix=f"dicom_{study_id}_"))

        # Get all DICOM metadata for study/series
        query = select(DICOMMetadata, FileMetadata).join(
            FileMetadata, DICOMMetadata.file_id == FileMetadata.id
        )

        if series_id:
            query = query.where(DICOMMetadata.series_id == series_id)
        else:
            # Get all series in study
            query = (
                query.join(DICOMSeries, DICOMMetadata.series_id == DICOMSeries.id).where(
                    DICOMSeries.study_id == study_id
                )
            )

        results = session.exec(query).all()

        dicom_files = []
        for dicom_meta, file_meta in results:
            # Download from MinIO
            local_path = temp_dir / f"{dicom_meta.instance_number or 'unknown'}.dcm"
            self.minio_client.fget_object(
                settings.MINIO_BUCKET_NAME, file_meta.minio_path, str(local_path)
            )
            dicom_files.append(local_path)

        logger.info(f"Downloaded {len(dicom_files)} DICOM files")
        return dicom_files

    def _dicom_to_nifti(self, dicom_files: List[Path]) -> sitk.Image:
        """Convert DICOM series to NIfTI using SimpleITK"""
        reader = sitk.ImageSeriesReader()
        reader.SetFileNames([str(f) for f in dicom_files])
        image = reader.Execute()

        logger.info(
            f"Converted DICOM to NIfTI: shape={image.GetSize()}, spacing={image.GetSpacing()}"
        )
        return image

    def _crop_to_nonzero(self, array: np.ndarray) -> Tuple[tuple, np.ndarray]:
        """
        Crop image to nonzero bounding box

        Returns:
            bbox: (z_min, z_max, y_min, y_max, x_min, x_max)
            cropped: cropped array
        """
        # Find nonzero indices
        nonzero_mask = array != 0
        nonzero_indices = np.where(nonzero_mask)

        if len(nonzero_indices[0]) == 0:
            # No nonzero voxels, return original
            logger.warning("No nonzero voxels found, skipping crop")
            return (0, array.shape[0], 0, array.shape[1], 0, array.shape[2]), array

        # Get bounding box
        z_min, z_max = nonzero_indices[0].min(), nonzero_indices[0].max() + 1
        y_min, y_max = nonzero_indices[1].min(), nonzero_indices[1].max() + 1
        x_min, x_max = nonzero_indices[2].min(), nonzero_indices[2].max() + 1

        bbox = (z_min, z_max, y_min, y_max, x_min, x_max)
        cropped = array[z_min:z_max, y_min:y_max, x_min:x_max]

        logger.info(f"Cropped to nonzero: {array.shape} -> {cropped.shape}")
        return bbox, cropped

    def _get_target_spacing_from_config(self, config: Dict[str, Any]) -> tuple:
        """
        Extract target spacing from model config

        Uses ModelConfigParser to support multiple config formats:
        - nnUNet: config["model_parameters"]["spacing"]
        - MultiTalent: TBD (document format in multitalent_todo.md)
        """
        config_parser = ModelConfigFactory.get_parser(config)
        return config_parser.get_spacing()

    def _normalize_intensity_from_config(
        self, array: np.ndarray, config: Dict[str, Any]
    ) -> np.ndarray:
        """
        Apply intensity normalization based on model config

        Uses ModelConfigParser to support multiple config formats:
        - nnUNet: Uses normalization_schemes and foreground_properties
        - MultiTalent: TBD (document format in multitalent_todo.md)
        """
        config_parser = ModelConfigFactory.get_parser(config)
        norm_scheme = config_parser.get_normalization_scheme()
        foreground_props = config_parser.get_foreground_properties()

        return self._normalize_intensity(array, norm_scheme, foreground_props)

    def _normalize_intensity(
        self,
        array: np.ndarray,
        normalization_scheme: str,
        foreground_properties: Dict[str, float] | None = None,
    ) -> np.ndarray:
        """
        Apply intensity normalization

        Args:
            array: Input array
            normalization_scheme: Normalization type (e.g., "CTNormalization", "ZScoreNormalization")
            foreground_properties: Optional dict with percentiles/stats from training

        Returns:
            Normalized array
        """
        if normalization_scheme == "CTNormalization":
            # CT normalization with optional foreground properties
            if foreground_properties:
                lower_percentile = foreground_properties.get("percentile_00_5", np.percentile(array, 0.5))
                upper_percentile = foreground_properties.get("percentile_99_5", np.percentile(array, 99.5))
            else:
                lower_percentile = np.percentile(array, 0.5)
                upper_percentile = np.percentile(array, 99.5)

            # Clip
            clipped = np.clip(array, lower_percentile, upper_percentile)

            # Z-score normalization
            mean = clipped.mean()
            std = clipped.std()
            normalized = (clipped - mean) / (std + 1e-8)

            logger.info(
                f"CT normalization: percentiles=({lower_percentile:.1f}, {upper_percentile:.1f}), mean={mean:.1f}, std={std:.1f}"
            )

        elif normalization_scheme == "ZScoreNormalization":
            # Simple z-score normalization
            mean = array.mean()
            std = array.std()
            normalized = (array - mean) / (std + 1e-8)

            logger.info(f"ZScore normalization: mean={mean:.1f}, std={std:.1f}")

        else:
            # Default: foreground-based normalization for MRI-like data
            logger.warning(f"Unknown normalization scheme: {normalization_scheme}, using foreground-based")
            mask = array > array.mean()
            foreground = array[mask]

            if len(foreground) > 0:
                mean = foreground.mean()
                std = foreground.std()
                normalized = (array - mean) / (std + 1e-8)
            else:
                normalized = array

            logger.info(f"Foreground normalization: mean={mean:.1f}, std={std:.1f}")

        return normalized.astype(np.float32)

    def _resample_image(
        self,
        array: np.ndarray,
        original_spacing: tuple,
        target_spacing: tuple,
    ) -> np.ndarray:
        """
        Resample image to target spacing

        Uses SimpleITK for proper interpolation
        """
        # Convert array to SimpleITK image
        image = sitk.GetImageFromArray(array)
        # original_spacing is already in (X, Y, Z) order from GetSpacing()
        # GetImageFromArray converts (Z,Y,X) numpy array to (X,Y,Z) SimpleITK image
        image.SetSpacing(original_spacing)

        # Calculate new size
        original_size = image.GetSize()
        original_spacing_itk = image.GetSpacing()

        new_size = [
            int(
                round(
                    original_size[i]
                    * (original_spacing_itk[i] / target_spacing[::-1][i])
                )
            )
            for i in range(3)
        ]

        # Resample
        resampler = sitk.ResampleImageFilter()
        resampler.SetOutputSpacing(target_spacing[::-1])
        resampler.SetSize(new_size)
        resampler.SetOutputDirection(image.GetDirection())
        resampler.SetOutputOrigin(image.GetOrigin())
        resampler.SetTransform(sitk.Transform())
        resampler.SetDefaultPixelValue(0)
        resampler.SetInterpolator(sitk.sitkBSpline)  # 3rd order spline

        resampled_image = resampler.Execute(image)
        resampled_array = sitk.GetArrayFromImage(resampled_image)

        logger.info(
            f"Resampled: {array.shape} -> {resampled_array.shape}, spacing {original_spacing} -> {target_spacing}"
        )
        return resampled_array
