from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from biocurator.providers.base import DatabaseConfig, DatabaseSearcher


class ProviderRegistry:
    _registry: dict[str, type[DatabaseSearcher]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[DatabaseSearcher]) -> None:
        cls._registry[name] = provider_cls

    @classmethod
    def get(
        cls, name: str, config: DatabaseConfig, email: str
    ) -> DatabaseSearcher:
        if name not in cls._registry:
            raise KeyError(
                f"Unknown provider: '{name}'. Available: {list(cls._registry)}"
            )
        return cls._registry[name](config, email)

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._registry.keys())
