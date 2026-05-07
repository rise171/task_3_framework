import hashlib
import hmac
import time
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import threading

class ImpedanceKeyManager:
    def __init__(self, secret: str, ttl_seconds: int = 300):
        self.secret = secret.encode('utf-8')
        self.ttl_seconds = ttl_seconds
        self._used_keys: Dict[str, float] = {}  # Хранилище использованных ключей
        self._lock = threading.RLock()
        
    def generate_key(self, client_id: Optional[str] = None) -> str:
        timestamp = int(time.time())
        
        # Создаем уникальную строку для подписи
        if client_id:
            message = f"{client_id}:{timestamp}:{secrets.token_hex(8)}"
        else:
            message = f"{timestamp}:{secrets.token_hex(8)}"
        
        # Создаем HMAC подпись
        signature = hmac.new(
            self.secret,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()[:32]
        
        # Формируем ключ: timestamp + signature
        key = f"{timestamp}:{signature}"
        return key
    
    def verify_key(self, key: str, client_id: Optional[str] = None) -> bool:
        with self._lock:
            try:
                # Проверяем формат ключа
                if ':' not in key:
                    return False
                
                timestamp_str, signature = key.split(':', 1)
                timestamp = int(timestamp_str)
                
                # Проверяем срок действия
                current_time = int(time.time())
                if current_time - timestamp > self.ttl_seconds:
                    return False
                
                # Проверяем не был ли ключ уже использован
                if key in self._used_keys:
                    return False
                
                # Восстанавливаем ожидаемую подпись
                if client_id:
                    expected_message = f"{client_id}:{timestamp_str}:"
                    # Нам нужно знать полный message, но мы его не сохраняли
                    # Поэтому проверяем через генерацию по тому же принципу
                    expected_signature = self._generate_signature(timestamp, client_id)
                else:
                    expected_signature = self._generate_signature(timestamp)
                
                # Сравниваем подписи
                if hmac.compare_digest(signature, expected_signature[:32]):
                    # Помечаем ключ как использованный
                    self._used_keys[key] = current_time
                    self._cleanup_used_keys()
                    return True
                
                return False
                
            except (ValueError, IndexError):
                return False
    
    def _generate_signature(self, timestamp: int, client_id: Optional[str] = None) -> str:
        if client_id:
            message = f"{client_id}:{timestamp}:"
        else:
            message = f"{timestamp}:"
        
        return hmac.new(
            self.secret,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _cleanup_used_keys(self):
        """Очищает использованные клюси старше TTL"""
        current_time = time.time()
        expired = [
            key for key, used_time in self._used_keys.items()
            if current_time - used_time > self.ttl_seconds * 2
        ]
        for key in expired:
            del self._used_keys[key]

# Глобальный экземпляр менеджера
_impedance_manager: Optional[ImpedanceKeyManager] = None

def init_impedance_manager(secret: str, ttl_seconds: int = 300):
    global _impedance_manager
    _impedance_manager = ImpedanceKeyManager(secret, ttl_seconds)

def get_impedance_manager() -> ImpedanceKeyManager:
    if _impedance_manager is None:
        raise RuntimeError("Impedance key manager not initialized")
    return _impedance_manager