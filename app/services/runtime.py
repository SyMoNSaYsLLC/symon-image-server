import os
import time
import signal
import subprocess
from pathlib import Path
from typing import Any

import requests

LLM_URL = "http://127.0.0.1:8080/v1"
QWEN_DIR = Path("/home/google/Downloads/Qwen3-32B-GGUF")
QWEN_SCRIPT = QWEN_DIR / "start_server_32b.sh"
QWEN_LOG = Path("/home/google/llama_logs/qwen_runtime_from_symon.log")


def llm_is_running() -> bool:
    try:
        r = requests.get(f"{LLM_URL}/models", timeout=2)
        return r.status_code < 500
    except Exception:
        return False


def find_llama_pids() -> list[int]:
    try:
        out = subprocess.check_output(["pgrep", "-f", "llama-server"], text=True)
        return [int(x.strip()) for x in out.splitlines() if x.strip().isdigit()]
    except subprocess.CalledProcessError:
        return []


def stop_llm_server():
    pids = find_llama_pids()
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.time() + 8
    while time.time() < deadline:
        if not find_llama_pids():
            return {"ok": True, "stopped": True}
        time.sleep(0.5)

    for pid in find_llama_pids():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    return {"ok": True, "stopped": True, "forced": True}


def unload_image_model():
    from app.services.image_jobs import unload_pipe, loaded_mode
    before = loaded_mode()
    unload_pipe()
    return {"ok": True, "unloaded_mode": before}


def start_llm_server():
    if llm_is_running():
        return {"ok": True, "already_running": True, "url": LLM_URL}

    unload_image_model()

    QWEN_LOG.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update({
        "CTX": "2048",
        "PARALLEL": "1",
        "BATCH": "256",
        "UBATCH": "64",
        "NGL": "70",
    })

    log = open(QWEN_LOG, "a", buffering=1)
    proc = subprocess.Popen(
        [str(QWEN_SCRIPT)],
        cwd=str(QWEN_DIR),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    deadline = time.time() + 45
    while time.time() < deadline:
        if llm_is_running():
            return {"ok": True, "started": True, "pid": proc.pid, "url": LLM_URL}
        time.sleep(1)

    return {
        "ok": False,
        "started": False,
        "pid": proc.pid,
        "error": "Qwen server did not become ready in time",
        "log": str(QWEN_LOG),
    }


def generate_text(prompt: str, max_tokens: int = 256, temperature: float = 0.2) -> dict[str, Any]:
    start = start_llm_server()
    if not start.get("ok"):
        return start

    r = requests.post(
        f"{LLM_URL}/chat/completions",
        json={
            "model": "local",
            "messages": [
                {
                    "role": "user",
                    "content": "/no_think\n" + prompt,
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()

    msg = data["choices"][0]["message"]
    return {
        "ok": True,
        "content": msg.get("content", ""),
        "usage": data.get("usage"),
        "timings": data.get("timings"),
    }


def runtime_status():
    from app.services.image_jobs import loaded_mode, queue_size

    return {
        "ok": True,
        "llm": {
            "running": llm_is_running(),
            "url": LLM_URL,
            "pids": find_llama_pids(),
            "log": str(QWEN_LOG),
        },
        "image": {
            "loaded_mode": loaded_mode(),
            "queue_size": queue_size(),
        },
    }
