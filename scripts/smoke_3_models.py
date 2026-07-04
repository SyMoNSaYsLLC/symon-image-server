#!/usr/bin/env python3
import json
import sys
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8090"
ROOT = Path("/home/google/symon-image-server")
USER_KEY_PATH = ROOT / "data/frontend_user_api_key.txt"


def require(cond, msg):
    if not cond:
        raise RuntimeError(msg)


def show(title, data):
    print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, sort_keys=True))


def main():
    if "--yes-generate" not in sys.argv:
        print("This test generates one fast image and spends 1 credit.")
        print("Run again with: python3 scripts/smoke_3_models.py --yes-generate")
        return

    key = USER_KEY_PATH.read_text().strip()
    headers = {"X-API-Key": key}
    json_headers = {"X-API-Key": key, "Content-Type": "application/json"}

    r = requests.get(f"{BASE}/me", headers=headers, timeout=20)
    r.raise_for_status()
    before = r.json()
    show("before /me", {"credits": before["credits"]})

    r = requests.post(
        f"{BASE}/chat/complete",
        headers=json_headers,
        json={
            "message": "Reply with exactly: OK",
            "max_tokens": 32,
            "temperature": 0.2,
        },
        timeout=180,
    )
    r.raise_for_status()
    chat = r.json()
    show("qwen chat", {"content": chat.get("content"), "timings": chat.get("timings")})
    require("OK" in chat.get("content", ""), "Qwen chat did not return OK")

    r = requests.post(
        f"{BASE}/sdxl/txt2img/queue",
        headers=json_headers,
        json={
            "mode": "fast",
            "prompt": "A Symoneural three model AI platform logo, cyber raven, clean futuristic dashboard style",
        },
        timeout=30,
    )
    r.raise_for_status()
    queued = r.json()
    show("sdxl queued", queued)
    job_id = queued["job_id"]

    deadline = time.time() + 120
    job = None
    while time.time() < deadline:
        r = requests.get(f"{BASE}/me/jobs/{job_id}", headers=headers, timeout=20)
        r.raise_for_status()
        job = r.json()["job"]
        if job["status"] in {"done", "error"}:
            break
        time.sleep(2)

    show("sdxl job", job)
    require(job and job["status"] == "done", "SDXL image job did not finish")
    require(job.get("url"), "SDXL job missing image URL")

    image_path = ROOT / "data/outputs" / Path(job["url"]).name
    require(image_path.exists(), f"image file missing: {image_path}")

    with image_path.open("rb") as f:
        r = requests.post(
            f"{BASE}/vision/caption",
            headers=headers,
            files={"image": (image_path.name, f, "image/png")},
            timeout=180,
        )
    r.raise_for_status()
    caption = r.json()
    show("blip caption", caption)
    require(caption.get("caption"), "BLIP returned empty caption")

    r = requests.post(
        f"{BASE}/chat/complete",
        headers=json_headers,
        json={
            "message": "Reply with exactly: DONE",
            "max_tokens": 32,
            "temperature": 0.2,
        },
        timeout=180,
    )
    r.raise_for_status()
    chat2 = r.json()
    show("qwen after blip", {"content": chat2.get("content")})
    require("DONE" in chat2.get("content", ""), "Qwen did not restart after BLIP")

    r = requests.get(f"{BASE}/runtime/status", headers=headers, timeout=20)
    r.raise_for_status()
    show("runtime status", r.json())

    r = requests.get(f"{BASE}/me", headers=headers, timeout=20)
    r.raise_for_status()
    after = r.json()
    show("after /me", {"credits": after["credits"]})

    print("\nPASS: 3-model smoke test succeeded")


if __name__ == "__main__":
    main()
