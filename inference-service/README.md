# Inference Service

AI inference microservice for medical image segmentation using ONNX Runtime.

## Deployment Options

The inference service supports flexible deployment on both CPU and GPU infrastructure.

### GPU Deployment (Production)

For production environments with GPU acceleration:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

**Requirements:**
- NVIDIA GPU with 8GB+ VRAM
- NVIDIA Docker runtime
- CUDA 11.8+ drivers

**Performance:**
- CT Chest (512×512×300): 15-30 seconds
- Throughput: 4-6 studies/minute

### CPU Deployment (Development)

For local development or environments without GPU:

```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d
```

**Suitable for:**
- Local development without GPU
- Low-volume deployments
- Budget-constrained environments

**Performance:**
- CT Chest (512×512×300): 3-5 minutes
- Throughput: ~0.5 studies/minute

**Note:** CPU inference is 6-10x slower than GPU.

### Mixed Deployment (Advanced)

Run both CPU and GPU workers simultaneously:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.cpu.yml up -d
```

GPU handles priority jobs, CPU handles overflow.

## Architecture

### CPU Mode
- Base image: `python:3.10-slim` (~150MB)
- Runtime: `onnxruntime` (CPU-only)
- Total size: ~800MB
- Concurrency: 2 workers

### GPU Mode
- Base image: `nvidia/cuda:11.8.0-cudnn8-runtime` (~1.5GB)
- Runtime: `onnxruntime-gpu` (CUDA-enabled)
- Total size: ~3GB
- Concurrency: 1 worker (GPU bound)

### Provider Auto-Detection

The service automatically detects available ONNX execution providers at runtime:

```python
settings.effective_onnx_providers  # Returns available providers
```

If CUDA is unavailable, the service gracefully falls back to CPU.

## Development

### Building Images

Build CPU worker:
```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml build inference-worker-cpu
```

Build GPU worker:
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml build inference-worker-gpu
```

### Viewing Logs

CPU worker:
```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml logs -f inference-worker-cpu
```

GPU worker:
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs -f inference-worker-gpu
```

### Configuration

Environment variables (set in `.env`):
- `REDIS_URL` - Celery broker URL
- `POSTGRES_SERVER` - Database host
- `MINIO_ENDPOINT` - Object storage endpoint
- `MODELS_PATH` - Path to ONNX models directory
- `ONNX_PROVIDERS` - Requested execution providers (JSON array)

## Testing

Verify provider detection:
```bash
# Check logs for provider info
docker compose logs inference-worker-cpu | grep "ONNX providers"
```

Expected output:
```
ONNX providers requested: ['CPUExecutionProvider']
ONNX providers available: ['CPUExecutionProvider']
ONNX providers using: ['CPUExecutionProvider']
```

## Troubleshooting

### GPU worker not using GPU

Check NVIDIA Docker runtime:
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base nvidia-smi
```

### ONNX Runtime errors

Check provider availability:
```python
import onnxruntime as ort
print(ort.get_available_providers())
```

### Worker not connecting to Redis

Verify Redis health:
```bash
docker compose exec redis redis-cli ping
```
