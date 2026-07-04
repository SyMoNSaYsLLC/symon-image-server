# Symon Image Server Status

## Confirmed Working

- FastAPI service
- systemd user service
- /health
- /admin/status
- SDXL fast mode
- SDXL quality mode
- image job queue
- image URL serving
- SQLite job persistence
- API-key auth
- account-bound user API keys
- Stripe Checkout test payments
- Stripe webhook credit fulfillment
- credit ledger
- credit-gated image generation
- no-credit requests blocked before GPU/model load
- /me
- /me/jobs
- no-generation smoke test

## Current Credit Costs

- fast: 1 credit
- quality: 5 credits

## Important Local Files Not To Commit

- .env
- data/frontend_user_api_key.txt
- data/dev_user_api_key.txt
- data/symon_jobs.sqlite3
- data/outputs/

## Useful Commands

systemctl --user status symon-image-server.service --no-pager
systemctl --user restart symon-image-server.service
journalctl --user -u symon-image-server.service -f
python3 scripts/smoke_no_generate.py

## Current API Split

### Admin Key

- /admin/status
- /accounts/*
- /billing/balance/*
- /billing/checkout

### User Account Key

- /me
- /me/jobs
- /me/jobs/{job_id}
- /sdxl/txt2img/queue

## Next Build Targets

1. Minimal frontend page
2. Public checkout flow tied to frontend account
3. Real user registration/session layer
4. Prompt enhancer route
5. Production reverse proxy/domain/TLS

## 3-Model MVP Confirmed

Confirmed passing:

- `python3 scripts/smoke_no_generate.py`
- `python3 scripts/smoke_3_models.py --yes-generate`

### Working Model Routes

- Text-to-text: Qwen3-32B-GGUF via `/chat/complete`
- Text-to-image: SDXL via `/sdxl/txt2img/queue`
- Image-to-text: BLIP via `/vision/caption`
- Runtime status: `/runtime/status`

### Runtime Result

- Qwen restarts after SDXL + BLIP
- SDXL queue finishes and clears
- BLIP does not remain loaded
- Credits deduct correctly
- Account-bound jobs show in `/me/jobs`

### Stable Runtime Policy

- Qwen is the text/chat/code model
- SDXL is the image-generation model
- BLIP is the image-caption model for now
- Current Qwen text GGUF does not handle images directly
- Future vision upgrade can replace BLIP behind `/vision/caption`

## Frontend Checkpoint

Confirmed mounted:

- `/ui/`
- `/ui/apps/chatbot.html`
- `/ui/apps/text_to_image.html`
- `/ui/apps/image_to_text.html`
- `/ui/apps/model_status.html`

Current architecture:

- `symon-image-server.service`: frontend/API controller, CUDA disabled
- `symon-qwen.service`: managed Qwen llama-server
- SDXL: one-shot CUDA worker subprocess
- BLIP: CPU subprocess worker
- No global `pkill llama-server`

## Frontend Checkpoint

Confirmed mounted:

- `/ui/`
- `/ui/apps/chatbot.html`
- `/ui/apps/text_to_image.html`
- `/ui/apps/image_to_text.html`
- `/ui/apps/model_status.html`

Current architecture:

- `symon-image-server.service`: frontend/API controller, CUDA disabled
- `symon-qwen.service`: managed Qwen llama-server
- SDXL: one-shot CUDA worker subprocess
- BLIP: CPU subprocess worker
- No global `pkill llama-server`

## Qwen Performance Profile

Current Qwen service performance override:

- `NGL=70`
- `CTX=2048`
- `BATCH=512`
- `UBATCH=128`
- `PARALLEL=1`
- Qwen is managed by `symon-qwen.service`
- Keep Qwen running while actively using chat for best response time

## Qwen Performance Profile

Current Qwen service performance override:

- `NGL=70`
- `CTX=2048`
- `BATCH=512`
- `UBATCH=128`
- `PARALLEL=8`
- Qwen is managed by `symon-qwen.service`
- Keep Qwen running while actively using chat for best response time

## SDXL Fast Mode Performance

Current fast mode tuning:

- SDXL fast mode uses `stabilityai/sdxl-turbo`
- Fast default steps: `1`
- Fast default size: `768x768`
- SDXL runs as a one-shot CUDA worker subprocess
- Main API process keeps CUDA disabled

## SDXL Fast Mode Performance

Current fast mode tuning:

- SDXL fast mode uses `stabilityai/sdxl-turbo`
- Fast default steps: `1`
- Fast default size: `768x768`
- SDXL runs as a one-shot CUDA worker subprocess
- Main API process keeps CUDA disabled
