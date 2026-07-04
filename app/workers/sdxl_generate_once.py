#!/usr/bin/env python3
import gc
import json
import os

# This worker is allowed to use GPU even though the main API is not.
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
import sys
import time
from pathlib import Path

import torch
from diffusers import AutoPipelineForText2Image


MODELS = {
    "fast": {
        "model_id": "stabilityai/sdxl-turbo",
        "variant": "fp16",
        "default_steps": 2,
        "default_guidance": 0.0,
    },
    "quality": {
        "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
        "variant": "fp16",
        "default_steps": 20,
        "default_guidance": 6.5,
    },
}


def clear_cuda():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


def write_result(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def main():
    job_path = Path(sys.argv[1])
    result_path = Path(sys.argv[2])

    job = json.loads(job_path.read_text())

    job_id = job["job_id"]
    mode = job.get("mode", "fast")

    if mode not in MODELS:
        raise RuntimeError(f"unsupported mode: {mode}")

    cfg = MODELS[mode]

    output_dir = Path("/home/google/symon-image-server/data/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{job_id}.png"
    out_path = output_dir / filename

    steps = job.get("num_inference_steps")
    if steps is None:
        steps = cfg["default_steps"]

    guidance = job.get("guidance_scale")
    if guidance is None:
        guidance = cfg["default_guidance"]

    t0 = time.time()

    try:
        print(f"Loading SDXL mode={mode}: {cfg['model_id']}", flush=True)

        pipe = AutoPipelineForText2Image.from_pretrained(
            cfg["model_id"],
            torch_dtype=torch.float16,
            variant=cfg["variant"],
            use_safetensors=True,
        )

        pipe = pipe.to("cuda")

        if hasattr(pipe, "enable_vae_tiling"):
            pipe.enable_vae_tiling()

        image = pipe(
            prompt=job["prompt"],
            negative_prompt=job.get("negative_prompt"),
            width=int(job.get("width", 1024)),
            height=int(job.get("height", 1024)),
            num_inference_steps=int(steps),
            guidance_scale=float(guidance),
        ).images[0]

        image.save(out_path)

        seconds = round(time.time() - t0, 2)

        write_result(
            result_path,
            {
                "ok": True,
                "filename": filename,
                "path": str(out_path),
                "url": f"/images/{filename}",
                "seconds": seconds,
                "resolved_steps": int(steps),
                "resolved_guidance": float(guidance),
            },
        )

    except Exception as e:
        write_result(
            result_path,
            {
                "ok": False,
                "error": str(e),
            },
        )
        raise

    finally:
        try:
            del pipe
        except Exception:
            pass

        try:
            del image
        except Exception:
            pass

        clear_cuda()


if __name__ == "__main__":
    main()
