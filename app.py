from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
from config import AppConfig

# Чтение настроек (ранняя проверка)
config = AppConfig.load("config.yaml")

# Разная настройка лимитов для разных маршрутов *
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{config.rate_limit_per_minute}/minute"])
app = FastAPI(title="Secure Web Service")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 1. Защита: только доверенные источники (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.trusted_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Origin", "Content-Type", "Authorization"],
)

# 2. Защитные заголовки (минимум 2)
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    if config.security_headers:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response

# Учебный режим: подробное логирование
@app.middleware("http")
async def verbose_logging(request: Request, call_next):
    if config.debug_verbose:
        start = time.time()
        print(f"[VERBOSE] {request.method} {request.url.path}")
        response = await call_next(request)
        duration = time.time() - start
        print(f"[VERBOSE] Status {response.status_code} in {duration:.4f}s")
        return response
    return await call_next(request)

# Маршрут списка (общий лимит)
@app.get("/items")
@limiter.limit(f"{config.rate_limit_per_minute}/minute")
async def get_items(request: Request):
    if config.debug_verbose:
        return {"items": [1, 2, 3], "mode": config.mode, "verbose": True}
    return {"items": [1, 2, 3]}

# Маршрут создания — более строгий лимит *
@app.post("/items")
@limiter.limit(f"{config.rate_limit_create_per_minute}/minute")
async def create_item(request: Request, name: str):
    if config.debug_verbose:
        print(f"[CREATE] {name} from {request.client.host}")
    return {"created": name, "status": "ok"}

# Для проверки ограничений
@app.get("/")
async def root():
    return {"message": "Protected service", "mode": config.mode}