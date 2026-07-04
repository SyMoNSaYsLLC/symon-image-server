import os
import time
import subprocess
from fastapi import APIRouter, Depends

from app.services.auth import require_api_key
from app.services.job_db import list_jobs_db
from app.services.image_jobs import queue_size, loaded_mode, worker_started

router = APIRouter(prefix="/admin", tags=["admin"])

START_TIME = time.time()


def get_gpu_status():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw,power.limit",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return {
                "ok": False,
                "error": result.stderr.strip(),
            }

        parts = [p.strip() for p in result.stdout.strip().split(",")]

        return {
            "ok": True,
            "name": parts[0],
            "memory_used_mib": int(parts[1]),
            "memory_total_mib": int(parts[2]),
            "gpu_util_percent": int(parts[3]),
            "temperature_c": int(parts[4]),
            "power_draw_w": float(parts[5]) if parts[5] != "[Not Supported]" else None,
            "power_limit_w": float(parts[6]) if parts[6] != "[Not Supported]" else None,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }


@router.get("/status")
def admin_status(_auth: bool = Depends(require_api_key)):
    jobs = list_jobs_db(limit=100)

    counts = {}
    for job in jobs:
        status = job.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    latest_jobs = [
        {
            "job_id": job.get("job_id"),
            "status": job.get("status"),
            "mode": job.get("mode"),
            "seconds": job.get("seconds"),
            "url": job.get("url"),
            "created_at": job.get("created_at"),
        }
        for job in jobs[:10]
    ]

    return {
        "ok": True,
        "service": "symon-image-server",
        "pid": os.getpid(),
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "image_worker": {
            "worker_started": worker_started(),
            "queue_size": queue_size(),
            "loaded_mode": loaded_mode(),
        },
        "jobs": {
            "stored_recent_jobs": len(jobs),
            "counts": counts,
            "latest": latest_jobs,
        },
        "gpu": get_gpu_status(),
    }
