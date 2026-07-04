#!/usr/bin/env python3
import json
import requests
from pathlib import Path

BASE = "http://127.0.0.1:8090"
ROOT = Path("/home/google/symon-image-server")
KEY = (ROOT / "data/frontend_user_api_key.txt").read_text().strip()

headers = {"X-API-Key": KEY}

def show(name, data):
    print(f"\n=== {name} ===")
    print(json.dumps(data, indent=2, sort_keys=True))

def get(path):
    r = requests.get(BASE + path, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

def head(path):
    r = requests.head(BASE + path, timeout=20)
    return {"status_code": r.status_code, "ok": r.status_code == 200}

show("health", requests.get(BASE + "/health", timeout=20).json())
show("me", get("/me"))
show("runtime", get("/runtime/status"))

show("frontend", {
    "/ui/": head("/ui/"),
    "/ui/apps/chatbot.html": head("/ui/apps/chatbot.html"),
    "/ui/apps/text_to_image.html": head("/ui/apps/text_to_image.html"),
    "/ui/apps/image_to_text.html": head("/ui/apps/image_to_text.html"),
    "/ui/apps/model_status.html": head("/ui/apps/model_status.html"),
})

print("\nPASS: launch check complete")
