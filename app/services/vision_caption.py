import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

MODEL_ID = "Salesforce/blip-image-captioning-base"

ROOT_DIR = Path("/home/google/symon-image-server")
RUNTIME_DIR = ROOT_DIR / "data/runtime_jobs"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def caption_loaded() -> bool:
    return False


def unload_caption_model():
    return {"ok": True, "unloaded": False, "reason": "BLIP is subprocess-only"}


def tail_text(value: str, lines: int = 80) -> str:
    return "\n".join((value or "").splitlines()[-lines:])


def caption_image_file(image_path: Path) -> dict[str, Any]:
    result_path = RUNTIME_DIR / f"blip_{uuid.uuid4()}.result.json"

    if result_path.exists():
        result_path.unlink()

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["PYTHONPATH"] = f"{ROOT_DIR}:{env.get('PYTHONPATH', '')}"

    cmd = [
        sys.executable,
        "-m",
        "app.workers.blip_caption_once",
        str(image_path),
        str(result_path),
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(ROOT_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result_path.exists():
        try:
            result = json.loads(result_path.read_text())
        except Exception:
            result = {"ok": False, "error": "could not read BLIP result JSON"}
    else:
        result = {"ok": False, "error": "BLIP worker did not write result JSON"}

    result["returncode"] = proc.returncode
    result["stdout_tail"] = tail_text(proc.stdout)
    result["stderr_tail"] = tail_text(proc.stderr)

    if proc.returncode != 0 and result.get("ok"):
        result["ok"] = False
        result["error"] = f"BLIP worker exited with code {proc.returncode}"

    if result.get("ok"):
        result["runtime"] = "subprocess_cpu"

    return result
