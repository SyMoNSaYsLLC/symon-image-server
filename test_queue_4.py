import time
import requests

BASE = "http://127.0.0.1:8090"

prompts = [
    "A neon wolf standing on a rainy cyberpunk rooftop, cinematic lighting, ultra detailed",
    "A futuristic armored owl flying through a glowing city, sharp focus, dramatic lighting",
    "A crystal dragon curled around a moonlit tower, fantasy concept art, detailed",
    "A robot samurai in a neon alley, reflective armor, cinematic, ultra detailed",
]

job_ids = []

print("Submitting 4 queued jobs...")
start = time.time()

for prompt in prompts:
    r = requests.post(
        f"{BASE}/sdxl/txt2img/queue",
        json={"prompt": prompt},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    print("submitted:", data)
    job_ids.append(data["job_id"])

print()
print("Polling jobs...")

while True:
    all_done = True

    for job_id in job_ids:
        r = requests.get(f"{BASE}/sdxl/jobs/{job_id}", timeout=30)
        r.raise_for_status()
        job = r.json()["job"]

        status = job["status"]
        seconds = job.get("seconds")
        url = job.get("url")

        print(f"{job_id}: {status} seconds={seconds} url={url}")

        if status not in ("done", "error"):
            all_done = False

    print("---")

    if all_done:
        break

    time.sleep(1)

print(f"Total wall time: {time.time() - start:.2f}s")
