"""Iskra - Secure Social Network"""
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import os

from app.models import Base, engine
from app.routers import auth, users, posts, messages, groups, feed, api
from app.config import settings

# Get absolute paths relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "templates")
UPLOADS_DIR = os.path.join(BASE_DIR, "app", "static", "uploads")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Iskra",
    description="Secure anonymous social network inspired by VK and Teleguard",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"])

# Static files and templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(api.router, prefix="/api", tags=["api"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(posts.router, prefix="/posts", tags=["posts"])
app.include_router(messages.router, prefix="/messages", tags=["messages"])
app.include_router(groups.router, prefix="/groups", tags=["groups"])
app.include_router(feed.router, prefix="/feed", tags=["feed"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

@app.get("/feed", response_class=HTMLResponse)
async def feed_page(request: Request):
    return templates.TemplateResponse("feed/index.html", {"request": request})

@app.get("/profile/{user_id}", response_class=HTMLResponse)
async def profile_page(request: Request, user_id: str):
    return templates.TemplateResponse("profile/index.html", {"request": request, "user_id": user_id})

@app.get("/messages", response_class=HTMLResponse)
async def messages_page(request: Request):
    return templates.TemplateResponse("messages/index.html", {"request": request})

@app.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request):
    return templates.TemplateResponse("groups/index.html", {"request": request})

@app.get("/group/{group_id}", response_class=HTMLResponse)
async def group_page(request: Request, group_id: int):
    return templates.TemplateResponse("groups/detail.html", {"request": request, "group_id": group_id})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("profile/settings.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
