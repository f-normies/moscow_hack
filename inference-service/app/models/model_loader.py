import logging
import json
from pathlib import Path
from typing import Dict, Any
import onnxruntime as ort

from app.config import settings

logger = logging.getLogger(__name__)


class ModelLoader:
    """Handles ONNX model loading and caching"""

    def __init__(self, models_path: str):
        self.models_path = Path(models_path)
        self.session_cache = {}
        self.config_cache = {}

    def load_model(self, onnx_path: str, config_path: str) -> ort.InferenceSession:
        """Load ONNX model with caching"""
        if onnx_path in self.session_cache:
            logger.info(f"Using cached model: {onnx_path}")
            return self.session_cache[onnx_path]

        full_path = self.models_path / onnx_path

        if not full_path.exists():
            raise FileNotFoundError(f"Model not found: {full_path}")

        # Configure providers
        providers = []
        for provider in settings.ONNX_PROVIDERS:
            if provider == "CUDAExecutionProvider":
                providers.append(
                    (
                        provider,
                        {
                            "device_id": 0,
                            "gpu_mem_limit": settings.GPU_MEMORY_LIMIT,
                            "arena_extend_strategy": "kSameAsRequested",
                        },
                    )
                )
            else:
                providers.append(provider)

        # Create session options
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        session_options.enable_mem_pattern = True
        session_options.enable_cpu_mem_arena = True

        # Load model
        session = ort.InferenceSession(
            str(full_path), sess_options=session_options, providers=providers
        )

        # Cache
        self.session_cache[onnx_path] = session

        logger.info(f"Loaded ONNX model: {onnx_path}")
        logger.info(f"Providers: {session.get_providers()}")

        return session

    def get_config(self, config_path: str) -> Dict[str, Any]:
        """Load model configuration JSON"""
        if config_path in self.config_cache:
            return self.config_cache[config_path]

        full_path = self.models_path / config_path

        if not full_path.exists():
            raise FileNotFoundError(f"Config not found: {full_path}")

        with open(full_path, "r") as f:
            config = json.load(f)

        # Cache
        self.config_cache[config_path] = config

        logger.info(f"Loaded config: {config_path}")
        return config
