"""
FastAPI application entrypoint.
Endpoints are stubs for now — no AI logic wired in yet.
"""
from fastapi import FastAPI

from app.api.routes import predict, history

app = FastAPI(title="MedX AI Platform", version="0.1.0")

app.include_router(predict.router)
app.include_router(history.router)


@app.get("/")
def root():
    return {"message": "MedX AI Platform is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
