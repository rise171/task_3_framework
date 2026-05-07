import uuid
import time
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any

class RequestAnalyticsService:
    """
    Сервис сбора статистики запросов.
    Собирает метрики: количество запросов, время ответа, популярные маршруты
    """
    
    def __init__(self):
        self.id = str(uuid.uuid4())
        self._lock = threading.RLock()
        
        # Статистика по маршрутам
        self._endpoint_stats: Dict[str, int] = defaultdict(int)
        
        # Время последних запросов (для расчета RPS)
        self._request_times: List[float] = []
        
        # Общая статистика
        self._total_requests = 0
        self._start_time = time.time()
        
        # Статистика по методам
        self._method_stats: Dict[str, int] = defaultdict(int)
        
        # История последних ошибок
        self._recent_errors: List[Dict] = []
        self._max_errors_to_store = 50
    
    def record_request(self, path: str, method: str, status_code: int, duration_ms: float):
        """Записать информацию о запросе"""
        with self._lock:
            # Общая статистика
            self._total_requests += 1
            self._endpoint_stats[path] += 1
            self._method_stats[method] += 1
            
            # Время запроса для RPS
            self._request_times.append(time.time())
            # Оставляем только последние 1000 замеров
            if len(self._request_times) > 1000:
                self._request_times = self._request_times[-1000:]
            
            # Запоминаем ошибки
            if status_code >= 400:
                self._recent_errors.insert(0, {
                    "timestamp": datetime.now().isoformat(),
                    "path": path,
                    "method": method,
                    "status_code": status_code,
                    "duration_ms": duration_ms
                })
                # Ограничиваем список
                if len(self._recent_errors) > self._max_errors_to_store:
                    self._recent_errors = self._recent_errors[:self._max_errors_to_store]
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить текущую статистику"""
        with self._lock:
            uptime_seconds = time.time() - self._start_time
            
            # Расчет RPS (запросов в секунду за последнюю минуту)
            current_time = time.time()
            one_minute_ago = current_time - 60
            recent_requests = [t for t in self._request_times if t > one_minute_ago]
            rps = len(recent_requests) / 60 if recent_requests else 0
            
            return {
                "service_id": self.id,
                "uptime_seconds": round(uptime_seconds, 2),
                "total_requests": self._total_requests,
                "requests_per_second": round(rps, 2),
                "endpoints": dict(self._endpoint_stats),
                "methods": dict(self._method_stats),
                "recent_errors": self._recent_errors[:5],  # Только 5 последних
                "is_healthy": len(self._recent_errors) < 10  # Здоров, если <10 ошибок
            }
    
    def get_popular_endpoints(self, limit: int = 5) -> List[tuple]:
        """Получить самые популярные маршруты"""
        with self._lock:
            sorted_endpoints = sorted(
                self._endpoint_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_endpoints[:limit]
    
    def reset_stats(self):
        """Сбросить статистику (для тестов)"""
        with self._lock:
            self._total_requests = 0
            self._endpoint_stats.clear()
            self._method_stats.clear()
            self._request_times.clear()
            self._start_time = time.time()