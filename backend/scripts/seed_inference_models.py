#!/usr/bin/env python3
"""
Seed database with available inference models

Usage:
    docker compose exec backend python scripts/seed_inference_models.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session, create_engine, select
from app.models import InferenceModel
from app.core.config import settings

def seed_models():
    """Seed database with available inference models"""

    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

    # Define models to seed
    models = [
        {
            "name": "nnUNet Lung Nodule Segmentation",
            "model_type": "nnunet",
            "onnx_path": "nnunet_test/3d_fullres/fold_0/checkpoint_final.onnx",
            "config_path": "nnunet_test/3d_fullres/fold_0/config.json",
            "modality": "CT",
            "description": "nnUNet model for lung nodule segmentation (Dataset002_Lung_Nodes)",
            "is_active": True
        },
        # Add more models here as they become available
        # {
        #     "name": "MultiTalent CT Multi-Organ v1",
        #     "model_type": "multitalent",
        #     "onnx_path": "multitalent_v1/fold_0.onnx",
        #     "config_path": "multitalent_v1/config.json",
        #     "modality": "CT",
        #     "description": "Production multi-dataset model for CT organ segmentation",
        #     "is_active": True
        # },
    ]

    print("=" * 60)
    print("Seeding Inference Models")
    print("=" * 60)

    with Session(engine) as session:
        for model_data in models:
            # Check if model already exists by name
            statement = select(InferenceModel).where(
                InferenceModel.name == model_data["name"]
            )
            existing = session.exec(statement).first()

            if not existing:
                model = InferenceModel(**model_data)
                session.add(model)
                print(f"✓ Added: {model_data['name']}")
                print(f"  - Type: {model_data['model_type']}")
                print(f"  - Modality: {model_data['modality']}")
                print(f"  - ONNX: {model_data['onnx_path']}")
                print(f"  - Config: {model_data['config_path']}")
            else:
                print(f"- Already exists: {model_data['name']}")
                print(f"  ID: {existing.id}")

        session.commit()

    print("=" * 60)
    print("✓ Model seeding complete!")
    print("=" * 60)

    # Display summary
    with Session(engine) as session:
        all_models = session.exec(select(InferenceModel)).all()
        print(f"\nTotal models in database: {len(all_models)}")
        print("\nActive models:")
        for model in all_models:
            if model.is_active:
                print(f"  - {model.name} ({model.modality})")

if __name__ == "__main__":
    try:
        seed_models()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
