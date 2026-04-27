
# app/main.py

from fastapi import FastAPI
from app.core.config import settings
from app.modules.routes import router
import app.utils.logger

app = FastAPI(title=settings.app_name)
 
app.include_router(router)