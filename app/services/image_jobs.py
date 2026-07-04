import gc
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import torch

from app.services.job_db import save_job, get_job_db, list_jobs_db, load_recent_jobs
from app.services.payment_db import spend_credits, add_credits, get_balance
from app.services.qwen_runtime import stop_qwen

ROOT_DIR = Path("/home/google/symon-image-server")
OUTPUT_DIR = ROOT_DIR / "data/outputs"
RUNTIME_DIR = ROOT_DIR / "data/runtime_jobs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

JOBS: dict[str, dict[str, Any]] = load_recent_jobs(limit=200)
JOB_QUEUE: "queue.Queue[str]" = queue.Queue()

_worker_started = False

MODELS = {
    "fast": {
        "model_id": "stabilityai/sdxl-turbo",
    },
    "quality": {
        "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
    },
}

CREDIT_COSTS = {
    "fast": 1,
    "quality": 5,
}


class InsufficientCreditsError(Exception):
    pass


class UnsupportedModeError(Exception):
    pass


def clear_cuda():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


def unload_pipe():
    # SDXL now runs in a one-shot subprocess, so the API process keeps no pipe.
    clear_cuda()


def loaded_mode() -> str | None:
    # Main uvicorn process no longer keeps SDXL resident.
    return None


def tail_text(value: str, lines: int = 80) -> str:
    return "\n".join((value or "").splitlines()[-lines:])


def run_sdxl_subprocess(job: dict[str, Any]) -> dict[str, Any]:
    job_id = job["job_id"]

    job_path = RUNTIME_DIR / f"{job_id}.json"
    result_path = RUNTIME_DIR / f"{job_id}.result.json"

    job_path.write_text(json.dumps(job, indent=2))

    if result_path.exists():
        result_path.unlink()

    env = os.environ.copy()

    # Main FastAPI service has CUDA_VISIBLE_DEVICES empty.
    # SDXL worker must explicitly get GPU access.
    env["CUDA_VISIBLE_DEVICES"] = "0"
    env["NVIDIA_VISIBLE_DEVICES"] = "0"
    env["PYTHONPATH"] = f"{ROOT_DIR}:{env.get('PYTHONPATH', '')}"
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    cmd = [
        sys.executable,
        "-m",
        "app.workers.sdxl_generate_once",
        str(job_path),
        str(result_path),
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(ROOT_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )

    if result_path.exists():
        try:
            result = json.loads(result_path.read_text())
        except Exception:
            result = {"ok": False, "error": "could not read SDXL result JSON"}
    else:
        result = {"ok": False, "error": "SDXL worker did not write result JSON"}

    result["returncode"] = proc.returncode
    result["stdout_tail"] = tail_text(proc.stdout)
    result["stderr_tail"] = tail_text(proc.stderr)

    if proc.returncode != 0 and result.get("ok"):
        result["ok"] = False
        result["error"] = f"SDXL worker exited with code {proc.returncode}"

    return result


def worker_loop():
    while True:
        job_id = JOB_QUEUE.get()
        job = JOBS[job_id]

        try:
            job["status"] = "running"
            job["started_at"] = time.time()
            save_job(job)

            mode = job["mode"]

            # One GPU owner at a time.
            stop_qwen()

            try:
                from app.services.vision_caption import unload_caption_model
                unload_caption_model()
            except Exception:
                pass

            clear_cuda()

            result = run_sdxl_subprocess(job)

            if not result.get("ok"):
                raise RuntimeError(result)

            job["status"] = "done"
            job["filename"] = result["filename"]
            job["path"] = result["path"]
            job["url"] = result["url"]
            job["seconds"] = result["seconds"]
            job["resolved_steps"] = result.get("resolved_steps")
            job["resolved_guidance"] = result.get("resolved_guidance")
            job["error"] = None

        except Exception as e:
            job["status"] = "error"
            job["error"] = str(e)

            if job.get("credits_charged") and not job.get("credits_refunded"):
                add_credits(
                    job["account_id"],
                    int(job["credit_cost"]),
                    reason="image_job_refund",
                    ref_id=job_id,
                )
                job["credits_refunded"] = True

        finally:
            job["finished_at"] = time.time()
            save_job(job)
            clear_cuda()
            JOB_QUEUE.task_done()


def ensure_worker():
    global _worker_started
    if not _worker_started:
        t = threading.Thread(target=worker_loop, daemon=True)
        t.start()
        _worker_started = True


def submit_job(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_worker()

    mode = payload.get("mode", "fast")
    if mode not in MODELS:
        raise UnsupportedModeError(f"unsupported mode: {mode}")

    account_id = payload.get("account_id", "dev")
    credit_cost = CREDIT_COSTS[mode]
    job_id = str(uuid.uuid4())

    paid = spend_credits(
        account_id,
        credit_cost,
        reason=f"image_job_{mode}",
        ref_id=job_id,
    )

    if not paid:
        balance = get_balance(account_id)
        raise InsufficientCreditsError(
            f"insufficient credits: account={account_id}, balance={balance}, required={credit_cost}"
        )

    job = {
        "job_id": job_id,
        "account_id": account_id,
        "status": "queued",
        "created_at": time.time(),
        "prompt": payload["prompt"],
        "negative_prompt": payload.get("negative_prompt"),
        "width": payload.get("width", 1024),
        "height": payload.get("height", 1024),
        "num_inference_steps": payload.get("num_inference_steps"),
        "guidance_scale": payload.get("guidance_scale"),
        "mode": mode,
        "credit_cost": credit_cost,
        "credits_charged": True,
        "credits_refunded": False,
    }

    JOBS[job_id] = job
    save_job(job)
    JOB_QUEUE.put(job_id)

    return {
        "ok": True,
        "job_id": job_id,
        "account_id": account_id,
        "status": "queued",
        "queue_size": JOB_QUEUE.qsize(),
        "mode": mode,
        "credit_cost": credit_cost,
        "remaining_credits": get_balance(account_id),
    }


def get_job(job_id: str):
    return JOBS.get(job_id) or get_job_db(job_id)


def list_jobs():
    return list_jobs_db(limit=100)


def queue_size() -> int:
    return JOB_QUEUE.qsize()


def worker_started() -> bool:
    return _worker_started
