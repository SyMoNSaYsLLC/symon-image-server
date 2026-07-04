#!/usr/bin/env python3
import gc
import json
import os
import sys
from pathlib import Path

# BLIP must stay CPU-only.
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor

MODEL_ID = "Salesforce/blip-image-captioning-base"


def write_result(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: blip_caption_once.py IMAGE_PATH RESULT_PATH")

    image_path = Path(sys.argv[1])
    result_path = Path(sys.argv[2])

    try:
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((768, 768))

        processor = BlipProcessor.from_pretrained(MODEL_ID)
        model = BlipForConditionalGeneration.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float32,
        ).to("cpu")

        model.eval()

        inputs = processor(image, return_tensors="pt")
        inputs = {k: v.to("cpu") for k, v in inputs.items()}

        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=60)

        caption = processor.decode(output[0], skip_special_tokens=True)

        write_result(
            result_path,
            {
                "ok": True,
                "caption": caption,
                "model": MODEL_ID,
                "runtime": "subprocess_cpu",
            },
        )

    except Exception as e:
        write_result(
            result_path,
            {
                "ok": False,
                "error": str(e),
                "model": MODEL_ID,
                "runtime": "subprocess_cpu",
            },
        )
        raise

    finally:
        try:
            del model
        except Exception:
            pass
        try:
            del processor
        except Exception:
            pass
        try:
            del image
        except Exception:
            pass

        gc.collect()


if __name__ == "__main__":
    main()
