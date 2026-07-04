import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image

from app.services.auth import require_account_api_key
from app.services.vision_caption import MODEL_ID, caption_loaded, caption_image_file

router = APIRouter(prefix="/vision", tags=["vision"])

UPLOAD_DIR = Path("/home/google/symon-image-server/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/status")
def vision_status(account: dict = Depends(require_account_api_key)):
    return {
        "ok": True,
        "account_id": account["account_id"],
        "model": MODEL_ID,
        "loaded": caption_loaded(),
        "runtime": "warm_cpu",
    }


@router.post("/caption")
async def caption_image(
    image: UploadFile = File(...),
    account: dict = Depends(require_account_api_key),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="file must be an image")

    safe_name = Path(image.filename or "upload.png").name
    out_path = UPLOAD_DIR / f"{int(time.time())}_{safe_name}"

    data = await image.read()
    out_path.write_bytes(data)

    try:
        Image.open(out_path).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="could not read image")

    result = caption_image_file(out_path)

    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result)

    return {
        "ok": True,
        "account_id": account["account_id"],
        "filename": safe_name,
        "caption": result["caption"],
        "model": result["model"],
        "runtime": result.get("runtime", "warm_cpu"),
    }
