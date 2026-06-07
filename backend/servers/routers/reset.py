from fastapi import APIRouter, HTTPException
from erp import client as erp

router = APIRouter()


@router.post("/")
async def reset_environment():
    """Reset all VMs and ERP activities to the initial state."""
    try:
        result = await erp.reset_me()

        # Also clear the local pipeline cache
        from routers.tickets import _pipeline_cache, _pipeline_running
        _pipeline_cache.clear()
        _pipeline_running.clear()

        return {"ok": True, "detail": result}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
