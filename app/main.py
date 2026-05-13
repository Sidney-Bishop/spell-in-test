from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Project paths — resolved relative to this file, so the app works
# no matter where you run it from.
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Spell in Test")

# Serve CSS, JS, images, etc. from /static/...
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Jinja2 environment for rendering HTML templates.
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "Spell in Test"},
    )