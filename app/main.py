from fastapi import FastAPI
from app.api.v1.endpoints import router as api_v1_router

app = FastAPI(
    title="QuizGen AI Engine",
    description="Production-grade quiz generation engine with self-correcting grounding audit and Redis caching",
    version="1.0.0"
)

app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/health")
def healthcheck():
    return {"status": "healthy"}
