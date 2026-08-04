import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="IPO Sahayak API")

# Comma-separated list, e.g. "https://ipo-sahayak.vercel.app,http://localhost:5173".
# Defaults to "*" so local/hackathon dev isn't blocked before the deployed frontend URL is known.
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

if allowed_origins == ["*"]:
    print(
        "WARNING: ALLOWED_ORIGINS not set — CORS is wide open (*). "
        "Set ALLOWED_ORIGINS in Render once the Vercel URL is known."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Hello from IPO Sahayak backend"}


@app.get("/health")
def health():
    return {"status": "ok"}
