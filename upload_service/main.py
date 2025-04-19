from fastapi import FastAPI
from routes import router

app = FastAPI(
    title="Book Upload Service",
    description="Handles book uploads and initiates processing.",
    version="1.0"
)

app.include_router(router)
