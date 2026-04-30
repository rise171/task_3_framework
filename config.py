import os
import sys
import yaml
from argparse import ArgumentParser
from typing import Any, Dict, List
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class AppConfig:
    mode: str
    host: str
    port: int
    trusted_origins: List[str]
    rate_limit_per_minute: int
    rate_limit_create_per_minute: int
    debug_verbose: bool
    security_headers: bool

    @classmethod
    def from_file(cls, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data if data else {}
        except FileNotFoundError:
            return {}

    @classmethod
    def from_env(cls) -> Dict[str, Any]:
        env_data = {}
        
        if os.getenv("APP_MODE"):
            env_data["mode"] = os.getenv("APP_MODE")
        if os.getenv("HOST"):
            env_data["host"] = os.getenv("HOST")
        if os.getenv("PORT"):
            env_data["port"] = int(os.getenv("PORT"))
        if os.getenv("TRUSTED_ORIGINS"):
            env_data["trusted_origins"] = os.getenv("TRUSTED_ORIGINS").split(",")
        if os.getenv("RATE_LIMIT_PER_MINUTE"):
            env_data["rate_limit_per_minute"] = int(os.getenv("RATE_LIMIT_PER_MINUTE"))
        if os.getenv("RATE_LIMIT_CREATE_PER_MINUTE"):
            env_data["rate_limit_create_per_minute"] = int(os.getenv("RATE_LIMIT_CREATE_PER_MINUTE"))
        if os.getenv("DEBUG_VERBOSE"):
            env_data["debug_verbose"] = os.getenv("DEBUG_VERBOSE", "").lower() == "true"
        if os.getenv("SECURITY_HEADERS"):
            env_data["security_headers"] = os.getenv("SECURITY_HEADERS", "").lower() == "true"
        
        return env_data

    @classmethod
    def from_cli(cls) -> Dict[str, Any]:
        # Фильтруем только аргументы, которые относятся к нашему приложению
        cli_args = [arg for arg in sys.argv[1:] if arg.startswith('--') and not arg in ['--reload', '--host', '--port']]
        
        parser = ArgumentParser(add_help=False)
        parser.add_argument("--mode", type=str)
        parser.add_argument("--trusted-origins", type=str)
        parser.add_argument("--rate-limit-per-minute", type=int)
        parser.add_argument("--rate-limit-create-per-minute", type=int)
        parser.add_argument("--debug-verbose", action="store_true")
        parser.add_argument("--no-debug-verbose", dest="debug_verbose", action="store_false")
        parser.add_argument("--security-headers", action="store_true")
        parser.add_argument("--no-security-headers", dest="security_headers", action="store_false")
        parser.set_defaults(debug_verbose=None, security_headers=None)
        
        try:
            args, _ = parser.parse_known_args(cli_args)
        except:
            return {}
        
        cli_data = {}
        if args.mode:
            cli_data["mode"] = args.mode
        if args.trusted_origins:
            cli_data["trusted_origins"] = args.trusted_origins.split(",")
        if args.rate_limit_per_minute:
            cli_data["rate_limit_per_minute"] = args.rate_limit_per_minute
        if args.rate_limit_create_per_minute:
            cli_data["rate_limit_create_per_minute"] = args.rate_limit_create_per_minute
        if args.debug_verbose is not None:
            cli_data["debug_verbose"] = args.debug_verbose
        if args.security_headers is not None:
            cli_data["security_headers"] = args.security_headers
        
        return cli_data

    @classmethod
    def load(cls, config_file: str = "config.yaml") -> "AppConfig":
        # Приоритет: CLI > ENV > FILE (но CLI только наши параметры)
        final = {}
        
        # Файл (низший приоритет)
        file_cfg = cls.from_file(config_file)
        final.update(file_cfg)
        
        # Переменные окружения
        env_cfg = cls.from_env()
        final.update(env_cfg)
        
        # CLI аргументы (высший приоритет)
        cli_cfg = cls.from_cli()
        final.update(cli_cfg)
        
        # Значения по умолчанию
        final.setdefault("mode", "educational")
        final.setdefault("host", "127.0.0.1")
        final.setdefault("port", 8000)
        final.setdefault("trusted_origins", ["http://localhost:3000", "http://127.0.0.1:8000"])
        final.setdefault("rate_limit_per_minute", 60)
        final.setdefault("rate_limit_create_per_minute", 10)
        final.setdefault("debug_verbose", final["mode"] == "educational")
        final.setdefault("security_headers", True)
        
        # Валидация
        errors = []
        if final["mode"] not in ["educational", "production"]:
            errors.append("mode must be 'educational' or 'production'")
        if not isinstance(final["port"], int) or not (1024 <= final["port"] <= 65535):
            errors.append(f"port must be 1024-65535, got {final['port']}")
        if not isinstance(final["trusted_origins"], list) or not all(isinstance(o, str) for o in final["trusted_origins"]):
            errors.append("trusted_origins must be list of strings")
        for origin in final["trusted_origins"]:
            if not (origin.startswith("http://") or origin.startswith("https://")):
                errors.append(f"Invalid origin format (must have http:// or https://): {origin}")
        if not isinstance(final["rate_limit_per_minute"], int) or final["rate_limit_per_minute"] < 1:
            errors.append("rate_limit_per_minute must be >=1")
        if not isinstance(final["rate_limit_create_per_minute"], int) or final["rate_limit_create_per_minute"] < 1:
            errors.append("rate_limit_create_per_minute must be >=1")
        
        if errors:
            print("❌ Configuration errors:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        
        print(f"✅ Configuration loaded: mode={final['mode']}, port={final['port']}, verbose={final['debug_verbose']}")
        return cls(**final)