from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import diagrams, chat, health
from audit.middleware import audit_middleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://app.test", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(audit_middleware)

app.include_router(health.router)
app.include_router(diagrams.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
