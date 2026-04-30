import requests
import time

BASE = "http://127.0.0.1:8000"

def test_invalid_config_blocks_start():
    # Ручная проверка: изменить port на 99999 в config.yaml — приложение не запустится
    print("✅ Проверка: измените порт на недопустимый — приложение должно упасть с ошибкой.")

def test_priority():
    # CLI > ENV > FILE
    print("✅ Проверка приоритета — см. ручную с разными аргументами")

def test_trusted_origin_block():
    headers = {"Origin": "http://evil.com"}
    resp = requests.get(f"{BASE}/", headers=headers)
    print("Trusted origin block:", resp.status_code)  # Должен быть 200? Нет, CORS не блокирует сам запрос, но браузер — да.
    # Проверим реальную блокировку: запрещаем через CORS middleware, но preflight не пройдёт.
    # Для теста используем curl -H "Origin: ..."
    # Лучше: проверить, что OPTIONS не возвращает Access-Control-Allow-Origin для чужого.
    preflight = requests.options(f"{BASE}/", headers=headers)
    print("Preflight evil origin:", preflight.headers.get("access-control-allow-origin"))
    assert preflight.headers.get("access-control-allow-origin") is None

def test_rate_limit():
    for _ in range(12):  # create limit = 10
        r = requests.post(f"{BASE}/items?name=test")
        print(r.status_code)
        if r.status_code == 429:
            print(" Rate limit exceeded works")
            break

def test_security_headers():
    resp = requests.get(f"{BASE}/")
    print("Security headers:", resp.headers.get("x-content-type-options"), resp.headers.get("x-frame-options"))
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"

def test_mode_behavior():
    # Запустить в production mode
    resp = requests.get(f"{BASE}/items")
    print("Production mode response:", resp.json())
    # В production verbose должен быть выключен

if __name__ == "__main__":
    test_trusted_origin_block()
    test_rate_limit()
    test_security_headers()
    test_mode_behavior()