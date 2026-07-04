from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.settings import settings
from app.routes.image import router as image_router
from app.routes.admin import router as admin_router
from app.routes.billing import router as billing_router
from app.routes.accounts import router as accounts_router
from app.routes.me import router as me_router
from app.routes.chat import router as chat_router
from app.routes.runtime_status import router as runtime_router
from app.routes.vision import router as vision_router

app = FastAPI(title=settings.app_name)

app.include_router(image_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(accounts_router)
app.include_router(me_router)
app.include_router(chat_router)
app.include_router(runtime_router)
app.include_router(vision_router)

app.mount("/images", StaticFiles(directory=settings.output_dir), name="images")
app.mount("/ui", StaticFiles(directory="/home/google/symon-image-server/frontend", html=True), name="ui")


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "status": "online",
        "services": {
            "image_agent": "active",
            "chat_agent": "planned",
            "coding_agent": "planned",
        },
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "app": settings.app_name,
    }


@app.get("/ui")
def ui_redirect():
    return RedirectResponse(url="/ui/")
