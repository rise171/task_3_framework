import os
import sys
import yaml
from argparse import ArgumentParser
from typing import Any, Dict, List
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

load_dotenv()

@dataclass
class AppConfig:
    mode: str                     # "educational" or "production"
    host: str
    port: int
    trusted_origins: List[str]    # список доверенных источников (браузер)
    rate_limit_per_minute: int    # общий лимит
    rate_limit_create_per_minute: int  # * повышенная строгость для POST
    debug_verbose: bool
    security_headers: bool

    @classmethod
    def from_file(cls, path: str) -> Dict[str, Any]:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return data

    @classmethod
    def from_env(cls) -> Dict[str, Any]:
        return {
            "mode": os.getenv("APP_MODE"),
            "host": os.getenv("HOST"),
            "port": os.getenv("PORT"),
            "trusted_origins": os.getenv("TRUSTED_ORIGINS", "").split(",") if os.getenv("TRUSTED_ORIGINS") else None,
            "rate_limit_per_minute": os.getenv("RATE_LIMIT_PER_MINUTE"),
            "rate_limit_create_per_minute": os.getenv("RATE_LIMIT_CREATE_PER_MINUTE"),
            "debug_verbose": os.getenv("DEBUG_VERBOSE", "").lower() == "true" if os.getenv("DEBUG_VERBOSE") else None,
            "security_headers": os.getenv("SECURITY_HEADERS", "").lower() == "true" if os.getenv("SECURITY_HEADERS") else None,
        }

    @classmethod
    def from_cli(cls) -> Dict[str, Any]:
        parser = ArgumentParser()
        parser.add_argument("--mode", type=str)
        parser.add_argument("--host", type=str)
        parser.add_argument("--port", type=int)
        parser.add_argument("--trusted-origins", type=str, help="comma separated")
        parser.add_argument("--rate-limit-per-minute", type=int)
        parser.add_argument("--rate-limit-create-per-minute", type=int)
        parser.add_argument("--debug-verbose", action="store_true")
        parser.add_argument("--no-debug-verbose", dest="debug_verbose", action="store_false")
        parser.add_argument("--security-headers", action="store_true")
        parser.add_argument("--no-security-headers", dest="security_headers", action="store_false")
        parser.set_defaults(debug_verbose=None, security_headers=None)
        args = parser.parse_args()

        cli_data = {}
        if args.mode:
            cli_data["mode"] = args.mode
        if args.host:
            cli_data["host"] = args.host
        if args.port:
            cli_data["port"] = args.port
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
        # Приоритет: CLI > ENV > FILE
        final = {}
        try:
            file_cfg = cls.from_file(config_file)
            final.update(file_cfg)
        except FileNotFoundError:
            print(f"⚠️ Config file {config_file} not found, using defaults/override")

        env_cfg = cls.from_env()
        # удаляем None
        env_cfg = {k: v for k, v in env_cfg.items() if v is not None}
        final.update(env_cfg)

        cli_cfg = cls.from_cli()
        cli_cfg = {k: v for k, v in cli_cfg.items() if v is not None}
        final.update(cli_cfg)

        # установка значений по умолчанию, если не задано
        final.setdefault("mode", "educational")
        final.setdefault("host", "127.0.0.1")
        final.setdefault("port", 8000)
        final.setdefault("trusted_origins", ["http://localhost:3000", "http://127.0.0.1:8000"])
        final.setdefault("rate_limit_per_minute", 60)
        final.setdefault("rate_limit_create_per_minute", 10)
        final.setdefault("debug_verbose", final["mode"] == "educational")
        final.setdefault("security_headers", True)

        # валидация
        errors = []
        if final["mode"] not in ["educational", "production"]:
            errors.append("mode must be 'educational' or 'production'")
        if not isinstance(final["port"], int) or not (1024 <= final["port"] <= 65535):
            errors.append("port must be 1024-65535")
        if not isinstance(final["trusted_origins"], list) or not all(isinstance(o, str) for o in final["trusted_origins"]):
            errors.append("trusted_origins must be list of strings")
        # * проверка корректности адресов (базовое)
        for origin in final["trusted_origins"]:
            if not (origin.startswith("http://") or origin.startswith("https://")):
                errors.append(f"Invalid origin format (no http/https): {origin}")
        if not isinstance(final["rate_limit_per_minute"], int) or final["rate_limit_per_minute"] < 1:
            errors.append("rate_limit_per_minute must be >=1")
        if not isinstance(final["rate_limit_create_per_minute"], int) or final["rate_limit_create_per_minute"] < 1:
            errors.append("rate_limit_create_per_minute must be >=1")

        if errors:
            print("❌ Configuration errors:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)

        return cls(**final)