"""Application registry for modular blueprints."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import ModuleType
from typing import Iterable, List

from flask import Blueprint, Flask


@dataclass(slots=True)
class AppModule:
    """Represents a discovered application module."""

    name: str
    module: ModuleType


class AppRegistry:
    """Manages discovery and registration of scaffold sub-applications."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self.modules: List[AppModule] = []

    def discover(self, module_paths: Iterable[str]) -> None:
        for path in module_paths:
            if not path:
                continue
            module = importlib.import_module(path)
            self.modules.append(AppModule(name=path, module=module))

    def register_all(self) -> None:
        for entry in self.modules:
            self._register_module(entry)

    def _register_module(self, entry: AppModule) -> None:
        registrar = getattr(entry.module, "register", None)
        if callable(registrar):
            registrar(self.app)
            return

        blueprints = getattr(entry.module, "blueprints", None)
        if isinstance(blueprints, Blueprint):
            self.app.register_blueprint(blueprints)
        elif isinstance(blueprints, (list, tuple)):
            for bp in blueprints:
                if isinstance(bp, Blueprint):
                    self.app.register_blueprint(bp)

        init_app = getattr(entry.module, "init_app", None)
        if callable(init_app):
            init_app(self.app)
