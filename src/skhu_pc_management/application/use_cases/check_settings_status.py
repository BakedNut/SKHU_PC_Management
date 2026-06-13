from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from skhu_pc_management.domain.settings.definitions import RegistrySettingDefinition
from skhu_pc_management.domain.settings.models import SettingStatus


@dataclass(frozen=True)
class CheckSettingsStatus:
    def execute(self, definitions: Iterable[RegistrySettingDefinition]) -> list[SettingStatus]:
        return [
            SettingStatus(
                name=definition.name,
                is_applied=False,
                expected_value=str(definition.expected_value),
            )
            for definition in definitions
        ]
