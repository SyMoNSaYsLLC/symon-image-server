from fastapi import APIRouter, Depends

from app.services.auth import require_account_api_key
from app.services.image_jobs import loaded_mode, queue_size
from app.services.qwen_runtime import qwen_pids, qwen_running
from app.services.vision_caption import MODEL_ID as VISION_MODEL_ID, caption_loaded

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/status")
def runtime_status(account: dict = Depends(require_account_api_key)):
    return {
        "ok": True,
        "account_id": account["account_id"],
        "models": {
            "text_to_text": {
                "name": "Qwen3-32B-GGUF",
                "running": qwen_running(),
                "pids": qwen_pids(),
                "url": "http://127.0.0.1:8080/v1",
            },
            "text_to_image": {
                "name": "SDXL Turbo/Base",
                "loaded_mode": loaded_mode(),
                "queue_size": queue_size(),
            },
            "image_to_text": {
                "name": VISION_MODEL_ID,
                "loaded": caption_loaded(),
            },
        },
    }
