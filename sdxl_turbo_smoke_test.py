import os
import time
import torch
from diffusers import AutoPipelineForText2Image

MODEL_ID = "stabilityai/sdxl-turbo"
OUT_DIR = "/home/google/symon-image-server/data/outputs"
OUT_PATH = os.path.join(OUT_DIR, "sdxl_turbo_smoke_test.png")

os.makedirs(OUT_DIR, exist_ok=True)

print("Loading model:", MODEL_ID)
t0 = time.time()

pipe = AutoPipelineForText2Image.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    variant="fp16",
    use_safetensors=True,
)
pipe = pipe.to("cuda")

print(f"Model loaded in {time.time() - t0:.2f}s")
print("Generating test image...")

t1 = time.time()
image = pipe(
    prompt="A cinematic futuristic city skyline at sunset, ultra detailed, vibrant lighting",
    num_inference_steps=4,
    guidance_scale=0.0,
    height=1024,
    width=1024,
).images[0]

image.save(OUT_PATH)

print(f"Image generated in {time.time() - t1:.2f}s")
print("Saved to:", OUT_PATH)
