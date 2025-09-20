from fastapi import FastAPI
from backend.routers import chat, health, auth  # absolute import

app = FastAPI(
    title="LLM Micro-Prompt Processing Backend",
    description="A backend to process prompts by splitting them into micro-prompts and routing to the best LLM.",
    version="0.1.0",
)

# Routers with prefixes to avoid conflicts
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])

@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint to welcome users to the API.
    """
    return {"message": "Welcome to the LLM Micro-Prompt Processing API"}
