import requests
import time
import pytest

URL = "http://127.0.0.1:8000"

def test_rate_limits():
    """Проверка ограничения частоты запросов"""
    responses = []
    
    # Делаем запросов больше лимита
    for i in range(70):
        response = requests.get(f"{URL}/items")
        responses.append(response.status_code)
        if response.status_code == 429:  # Too Many Requests
            break
    
    # Должен быть хотя бы один 429
    assert 429 in responses

def test_different_limits():
    """Проверка разных лимитов для разных маршрутов"""
    # GET /items имеет лимит 60/минуту
    # POST /items имеет лимит 10/минуту
    
    post_responses = []
    for i in range(15):
        response = requests.post(f"{URL}/items?name=test{i}")
        post_responses.append(response.status_code)
        if response.status_code == 429:
            break
    
    assert 429 in post_responses