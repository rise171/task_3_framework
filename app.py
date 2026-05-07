from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
from config import AppConfig
from di import Container, Lifetime, reset_scope
from services import CounterService
from impedance_key import init_impedance_manager, get_impedance_manager, ImpedanceKeyManager

# Чтение настроек (ранняя проверка)
config = AppConfig.load("config.yaml")
if config.impedance_key_enabled:
    init_impedance_manager(config.impedance_key_secret, config.impedance_key_ttl)

# Разная настройка лимитов для разных маршрутов
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{config.rate_limit_per_minute}/minute"])
app = FastAPI(title="Secure Web Service")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Настройка DI
container = Container()
container.register(CounterService, lambda: CounterService(), lifetime=Lifetime.SINGLETON)

# 1. Защита: только доверенные источники (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.trusted_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Origin", "Content-Type"],
)

# 2. Защитные заголовки
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

@app.middleware("http")
async def di_scope_middleware(request: Request, call_next):
    reset_scope()
    response = await call_next(request)
    return response

# Маршрут списка (общий лимит)
@app.get("/items")
@limiter.limit(f"{config.rate_limit_per_minute}/minute")
async def get_items(request: Request):
    if config.debug_verbose:
        return {"items": [1, 2, 3], "mode": config.mode, "verbose": True}
    return {"items": [1, 2, 3]}

# Маршрут создания — более строгий лимит
@app.post("/items")
@limiter.limit(f"{config.rate_limit_create_per_minute}/minute")
async def create_item(request: Request, name: str):
    if config.debug_verbose:
        print(f"[CREATE] {name} from {request.client.host}")
    return {"created": name, "status": "ok"}

@app.get("/di-test")
async def di_test():
    s1 = container.resolve(CounterService)
    s2 = container.resolve(CounterService)

    return {
        "same_instance": s1 is s2,
        "id": s1.id,
        "counter": s1.increment()
    }

# Для проверки ограничений
@app.get("/")
async def root():
    return {"message": "Protected service", "mode": config.mode}

@app.middleware("http")
async def impedance_key_middleware(request: Request, call_next):
    """
    Middleware для проверки ключа импедантности.
    Защищает все маршруты, кроме отмеченных @no_impedance_check
    """
    # Пропускаем проверку для определенных маршрутов
    if not config.impedance_key_enabled:
        return await call_next(request)
    
    # Маршруты, которые не требуют проверки
    skip_paths = ['/', '/health', '/metrics', '/docs', '/openapi.json', '/redoc']
    if request.url.path in skip_paths:
        return await call_next(request)
    
    # Получаем ключ из заголовка или query параметра
    impedance_key = request.headers.get('X-Impedance-Key')
    if not impedance_key:
        impedance_key = request.query_params.get('impedance_key')
    
    if not impedance_key:
        return JSONResponse(
            status_code=401,
            content={"error": "Impedance key required", "message": "Provide X-Impedance-Key header or impedance_key parameter"}
        )
    
    # Получаем client_id (опционально, из заголовка)
    client_id = request.headers.get('X-Client-Id')
    
    # Проверяем ключ
    manager = get_impedance_manager()
    if not manager.verify_key(impedance_key, client_id):
        return JSONResponse(
            status_code=403,
            content={"error": "Invalid or expired impedance key", "message": "Provide a valid impedance key"}
        )
    
    # Если проверка пройдена, добавляем информацию в request state
    request.state.impedance_verified = True
    request.state.impedance_timestamp = int(time.time())
    
    response = await call_next(request)
    return response

# Исправленная часть запуска
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",  # Изменено с "main:app" на "app:app"
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )