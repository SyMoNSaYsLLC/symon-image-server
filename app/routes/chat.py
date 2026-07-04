import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth import require_account_api_key
from app.services.image_jobs import unload_pipe
from app.services.qwen_runtime import QWEN_URL, qwen_running, start_qwen
from app.services.vision_caption import unload_caption_model

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    max_tokens: int = 512
    temperature: float = 0.2


@router.get("/status")
def chat_status(_account: dict = Depends(require_account_api_key)):
    return {
        "ok": True,
        "qwen_running": qwen_running(),
        "llm_base_url": QWEN_URL,
    }


@router.post("/complete")
def chat_complete(req: ChatRequest, account: dict = Depends(require_account_api_key)):
    unload_pipe()
    unload_caption_model()

    started = start_qwen()
    if not started.get("ok"):
        raise HTTPException(status_code=503, detail=started)

    try:
        r = requests.post(
            f"{QWEN_URL}/chat/completions",
            json={
                "model": "local",
                "messages": [
                    {
                        "role": "user",
                        "content": "/no_think\n" + req.message,
                    }
                ],
                "max_tokens": req.max_tokens,
                "temperature": req.temperature,
            },
            timeout=180,
        )
        r.raise_for_status()
        data = r.json()

        return {
            "ok": True,
            "account_id": account["account_id"],
            "content": data["choices"][0]["message"].get("content", ""),
            "usage": data.get("usage"),
            "timings": data.get("timings"),
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))
