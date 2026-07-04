import subprocess
import time

import requests

QWEN_SERVICE = "symon-qwen.service"
QWEN_URL = "http://127.0.0.1:8080/v1"
QWEN_NGL_ATTEMPTS = ["70"]


def qwen_running() -> bool:
    try:
        r = requests.get(f"{QWEN_URL}/models", timeout=2)
        return r.status_code < 500
    except Exception:
        return False


def systemctl_user(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", *args],
        capture_output=True,
        text=True,
    )


def qwen_pids() -> list[int]:
    r = systemctl_user("show", QWEN_SERVICE, "-p", "MainPID", "--value")
    if r.returncode != 0:
        return []

    value = r.stdout.strip()
    if not value or value == "0":
        return []

    try:
        return [int(value)]
    except ValueError:
        return []


def stop_qwen() -> dict:
    r = systemctl_user("stop", QWEN_SERVICE)
    return {
        "ok": r.returncode == 0,
        "service": QWEN_SERVICE,
        "stopped": r.returncode == 0,
        "stderr": r.stderr.strip(),
    }


def prepare_gpu_for_qwen():
    # Stop only Symon's own Qwen service. Do not pkill global llama-server.
    stop_qwen()

    try:
        from app.services.vision_caption import unload_caption_model
        unload_caption_model()
    except Exception:
        pass

    try:
        from app.services.image_jobs import unload_pipe
        unload_pipe()
    except Exception:
        pass

    time.sleep(5)


def start_qwen() -> dict:
    if qwen_running():
        return {
            "ok": True,
            "already_running": True,
            "url": QWEN_URL,
            "pids": qwen_pids(),
        }

    prepare_gpu_for_qwen()

    r = systemctl_user("start", QWEN_SERVICE)
    if r.returncode != 0:
        return {
            "ok": False,
            "error": "failed to start Symon Qwen service",
            "service": QWEN_SERVICE,
            "stderr": r.stderr.strip(),
        }

    deadline = time.time() + 120
    while time.time() < deadline:
        if qwen_running():
            return {
                "ok": True,
                "started": True,
                "service": QWEN_SERVICE,
                "url": QWEN_URL,
                "pids": qwen_pids(),
                "ngl": "70",
            }
        time.sleep(1)

    status = systemctl_user("status", QWEN_SERVICE, "--no-pager")
    return {
        "ok": False,
        "error": "Symon Qwen service did not become ready in time",
        "service": QWEN_SERVICE,
        "status": status.stdout[-4000:],
        "stderr": status.stderr.strip(),
    }
