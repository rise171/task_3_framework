from typing import Callable, Dict, Type, Any
from contextvars import ContextVar

# Хранилище scoped объектов (на запрос)
_request_scope: ContextVar[Dict] = ContextVar("request_scope", default={})

class Lifetime:
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"

class Container:
    def __init__(self):
        self._providers: Dict[Type, Callable] = {}
        self._lifetimes: Dict[Type, str] = {}
        self._singletons: Dict[Type, Any] = {}

    def register(self, cls: Type, provider: Callable, lifetime: str):
        self._providers[cls] = provider
        self._lifetimes[cls] = lifetime

    def resolve(self, cls: Type):
        lifetime = self._lifetimes[cls]

        if lifetime == Lifetime.SINGLETON:
            if cls not in self._singletons:
                self._singletons[cls] = self._providers[cls]()
            return self._singletons[cls]

        elif lifetime == Lifetime.TRANSIENT:
            return self._providers[cls]()

        elif lifetime == Lifetime.SCOPED:
            scope = _request_scope.get()
            if cls not in scope:
                scope[cls] = self._providers[cls]()
                _request_scope.set(scope)
            return scope[cls]

        else:
            raise ValueError("Unknown lifetime")

# helper для очистки scope
def reset_scope():
    _request_scope.set({})