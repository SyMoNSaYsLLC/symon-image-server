#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

import requests


BASE = os.getenv("BASE_URL", "http://127.0.0.1:8090")
ROOT = Path("/home/google/symon-image-server")
ENV_PATH = ROOT / ".env"
USER_KEY_PATH = ROOT / "data/frontend_user_api_key.txt"


def read_env_key(name: str) -> str:
    if not ENV_PATH.exists():
        raise RuntimeError(f"missing {ENV_PATH}")

    for line in ENV_PATH.read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()

    raise RuntimeError(f"missing {name} in .env")


def print_json(title: str, data):
    print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, sort_keys=True))


def require_status(resp: requests.Response, expected: int, label: str):
    if resp.status_code != expected:
        print(f"\nFAIL: {label}")
        print(f"Expected HTTP {expected}, got HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)


def main():
    admin_key = read_env_key("API_KEYS")

    if not USER_KEY_PATH.exists():
        raise RuntimeError(f"missing {USER_KEY_PATH}")

    user_key = USER_KEY_PATH.read_text().strip()

    admin_headers = {"X-API-Key": admin_key}
    user_headers = {"X-API-Key": user_key}
    json_user_headers = {
        "X-API-Key": user_key,
        "Content-Type": "application/json",
    }

    # 1. Health is public.
    r = requests.get(f"{BASE}/health", timeout=15)
    require_status(r, 200, "health")
    print_json("health", r.json())

    # 2. Admin status requires admin key.
    r = requests.get(f"{BASE}/admin/status", headers=admin_headers, timeout=15)
    require_status(r, 200, "admin status")
    admin_status = r.json()
    print_json("admin status", {
        "ok": admin_status.get("ok"),
        "queue_size": admin_status.get("image_worker", {}).get("queue_size"),
        "loaded_mode": admin_status.get("image_worker", {}).get("loaded_mode"),
        "gpu_memory_used_mib": admin_status.get("gpu", {}).get("memory_used_mib"),
        "stored_recent_jobs": admin_status.get("jobs", {}).get("stored_recent_jobs"),
    })

    # 3. Billing packs are public.
    r = requests.get(f"{BASE}/billing/packs", timeout=15)
    require_status(r, 200, "billing packs")
    print_json("billing packs", r.json())

    # 4. Admin can read account status.
    r = requests.get(f"{BASE}/accounts/dev", headers=admin_headers, timeout=15)
    require_status(r, 200, "account status")
    account_status = r.json()
    print_json("account status", {
        "ok": account_status.get("ok"),
        "account_id": account_status.get("account_id"),
        "credits": account_status.get("credits"),
        "key_count": len(account_status.get("keys", [])),
        "ledger_count": len(account_status.get("ledger", [])),
    })

    # 5. User key can read /me.
    r = requests.get(f"{BASE}/me", headers=user_headers, timeout=15)
    require_status(r, 200, "me")
    me = r.json()
    print_json("me", {
        "ok": me.get("ok"),
        "account_id": me.get("account_id"),
        "credits": me.get("credits"),
        "api_key": me.get("api_key"),
        "recent_job_count": len(me.get("recent_jobs", [])),
        "recent_ledger_count": len(me.get("recent_ledger", [])),
    })

    # 6. User key can list own jobs.
    r = requests.get(f"{BASE}/me/jobs", headers=user_headers, timeout=15)
    require_status(r, 200, "me jobs")
    print_json("me jobs", r.json())

    # 7. Admin key cannot submit image jobs.
    r = requests.post(
        f"{BASE}/sdxl/txt2img/queue",
        headers={
            "X-API-Key": admin_key,
            "Content-Type": "application/json",
        },
        json={
            "mode": "not_a_real_mode",
            "prompt": "admin key should not submit jobs",
        },
        timeout=15,
    )
    require_status(r, 401, "admin key blocked from image queue")
    print_json("admin key blocked", r.json())

    # 8. User key authenticates, but invalid mode blocks before generation.
    r = requests.post(
        f"{BASE}/sdxl/txt2img/queue",
        headers=json_user_headers,
        json={
            "mode": "not_a_real_mode",
            "prompt": "this should not generate",
        },
        timeout=15,
    )
    require_status(r, 400, "invalid mode blocks generation")
    print_json("invalid mode blocked", r.json())

    # 9. Confirm no queue/model loaded after no-generate tests.
    r = requests.get(f"{BASE}/admin/status", headers=admin_headers, timeout=15)
    require_status(r, 200, "final admin status")
    final_status = r.json()
    final_worker = final_status.get("image_worker", {})

    print_json("final no-generate check", {
        "queue_size": final_worker.get("queue_size"),
        "loaded_mode": final_worker.get("loaded_mode"),
        "gpu_memory_used_mib": final_status.get("gpu", {}).get("memory_used_mib"),
    })

    if final_worker.get("queue_size") != 0:
        raise RuntimeError("queue_size is not 0")

    if final_worker.get("loaded_mode") is not None:
        raise RuntimeError("loaded_mode is not null; model may have loaded")

    print("\nPASS: no-generation smoke test completed successfully")


if __name__ == "__main__":
    main()
