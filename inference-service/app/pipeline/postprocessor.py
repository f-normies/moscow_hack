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
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Postprocess predictions and upload to MinIO

        Returns:
            (minio_path, metrics)
        """
        # 1. Convert logits to segmentation mask
        segmentation = self._logits_to_segmentation(predictions)

        # 2. Resample to original spacing
        resampled_seg = self._resample_to_original(segmentation, preprocessed_metadata)

        # 3. Apply connected component analysis
        filtered_seg = self._connected_component_filter(resampled_seg)

        # 4. Restore original dimensions (uncrop)
        restored_seg = self._restore_original_shape(filtered_seg, preprocessed_metadata)

        # 5. Calculate metrics
        metrics = self._calculate_metrics(restored_seg)

        # 6. Convert to output format
        output_path = self._convert_to_format(
            restored_seg, preprocessed_metadata, output_format, job_id
        )

        # 7. Upload to MinIO
        minio_path = self._upload_to_minio(output_path, job_id)

        logger.info(f"Postprocessing complete: {minio_path}")
        return minio_path, metrics

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
        # Convert to SimpleITK
        seg_image = sitk.GetImageFromArray(segmentation)
        seg_image.SetSpacing(metadata["target_spacing"][::-1])

        # Resample to original spacing
        resampler = sitk.ResampleImageFilter()
        resampler.SetOutputSpacing(metadata["original_spacing"][::-1])

        # Calculate output size based on cropped shape
        cropped_shape = metadata["cropped_shape"]
        target_spacing = metadata["target_spacing"]
        original_spacing = metadata["original_spacing"]

        output_size = [
            int(
                round(
                    cropped_shape[2 - i]
                    * (original_spacing[i] / target_spacing[i])
                )
            )
            for i in range(3)
        ]

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

    def _calculate_metrics(self, segmentation: np.ndarray) -> Dict[str, Any]:
        """Calculate quality metrics"""
        unique_classes = np.unique(segmentation)
        class_volumes = {}
        class_counts = {}

        for class_id in unique_classes:
            if class_id == 0:  # Skip background
                continue

            class_mask = segmentation == class_id
            class_counts[int(class_id)] = int(np.sum(class_mask))
            class_volumes[int(class_id)] = float(np.sum(class_mask))  # In voxels

        metrics = {
            "classes": {
                "detected": list(unique_classes.tolist()),
                "counts": class_counts,
                "volumes": class_volumes,
            },
            "total_foreground_voxels": int(np.sum(segmentation > 0)),
            "shape": segmentation.shape,
        }

        return metrics

    def _convert_to_format(
        self,
        segmentation: np.ndarray,
        metadata: Dict[str, Any],
        output_format: str,
        job_id: uuid.UUID,
    ) -> Path:
        """Convert segmentation to output format"""
        temp_dir = Path(tempfile.mkdtemp(prefix=f"result_{job_id}_"))

        if output_format == "nifti":
            output_path = temp_dir / f"{job_id}.nii.gz"

            # Convert to SimpleITK image
            image = sitk.GetImageFromArray(segmentation)
            image.SetSpacing(metadata["original_spacing"][::-1])
            image.SetOrigin(metadata["original_origin"])
            image.SetDirection(metadata["original_direction"])

            # Save as NIfTI
            sitk.WriteImage(image, str(output_path), useCompression=True)

        elif output_format == "dicom-seg":
            # TODO: Implement DICOM-SEG export using pydicom-seg
            output_path = temp_dir / f"{job_id}.dcm"
            raise NotImplementedError("DICOM-SEG export not yet implemented")

        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        logger.info(f"Converted to {output_format}: {output_path}")
        return output_path

    def _upload_to_minio(self, file_path: Path, job_id: uuid.UUID) -> str:
        """Upload result to MinIO"""
        object_name = f"inference_results/{job_id}/{file_path.name}"

        self.minio_client.fput_object(
            settings.MINIO_BUCKET_NAME, object_name, str(file_path)
        )

        logger.info(f"Uploaded to MinIO: {object_name}")
        return object_name
