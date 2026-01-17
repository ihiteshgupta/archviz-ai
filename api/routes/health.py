"""Health check routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/health/gpu")
async def gpu_status():
    """Check GPU availability."""
    gpu_available = False
    gpu_info = None

    try:
        import torch

        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_info = {
                "device_count": torch.cuda.device_count(),
                "device_name": torch.cuda.get_device_name(0),
                "memory_total": torch.cuda.get_device_properties(0).total_memory,
            }
    except ImportError:
        pass

    return {
        "gpu_available": gpu_available,
        "gpu_info": gpu_info,
    }
