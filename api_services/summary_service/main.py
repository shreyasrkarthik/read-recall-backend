from fastapi import FastAPI
from routes import router

app = FastAPI(
    title="Book Summarization Service",
    description="Handles book summarization for normalized files",
    version="1.0"
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
