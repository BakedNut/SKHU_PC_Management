from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from skhu_pc_management.domain.settings.definitions import RegistrySettingDefinition
from skhu_pc_management.domain.settings.models import ApplyResult


@dataclass(frozen=True)
class ApplySettings:
    def execute(self, definitions: Iterable[RegistrySettingDefinition]) -> list[ApplyResult]:
        return [
            ApplyResult(
                name=definition.name,
                success=False,
                message="Setting application is not implemented yet.",
            )
            for definition in definitions
        ]
