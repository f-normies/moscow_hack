import logging
import numpy as np
import SimpleITK as sitk
from typing import Dict, Any, Tuple
import uuid
from pathlib import Path
import tempfile
from scipy import ndimage
from skimage.measure import label

from minio import Minio
from app.config import settings
from app.pipeline.model_configs import ModelConfigFactory

logger = logging.getLogger(__name__)


class Postprocessor:
    """Handles postprocessing and output generation"""

    def __init__(self):
        self.minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    def process(
        self,
        predictions: np.ndarray,
        preprocessed_metadata: Dict[str, Any],
        output_format: str,
        job_id: uuid.UUID,
        model_config: Dict[str, Any],
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Postprocess predictions and upload to MinIO

        Args:
            predictions: Model output logits
            preprocessed_metadata: Metadata from preprocessing
            output_format: Output format (nifti, dicom-seg)
            job_id: Job identifier
            model_config: Model configuration from config.json

        Returns:
            (segmentation_path, source_ct_path, metrics)
        """
        # 1. Convert logits to segmentation mask
        segmentation = self._logits_to_segmentation(predictions)

        # 2. Resample to original spacing
        resampled_seg = self._resample_to_original(segmentation, preprocessed_metadata)

        # 3. Apply connected component analysis
        filtered_seg = self._connected_component_filter(resampled_seg)

        # 4. Restore original dimensions (uncrop)
        restored_seg = self._restore_original_shape(filtered_seg, preprocessed_metadata)

        # 5. Calculate metrics with class names from config
        # TODO: Support multiple config formats for class names
        metrics = self._calculate_metrics(restored_seg, model_config)

        # 6. Convert segmentation to output format
        seg_output_path = self._convert_to_format(
            restored_seg, preprocessed_metadata, output_format, job_id, suffix="_seg"
        )

        # 7. Save processed source CT image
        ct_output_path = self._save_processed_ct(
            preprocessed_metadata, job_id
        )

        # 8. Upload both to MinIO
        seg_minio_path = self._upload_to_minio(seg_output_path, job_id, "segmentation")
        ct_minio_path = self._upload_to_minio(ct_output_path, job_id, "source_ct")

        logger.info(f"Postprocessing complete: seg={seg_minio_path}, ct={ct_minio_path}")
        return seg_minio_path, ct_minio_path, metrics

    def _logits_to_segmentation(self, logits: np.ndarray) -> np.ndarray:
        """Convert logits to segmentation mask (argmax)"""
        # logits shape: (1, num_classes, Z, Y, X)
        # segmentation shape: (Z, Y, X)
        segmentation = np.argmax(logits[0], axis=0).astype(np.uint8)

        logger.info(f"Converted logits to segmentation: {np.unique(segmentation)}")
        return segmentation

    def _resample_to_original(
        self, segmentation: np.ndarray, metadata: Dict[str, Any]
    ) -> np.ndarray:
        """Resample segmentation back to original spacing"""
        # Both spacings are now in (X, Y, Z) order for consistency
        target_spacing = metadata["target_spacing"]  # (X, Y, Z)
        original_spacing = metadata["original_spacing"]  # (X, Y, Z)

        # Convert to SimpleITK (numpy Z,Y,X → SimpleITK X,Y,Z)
        seg_image = sitk.GetImageFromArray(segmentation)
        seg_image.SetSpacing(target_spacing)

        # Resample to original spacing
        resampler = sitk.ResampleImageFilter()
        resampler.SetOutputSpacing(original_spacing)

        # Use cropped_shape from metadata as the target size
        # This is the shape BEFORE resampling to target_spacing
        cropped_shape = metadata["cropped_shape"]  # (Z, Y, X)
        output_size = list(cropped_shape[::-1])  # Convert to (X, Y, Z) for SimpleITK

        resampler.SetSize(output_size)
        resampler.SetOutputDirection(seg_image.GetDirection())
        resampler.SetOutputOrigin(seg_image.GetOrigin())
        resampler.SetTransform(sitk.Transform())
        resampler.SetDefaultPixelValue(0)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)  # Nearest for labels

        resampled_image = resampler.Execute(seg_image)
        resampled_array = sitk.GetArrayFromImage(resampled_image)

        logger.info(
            f"Resampled to original spacing: {segmentation.shape} -> {resampled_array.shape}"
        )
        return resampled_array

    def _connected_component_filter(self, segmentation: np.ndarray) -> np.ndarray:
        """
        Remove small connected components

        Two-step process:
        1. Foreground-level filtering (all classes as one)
        2. Class-level filtering (individual classes)
        """
        filtered = segmentation.copy()

        # Step 1: Foreground filtering
        foreground_mask = segmentation > 0
        labeled_fg, num_fg = label(foreground_mask, connectivity=3, return_num=True)

        if num_fg > 1:
            # Keep only largest foreground component
            component_sizes = [
                np.sum(labeled_fg == i) for i in range(1, num_fg + 1)
            ]
            largest_component = np.argmax(component_sizes) + 1
            foreground_mask = labeled_fg == largest_component
            filtered = segmentation * foreground_mask

            logger.info(f"Removed {num_fg - 1} small foreground components")

        # Step 2: Per-class filtering
        unique_classes = np.unique(filtered)
        unique_classes = unique_classes[unique_classes > 0]  # Exclude background

        for class_id in unique_classes:
            class_mask = filtered == class_id
            labeled_class, num_class = label(class_mask, connectivity=3, return_num=True)

            if num_class > 1:
                # Keep only largest component for this class
                component_sizes = [
                    np.sum(labeled_class == i) for i in range(1, num_class + 1)
                ]
                largest_component = np.argmax(component_sizes) + 1
                class_mask = labeled_class == largest_component
                filtered[filtered == class_id] = 0
                filtered[class_mask] = class_id

                logger.info(
                    f"Class {class_id}: removed {num_class - 1} small components"
                )

        return filtered

    def _restore_original_shape(
        self, segmentation: np.ndarray, metadata: Dict[str, Any]
    ) -> np.ndarray:
        """Restore original image dimensions by uncropping"""
        bbox = metadata["bbox"]
        z_min, z_max, y_min, y_max, x_min, x_max = bbox

        # Create array with original shape
        original_shape = metadata["original_shape"]
        restored = np.zeros(original_shape, dtype=segmentation.dtype)

        # Place cropped segmentation back into original position
        restored[z_min:z_max, y_min:y_max, x_min:x_max] = segmentation

        logger.info(f"Restored original shape: {segmentation.shape} -> {restored.shape}")
        return restored

    def _extract_class_names_from_config(
        self, config: Dict[str, Any]
    ) -> Dict[int, str]:
        """
        Extract class ID to name mapping from model config

        Uses ModelConfigParser to support multiple config formats:
        - nnUNet: config["dataset_parameters"]["class_names"]
        - MultiTalent: TBD (document format in multitalent_todo.md)
        """
        config_parser = ModelConfigFactory.get_parser(config)
        class_names = config_parser.get_class_names()
        # Convert string keys to int if needed
        return {int(k): v for k, v in class_names.items()}

    def _calculate_metrics(
        self, segmentation: np.ndarray, model_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate quality metrics with class name mapping

        Args:
            segmentation: Segmentation mask
            model_config: Model configuration for class names
        """
        unique_classes = np.unique(segmentation)
        class_names_map = self._extract_class_names_from_config(model_config)

        class_info = {}
        for class_id in unique_classes:
            if class_id == 0:  # Skip background
                continue

            class_mask = segmentation == class_id
            voxel_count = int(np.sum(class_mask))

            class_name = class_names_map.get(int(class_id), f"class_{class_id}")

            class_info[class_name] = {
                "class_id": int(class_id),
                "voxel_count": voxel_count,
                "volume_mm3": float(voxel_count),  # TODO: Calculate with spacing
            }

        metrics = {
            "detected_classes": class_info,
            "total_foreground_voxels": int(np.sum(segmentation > 0)),
            "output_shape": list(segmentation.shape),
            "unique_class_ids": unique_classes.tolist(),
        }

        return metrics

    def _convert_to_format(
        self,
        segmentation: np.ndarray,
        metadata: Dict[str, Any],
        output_format: str,
        job_id: uuid.UUID,
        suffix: str = "",
    ) -> Path:
        """Convert segmentation to output format"""
        temp_dir = Path(tempfile.mkdtemp(prefix=f"result_{job_id}_"))

        if output_format == "nifti":
            output_path = temp_dir / f"{job_id}{suffix}.nii.gz"

            # Convert to SimpleITK image
            image = sitk.GetImageFromArray(segmentation)
            image.SetSpacing(metadata["original_spacing"][::-1])
            image.SetOrigin(metadata["original_origin"])
            image.SetDirection(metadata["original_direction"])

            # Save as NIfTI
            sitk.WriteImage(image, str(output_path), useCompression=True)

        elif output_format == "dicom-seg":
            # TODO: Implement DICOM-SEG export using pydicom-seg
            output_path = temp_dir / f"{job_id}{suffix}.dcm"
            raise NotImplementedError("DICOM-SEG export not yet implemented")

        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        logger.info(f"Converted to {output_format}: {output_path}")
        return output_path

    def _save_processed_ct(
        self, metadata: Dict[str, Any], job_id: uuid.UUID
    ) -> Path:
        """
        Save processed original CT image

        Creates NIfTI file with same geometric properties as segmentation
        for perfect alignment in visualization tools.

        Args:
            metadata: Preprocessing metadata containing original_image
            job_id: Job identifier

        Returns:
            Path to saved CT NIfTI file
        """
        temp_dir = Path(tempfile.mkdtemp(prefix=f"ct_{job_id}_"))
        output_path = temp_dir / f"{job_id}_ct.nii.gz"

        # Get original image from metadata
        original_image = metadata["original_image"]

        # Convert to SimpleITK image with same properties as segmentation
        ct_image = sitk.GetImageFromArray(original_image)
        ct_image.SetSpacing(metadata["original_spacing"][::-1])  # Convert to X,Y,Z
        ct_image.SetOrigin(metadata["original_origin"])
        ct_image.SetDirection(metadata["original_direction"])

        # Save as NIfTI
        sitk.WriteImage(ct_image, str(output_path), useCompression=True)

        logger.info(f"Saved processed CT: {output_path}, shape={original_image.shape}")
        return output_path

    def _upload_to_minio(
        self, file_path: Path, job_id: uuid.UUID, file_type: str = "result"
    ) -> str:
        """Upload result to MinIO"""
        object_name = f"inference_results/{job_id}/{file_path.name}"

        self.minio_client.fput_object(
            settings.MINIO_BUCKET_NAME, object_name, str(file_path)
        )

        logger.info(f"Uploaded {file_type} to MinIO: {object_name}")
        return object_name
