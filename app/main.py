from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pathlib import Path
import logging

from app.database import engine, Base
from app.routers import auth, schedules, links, public, profile, settings as app_settings
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="SlotSync API",
    description="API de Gestão de Agenda com links públicos de agendamento",
    version="1.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Rate limit handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Routers
app.include_router(auth.router)
app.include_router(schedules.router)
app.include_router(links.router)
app.include_router(public.router)
app.include_router(profile.router)
app.include_router(app_settings.router)


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/health")
def health():
    return {"status": "ok", "service": "SlotSync API"}
