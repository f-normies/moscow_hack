"""
Model configuration parsers for different model types.

Handles extraction of preprocessing/inference parameters from various config formats:
- nnUNet: Uses model_parameters and dataset_parameters structure
- MultiTalent: TBD (to be documented)
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


class ModelConfigParser(ABC):
    """Base class for model configuration parsing"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def get_patch_size(self) -> List[int]:
        """Extract patch size for inference"""
        pass

    @abstractmethod
    def get_spacing(self) -> Tuple[float, ...]:
        """Extract target spacing for preprocessing"""
        pass

    @abstractmethod
    def get_normalization_scheme(self) -> str:
        """Extract normalization scheme name"""
        pass

    @abstractmethod
    def get_foreground_properties(self) -> Optional[Dict[str, float]]:
        """Extract foreground intensity properties for normalization"""
        pass

    @abstractmethod
    def get_num_classes(self) -> int:
        """Extract number of output classes"""
        pass

    @abstractmethod
    def get_class_names(self) -> Dict[str, str]:
        """Extract class ID to name mapping"""
        pass


class NnUNetConfigParser(ModelConfigParser):
    """Parser for nnUNet v2 configuration format"""

    def get_patch_size(self) -> List[int]:
        """
        Extract patch size from nnUNet config

        nnUNet stores it at: model_parameters.patch_size
        """
        if "model_parameters" in self.config and "patch_size" in self.config["model_parameters"]:
            patch_size = self.config["model_parameters"]["patch_size"]
            logger.info(f"nnUNet patch_size: {patch_size}")
            return patch_size

        # Fallback
        logger.warning("Could not find patch_size in nnUNet config, using default")
        return [128, 128, 128]

    def get_spacing(self) -> Tuple[float, ...]:
        """
        Extract target spacing from nnUNet config

        nnUNet stores it at: model_parameters.spacing
        """
        if "model_parameters" in self.config and "spacing" in self.config["model_parameters"]:
            spacing = tuple(self.config["model_parameters"]["spacing"])
            logger.info(f"nnUNet spacing: {spacing}")
            return spacing

        # Fallback
        logger.warning("Could not find spacing in nnUNet config, using default")
        return (1.0, 1.0, 1.0)

    def get_normalization_scheme(self) -> str:
        """
        Extract normalization scheme from nnUNet config

        nnUNet stores it at: model_parameters.normalization_schemes[0]
        """
        if "model_parameters" in self.config and "normalization_schemes" in self.config["model_parameters"]:
            schemes = self.config["model_parameters"]["normalization_schemes"]
            if schemes and len(schemes) > 0:
                scheme = schemes[0]
                logger.info(f"nnUNet normalization scheme: {scheme}")
                return scheme

        # Fallback to CT
        logger.warning("Could not find normalization scheme in nnUNet config, using CTNormalization")
        return "CTNormalization"

    def get_foreground_properties(self) -> Optional[Dict[str, float]]:
        """
        Extract foreground intensity properties from nnUNet config

        nnUNet stores it at: dataset_parameters.channels.0.foreground_properties
        """
        if "dataset_parameters" in self.config:
            channels = self.config["dataset_parameters"].get("channels", {})
            if "0" in channels:
                fg_props = channels["0"].get("foreground_properties")
                if fg_props:
                    logger.info(f"nnUNet foreground properties: {list(fg_props.keys())}")
                    return fg_props

        logger.info("No foreground properties found in nnUNet config")
        return None

    def get_num_classes(self) -> int:
        """
        Extract number of classes from nnUNet config

        nnUNet stores it at: dataset_parameters.num_classes
        """
        if "dataset_parameters" in self.config and "num_classes" in self.config["dataset_parameters"]:
            num_classes = self.config["dataset_parameters"]["num_classes"]
            logger.info(f"nnUNet num_classes: {num_classes}")
            return num_classes

        # Fallback to binary
        logger.warning("Could not find num_classes in nnUNet config, using 2 (binary)")
        return 2

    def get_class_names(self) -> Dict[str, str]:
        """
        Extract class names from nnUNet config

        nnUNet stores it at: dataset_parameters.class_names
        """
        if "dataset_parameters" in self.config and "class_names" in self.config["dataset_parameters"]:
            class_names = self.config["dataset_parameters"]["class_names"]
            logger.info(f"nnUNet class_names: {class_names}")
            return class_names

        # Fallback
        logger.warning("Could not find class_names in nnUNet config")
        return {}


class MultiTalentConfigParser(ModelConfigParser):
    """
    Parser for MultiTalent configuration format

    TODO: Implement based on MultiTalent config structure
    Document format in: .claude/tasks/multitalent_todo.md
    """

    def get_patch_size(self) -> List[int]:
        # TODO: Implement MultiTalent patch_size extraction
        logger.warning("MultiTalent config parser not yet implemented, using defaults")
        return [128, 128, 128]

    def get_spacing(self) -> Tuple[float, ...]:
        # TODO: Implement MultiTalent spacing extraction
        return (1.0, 1.0, 1.0)

    def get_normalization_scheme(self) -> str:
        # TODO: Implement MultiTalent normalization extraction
        return "CTNormalization"

    def get_foreground_properties(self) -> Optional[Dict[str, float]]:
        # TODO: Implement MultiTalent foreground properties extraction
        return None

    def get_num_classes(self) -> int:
        # TODO: Implement MultiTalent num_classes extraction
        return 2

    def get_class_names(self) -> Dict[str, str]:
        # TODO: Implement MultiTalent class_names extraction
        return {}


class ModelConfigFactory:
    """Factory for creating appropriate config parser"""

    @staticmethod
    def get_parser(config: Dict[str, Any]) -> ModelConfigParser:
        """
        Create appropriate config parser based on model type

        Args:
            config: Model configuration dict

        Returns:
            Appropriate ModelConfigParser instance
        """
        model_type = config.get("model_type", "nnunet").lower()

        if model_type == "nnunet":
            return NnUNetConfigParser(config)
        elif model_type == "multitalent":
            return MultiTalentConfigParser(config)
        else:
            logger.warning(f"Unknown model_type '{model_type}', defaulting to nnUNet parser")
            return NnUNetConfigParser(config)
