from app.api.routes.match import router as match_router
from app.core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.job import router as job_router
from app.api.routes.profile import router as profile_router
from app.api.routes.auth import router as auth_router
from app.api.routes.resume import router as resume_router

from app.middlewares.exception_middleware import register_exception_handlers


app = FastAPI(title = "Jobpilot API")



app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


app.include_router(auth_router)
app.include_router(resume_router)
app.include_router(profile_router)

app.include_router(job_router)

app.include_router(match_router)
