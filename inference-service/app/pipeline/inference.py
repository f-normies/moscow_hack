import logging
import numpy as np
import onnxruntime as ort
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class InferenceEngine:
    """ONNX-based inference with sliding window and Gaussian weighting"""

    def __init__(self, providers: List[str], gpu_memory_limit: int):
        self.providers = providers
        self.gpu_memory_limit = gpu_memory_limit

    def predict(
        self,
        onnx_session: ort.InferenceSession,
        input_data: np.ndarray,
        config: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> np.ndarray:
        """
        Run inference with sliding window

        Args:
            onnx_session: Loaded ONNX session
            input_data: Preprocessed image (1, 1, Z, Y, X)
            config: Model configuration (patch size, etc.)
            parameters: Job-specific parameters

        Returns:
            predictions: Logits or probabilities (1, num_classes, Z, Y, X)
        """
        patch_size = config.get("patch_size", [128, 128, 128])
        step_size = parameters.get("step_size", 0.5)  # 50% overlap
        use_gaussian = parameters.get("use_gaussian", True)
        use_tta = parameters.get("use_tta", False)  # Test-time augmentation

        logger.info(
            f"Running sliding window inference: patch_size={patch_size}, step_size={step_size}"
        )

        # Generate sliding window coordinates
        windows = self._generate_sliding_windows(
            input_data.shape[2:], patch_size, step_size  # (Z, Y, X)
        )

        # Initialize aggregation arrays
        _, _, d, h, w = input_data.shape
        num_classes = config.get("num_classes", 2)  # Binary by default
        aggregated_logits = np.zeros((1, num_classes, d, h, w), dtype=np.float32)
        aggregated_weights = np.zeros((1, 1, d, h, w), dtype=np.float32)

        # Create Gaussian importance map for weighting
        if use_gaussian:
            gaussian_map = self._create_gaussian_importance_map(patch_size)
        else:
            gaussian_map = np.ones(patch_size, dtype=np.float32)

        # Process each patch
        for i, (z_start, y_start, x_start) in enumerate(windows):
            z_end = z_start + patch_size[0]
            y_end = y_start + patch_size[1]
            x_end = x_start + patch_size[2]

            # Extract patch
            patch = input_data[:, :, z_start:z_end, y_start:y_end, x_start:x_end]

            # Run inference
            patch_logits = self._run_onnx_inference(onnx_session, patch)

            # Apply test-time augmentation if enabled
            if use_tta:
                patch_logits = self._apply_tta(onnx_session, patch, patch_logits)

            # Aggregate with Gaussian weighting
            aggregated_logits[:, :, z_start:z_end, y_start:y_end, x_start:x_end] += (
                patch_logits * gaussian_map[np.newaxis, np.newaxis, :]
            )
            aggregated_weights[:, :, z_start:z_end, y_start:y_end, x_start:x_end] += (
                gaussian_map[np.newaxis, np.newaxis, :]
            )

            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(windows)} patches")

        # Normalize by weights
        aggregated_logits /= aggregated_weights + 1e-8

        logger.info(
            f"Sliding window inference complete: {len(windows)} patches processed"
        )
        return aggregated_logits

    def _generate_sliding_windows(
        self, image_shape: Tuple[int, int, int], patch_size: List[int], step_size: float
    ) -> List[Tuple[int, int, int]]:
        """Generate sliding window coordinates"""
        d, h, w = image_shape
        pd, ph, pw = patch_size

        step_d = int(pd * step_size)
        step_h = int(ph * step_size)
        step_w = int(pw * step_size)

        windows = []
        for z in range(0, max(1, d - pd + 1), max(1, step_d)):
            for y in range(0, max(1, h - ph + 1), max(1, step_h)):
                for x in range(0, max(1, w - pw + 1), max(1, step_w)):
                    windows.append((z, y, x))

        # Handle edges if image doesn't divide evenly
        if d > pd and (d - pd) % step_d != 0:
            for y in range(0, max(1, h - ph + 1), max(1, step_h)):
                for x in range(0, max(1, w - pw + 1), max(1, step_w)):
                    windows.append((d - pd, y, x))

        if h > ph and (h - ph) % step_h != 0:
            for z in range(0, max(1, d - pd + 1), max(1, step_d)):
                for x in range(0, max(1, w - pw + 1), max(1, step_w)):
                    windows.append((z, h - ph, x))

        if w > pw and (w - pw) % step_w != 0:
            for z in range(0, max(1, d - pd + 1), max(1, step_d)):
                for y in range(0, max(1, h - ph + 1), max(1, step_h)):
                    windows.append((z, y, w - pw))

        return windows

    def _create_gaussian_importance_map(self, patch_size: List[int]) -> np.ndarray:
        """
        Create Gaussian importance map for patch weighting

        Higher weights at center (1.0), lower at edges (0.1)
        """
        d, h, w = patch_size

        # Create 1D Gaussian for each dimension
        gaussian_d = self._gaussian_1d(d, sigma=d / 8)
        gaussian_h = self._gaussian_1d(h, sigma=h / 8)
        gaussian_w = self._gaussian_1d(w, sigma=w / 8)

        # Create 3D Gaussian by outer product
        gaussian_map = (
            gaussian_d[:, np.newaxis, np.newaxis]
            * gaussian_h[np.newaxis, :, np.newaxis]
            * gaussian_w[np.newaxis, np.newaxis, :]
        )

        # Normalize to range [0.1, 1.0]
        gaussian_map = (gaussian_map - gaussian_map.min()) / (
            gaussian_map.max() - gaussian_map.min()
        )
        gaussian_map = gaussian_map * 0.9 + 0.1

        return gaussian_map.astype(np.float32)

    def _gaussian_1d(self, length: int, sigma: float) -> np.ndarray:
        """Generate 1D Gaussian"""
        x = np.arange(length)
        center = length / 2
        gaussian = np.exp(-((x - center) ** 2) / (2 * sigma**2))
        return gaussian

    def _run_onnx_inference(
        self, session: ort.InferenceSession, input_data: np.ndarray
    ) -> np.ndarray:
        """Run ONNX model inference on single patch"""
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name

        outputs = session.run([output_name], {input_name: input_data})
        return outputs[0]

    def _apply_tta(
        self,
        session: ort.InferenceSession,
        patch: np.ndarray,
        original_logits: np.ndarray,
    ) -> np.ndarray:
        """
        Apply test-time augmentation (mirroring)

        Average predictions from original and mirrored versions
        """
        augmented_predictions = [original_logits]

        # Mirror Z axis
        mirrored_z = np.flip(patch, axis=2)
        logits_z = self._run_onnx_inference(session, mirrored_z)
        logits_z = np.flip(logits_z, axis=2)
        augmented_predictions.append(logits_z)

        # Mirror Y axis
        mirrored_y = np.flip(patch, axis=3)
        logits_y = self._run_onnx_inference(session, mirrored_y)
        logits_y = np.flip(logits_y, axis=3)
        augmented_predictions.append(logits_y)

        # Mirror X axis
        mirrored_x = np.flip(patch, axis=4)
        logits_x = self._run_onnx_inference(session, mirrored_x)
        logits_x = np.flip(logits_x, axis=4)
        augmented_predictions.append(logits_x)

        # Average all predictions
        tta_logits = np.mean(augmented_predictions, axis=0)
        return tta_logits
