from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.auth import require_account_api_key, require_api_key
from app.services.image_jobs import (
    submit_job,
    get_job,
    list_jobs,
    InsufficientCreditsError,
    UnsupportedModeError,
)

router = APIRouter(prefix="/sdxl", tags=["sdxl"])


class Txt2ImgRequest(BaseModel):
    prompt: str
    negative_prompt: str | None = None
    width: int = 1024
    height: int = 1024
    num_inference_steps: int | None = None
    guidance_scale: float | None = None
    mode: str = "fast"


@router.post("/txt2img/queue")
def txt2img_queue(
    req: Txt2ImgRequest,
    account: dict = Depends(require_account_api_key),
):
    try:
        payload = req.model_dump()
        payload["account_id"] = account["account_id"]
        return submit_job(payload)
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except UnsupportedModeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs")
def jobs(_auth: bool = Depends(require_api_key)):
    return {
        "ok": True,
        "jobs": list_jobs(),
    }


@router.get("/jobs/{job_id}")
def job_status(job_id: str, _auth: bool = Depends(require_api_key)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "ok": True,
        "job": job,
    }
