
# app/main.py

from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import router

app = FastAPI(title=settings.app_name)
 
app.include_router(router)