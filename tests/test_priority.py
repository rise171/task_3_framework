# test_priority.py
import os
import subprocess

def test_config_priority():
    """Проверка приоритета CLI > ENV > YAML"""
    
    # Тест 1: YAML default
    # config.yaml: port=8000
    result = subprocess.run(['python', '-c', 
        'from config import AppConfig; c=AppConfig.load(); print(c.port)'],
        capture_output=True, text=True)
    assert "8000" in result.stdout  # Берется из YAML
    
    # Тест 2: ENV переопределяет YAML
    os.environ['PORT'] = '9000'
    result = subprocess.run(['python', '-c', 
        'from config import AppConfig; c=AppConfig.load(); print(c.port)'],
        capture_output=True, text=True, env=os.environ)
    assert "9000" in result.stdout  # ENV переопределил
    
    # Тест 3: CLI имеет высший приоритет
    result = subprocess.run(['python', '-c', 
        'from config import AppConfig; c=AppConfig.load(); print(c.port)',
        '--port', '7000'], capture_output=True, text=True)
    assert "7000" in result.stdout  # CLI переопределил всех